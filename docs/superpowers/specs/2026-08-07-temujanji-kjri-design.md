# Temujanji KJRI Dubai — Design Spec (MVP)

**Date:** 2026-08-07  
**Status:** Approved (brainstorm checkpoint + completed design sections)  
**Product:** Appointment booking for visiting KJRI Dubai; same-day walk-in queue remains in `antrian`

---

## 1. Goal

WNI can book a visit date for a consular counter service via a Telegram agent, receive a magic-link web page with a QR code, and on arrival have a staff member scan that QR to check them in and immediately create a matching queue number in the existing antrian system.

## 2. Locked decisions

| Area | Decision |
|------|----------|
| Users | End-user books via agent |
| Channel MVP | Telegram first; WhatsApp later (channel adapter only) |
| Services source | Read from existing `antrian` `Service` (mirror/cache in temujanji) |
| Appointment storage | Separate DB from antrian |
| Slot model | Date-only + daily quota per service (in temujanji) |
| Identity | Full name + passport/document number |
| User web | Magic link `/j/{access_token}` (no login) |
| Check-in | Staff scans QR → create antrian `Queue` for same service → link numbers |
| MVP scope | Full flow: Telegram booking + user QR page + staff scan |
| Architecture | Temujanji API is source of truth; ADK uses HTTP tools only |
| Python tooling | **uv required** (`pyproject.toml` + `uv.lock`) |

## 3. Architecture

```text
Telegram → ADK Agent (tools HTTP) → Temujanji FastAPI → Postgres (temujanji)
                                         ↑
                         Next.js (user / staff / admin)
                                         ↓ check-in
                              Antrian Django API → MySQL (antrian)
```

**Boundaries**

- Agent never writes DBs directly.
- Antrian does not store appointment rows; optional `external_ref` on `Queue` links back to booking code.
- Channel adapters (Telegram/WhatsApp) sit outside booking rules.

### 3.1 Components

| Unit | Responsibility |
|------|----------------|
| Temujanji FastAPI | Quotas, appointments, tokens, check-in orchestration |
| Postgres temujanji | Appointment domain data |
| Next.js web | Magic link + QR; staff scanner; admin quotas |
| Google ADK 2.x agent | Conversational booking in Bahasa Indonesia |
| Telegram webhook | Session bridge; send magic link after booking |
| Antrian API | List services; create queue on check-in |

## 4. Tech stack

| Layer | Choice |
|-------|--------|
| Python | 3.12+, managed with **uv** only |
| API | FastAPI + Pydantic v2 + SQLAlchemy 2 / SQLModel + Alembic |
| DB | PostgreSQL 16 (separate from antrian MySQL) |
| Web | Next.js 15/16 + React 19 + TypeScript + Tailwind CSS v4 + pnpm |
| Agent | `google-adk` 2.x; tools call Temujanji HTTP API |
| LLM | Gemini 2.x default; Ollama optional |
| Telegram | FastAPI webhook + Bot API |
| Antrian client | `httpx` + shared API key |
| Runtime | Docker Compose: `api`, `web`, `agent`, `telegram`, `postgres` |

**Out of MVP:** Django for temujanji, MySQL for temujanji, MCP Toolbox writes to booking DB, native scanner app, WhatsApp.

### Repo layout

```text
temujanji-agent/
  backend/           # FastAPI
  frontend/          # Next.js
  agent/             # google-adk
  telegram/          # webhook adapter
  docs/superpowers/
  docker-compose.yml
  pyproject.toml
  uv.lock
```

## 5. Data model (temujanji)

### 5.1 `service_cache`

| Column | Type | Notes |
|--------|------|-------|
| antrian_service_id | int PK | Canonical ID from antrian |
| code | varchar | Loket code (A, B, …) |
| name | varchar | |
| is_active | bool | |
| synced_at | timestamptz | |

### 5.2 `daily_quota`

| Column | Type | Notes |
|--------|------|-------|
| id | serial PK | |
| antrian_service_id | int FK | → service_cache |
| day | date | Visit date |
| capacity | int | >= 1 |
| booked_count | int | Default 0 |

Unique `(antrian_service_id, day)`.  
**Rule:** No row for that day/service ⇒ booking rejected (admin must open quota).

### 5.3 `appointment`

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| booking_code | varchar UK | Human code e.g. `KJRI-A7F2` |
| access_token | varchar UK | Magic-link secret |
| antrian_service_id | int | |
| full_name | varchar | |
| document_number | varchar | Passport / doc |
| appointment_date | date | |
| status | enum | `booked` \| `checked_in` \| `cancelled` |
| telegram_user_id | varchar null | |
| antrian_queue_id | int null | Set after check-in |
| queue_number | varchar null | Set after check-in |
| created_at / updated_at | timestamptz | |

### 5.4 `check_in`

| Column | Type | Notes |
|--------|------|-------|
| id | serial PK | |
| appointment_id | uuid FK | |
| staff_user_id | int / uuid | Staff who scanned |
| checked_in_at | timestamptz | |

### 5.5 Staff/admin users

Minimal `staff_user` table: email/username, password hash, role (`staff` \| `admin`). JWT auth for web staff/admin.

## 6. API (Temujanji)

Base: `/api/v1`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/services` | Agent key or public read | Active services from cache |
| POST | `/services/sync` | Admin JWT | Pull from antrian into cache |
| GET | `/availability` | Agent key | Query: `service_id`, `from`, `to` → dates + remaining |
| POST | `/appointments` | Agent key | Create booking |
| GET | `/appointments/by-token/{token}` | None (token is secret) | User page payload |
| POST | `/appointments/{id}/cancel` | Agent key or token | Cancel if `booked` |
| POST | `/check-in` | Staff JWT | Body: QR payload → create antrian queue → update appointment |
| GET/POST/PATCH | `/admin/quotas` | Admin JWT | Manage daily quotas |
| GET | `/admin/appointments` | Admin JWT | Filter list |
| POST | `/auth/login` | None | Staff/admin JWT |

### 6.1 Agent tools (1:1 API)

1. `list_services`
2. `get_availability`
3. `create_appointment`
4. `cancel_appointment`

After successful create, Telegram adapter sends:  
`{PUBLIC_WEB_BASE}/j/{access_token}`

### 6.2 Create appointment rules

- Require: `antrian_service_id`, `full_name`, `document_number`, `appointment_date`, optional `telegram_user_id`
- Reject if service inactive / no quota row / `booked_count >= capacity`
- Reject past dates (timezone: Asia/Dubai)
- Increment `booked_count` atomically (`SELECT … FOR UPDATE` on quota row)
- Dedup soft rule MVP: same `document_number` + `antrian_service_id` + `appointment_date` + status `booked` → reject

### 6.3 Check-in rules

1. Validate QR payload (booking_code + HMAC or access_token fragment).
2. Load appointment; must be `booked`.
3. MVP **allows** check-in only when `appointment_date == today` (Asia/Dubai); otherwise reject.
4. Call antrian create-queue with `service_id` + `external_ref=booking_code`.
5. On antrian success: set status `checked_in`, store queue ids, insert `check_in` row.
6. On antrian failure: **do not** set `checked_in`; return error to staff UI.
7. Double scan: if already `checked_in`, return existing `queue_number` (idempotent success).

## 7. End-to-end flows

### 7.1 Booking (Telegram)

```text
User opens Telegram bot
  → Agent greets, asks layanan
  → list_services
  → User picks service
  → get_availability
  → User picks date with remaining > 0
  → Agent collects full_name + document_number
  → create_appointment
  → API returns booking_code + access_token + magic URL
  → Bot sends confirmation + magic link
  → User opens web → sees details + QR
```

### 7.2 Staff check-in

```text
User arrives with QR (phone or print)
  → Staff opens /staff/scan (logged in)
  → Camera scans QR
  → POST /check-in
  → Temujanji → Antrian POST create queue
  → Screen shows queue_number + service name
  → Appointment status checked_in
```

### 7.3 Admin opens quota

```text
Admin logs in → /admin/quotas
  → Sync services if needed
  → Set capacity for (service, date)
  → Dates become bookable
```

### 7.4 Cancel

```text
User asks bot to cancel (booking_code)
  → cancel_appointment
  → status cancelled; booked_count decremented if was booked
```

## 8. Error handling

| Case | Behavior |
|------|----------|
| No quota row | 400: tanggal belum dibuka |
| Quota full | 409: kuota penuh |
| Duplicate active booking | 409: sudah ada janji aktif |
| Invalid/expired magic token | 404 user page |
| Cancel when not `booked` | 409 |
| Check-in wrong day | 409: hanya bisa check-in pada tanggal janji |
| Check-in already done | 200 idempotent with existing queue_number |
| Antrian unreachable / 5xx | 502 to staff; appointment stays `booked` |
| Antrian service inactive | 409; appointment stays `booked` |
| Agent missing fields | Tool returns validation errors; agent re-asks |

## 9. Auth & security

| Surface | Mechanism |
|---------|-----------|
| Agent → API | Header `X-API-Key: TEMUJANJI_AGENT_API_KEY` |
| Temujanji → Antrian | Header `X-API-Key: ANTRIAN_INTERNAL_API_KEY` |
| Staff/Admin web | JWT (login); role checks |
| User magic link | High-entropy `access_token` in URL; HTTPS only in prod |
| QR payload | `booking_code` + HMAC using `QR_SIGNING_SECRET`. Do not put passport in QR |
| PII | Minimize logs; never log full access_token |

## 10. Antrian changes (required)

Existing public create: `POST …/public/queue/` with `{ "service_id" }` (`CreateQueueView` in antrian).

**MVP patches in antrian repo:**

1. Add nullable `external_ref` (`CharField`, indexed) on `Queue`.
2. Accept optional `external_ref` on create-queue body.
3. Add internal create endpoint:  
   `POST /api/internal/queue/`  
   - Auth: `X-API-Key`  
   - Body: `{ "service_id": int, "external_ref": str }`  
   - Returns `{ id, queue_number, service_id, external_ref, status }`  
4. Idempotency: if `external_ref` already exists for today, return existing queue.
5. Keep public kiosk endpoint unchanged for walk-in.

Temujanji must not rely on AllowAny public create alone in production.

## 11. Web UX (MVP)

| Route | Audience | Content |
|-------|----------|---------|
| `/j/[token]` | User | Name, service, date, booking_code, QR, status |
| `/staff/login` | Staff | Login |
| `/staff/scan` | Staff | Camera scanner + result panel |
| `/admin/login` | Admin | Login |
| `/admin/quotas` | Admin | CRUD daily quotas + sync services |
| `/admin/appointments` | Admin | Filterable list |

## 12. Agent conversation (MVP)

Bahasa Indonesia. Flow: greet → pilih layanan → pilih tanggal → nama + paspor → confirm → create → send link.  
Support cancel by booking_code.  
Do not invent availability; always call tools.

## 13. Testing strategy

| Layer | What |
|-------|------|
| Backend unit | Quota atomic increment; create/cancel rules; check-in state machine |
| Backend integration | Postgres test DB; httpx mock for antrian |
| Antrian patch | Test internal queue create + external_ref idempotency |
| Frontend | Magic link render; staff scan posts payload (mock API) |
| Agent | Tool schema + instruction smoke (manual Telegram E2E) |
| E2E pilot | Book → open link → scan → see queue number in antrian |

**Timezone for all date rules:** `Asia/Dubai`.

## 14. Non-goals (MVP)

- Time-of-day slots
- WhatsApp
- Merging with Chatbot KJRI info bot
- Priority queue / skipping walk-in based on appointment
- Native mobile scanner app
- Payments

## 15. Implementation order

1. Scaffold monorepo (uv + FastAPI + Postgres + Next.js)  
2. Models + migrations + admin quotas API  
3. Antrian client + service sync  
4. Appointments + magic link API  
5. User web page + QR  
6. Antrian internal queue patch  
7. Check-in API + staff scan UI  
8. ADK agent + Telegram webhook  
9. Docker Compose + pilot E2E  

## 16. Spec self-review

- No TBD placeholders in requirements above.  
- Architecture matches data model and API.  
- Scope is one MVP product (booking + check-in + antrian link).  
- Ambiguities resolved: date-only slots; check-in only on appointment date; double scan idempotent; antrian failure leaves appointment `booked`.
