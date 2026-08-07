# Temujanji KJRI MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build KJRI Dubai visit booking (Telegram ADK agent + FastAPI + Next.js magic-link/QR + staff scan) that syncs services from antrian and creates a queue number on check-in.

**Architecture:** Temujanji FastAPI + Postgres is the source of truth for appointments and daily quotas. Google ADK tools call that API over HTTP. Next.js serves user magic-link, staff scanner, and admin quotas. On staff QR scan, Temujanji calls antrian’s internal queue API with `external_ref=booking_code`.

**Tech Stack:** Python 3.12+ with **uv**, FastAPI, SQLModel/SQLAlchemy 2, Alembic, PostgreSQL 16, Next.js 15/16 + React 19 + Tailwind v4 + pnpm, google-adk 2.x, Telegram webhook, Docker Compose. Sibling app: `../antrian` (Django/MySQL).

**Spec:** [`docs/superpowers/specs/2026-08-07-temujanji-kjri-design.md`](../specs/2026-08-07-temujanji-kjri-design.md)

## Global Constraints

- Python deps: **uv only** (`pyproject.toml` + `uv.lock`); use `uv sync` / `uv run` / `uv add` — never primary `pip install -r`.
- Timezone for date rules: `Asia/Dubai`.
- Slot model: date-only; no time-of-day slots in MVP.
- Identity: `full_name` + `document_number` only.
- Check-in only on appointment date; antrian failure must leave status `booked`.
- Do not merge with Chatbot KJRI info bot.
- Do not edit `.cursor/plans/temujanji_adk_design_*.plan.md`.

---

## File structure (target)

```text
temujanji-agent/
  pyproject.toml
  uv.lock
  .env.example
  docker-compose.yml
  backend/
    app/
      main.py
      config.py
      db.py
      models.py
      schemas.py
      auth.py
      deps.py
      services/
        quota.py
        appointments.py
        checkin.py
        antrian_client.py
        qr.py
      routers/
        auth.py
        services.py
        availability.py
        appointments.py
        checkin.py
        admin.py
    alembic/
    tests/
  frontend/
    package.json
    app/j/[token]/page.tsx
    app/staff/login/page.tsx
    app/staff/scan/page.tsx
    app/admin/login/page.tsx
    app/admin/quotas/page.tsx
    app/admin/appointments/page.tsx
    lib/api.ts
  agent/
    agent.py
    tools.py
  telegram/
    bot.py
  docs/superpowers/...
```

Antrian (sibling) modifications:

```text
../antrian/backend/services/models.py
../antrian/backend/services/views.py
../antrian/backend/services/urls.py
../antrian/backend/services/serializers.py
../antrian/backend/antrian/settings.py
```

---

### Task 1: Repo scaffold (uv + FastAPI hello + Postgres compose)

**Files:**
- Create: `pyproject.toml`, `.env.example`, `docker-compose.yml`, `backend/app/main.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/tests/test_health.py`, `.gitignore`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: FastAPI `GET /health` → `{"status":"ok"}`; Compose `postgres` + `api`

- [ ] **Step 1: Init git and ignore junk**

```bash
cd "/Users/ahmadsyafiqkamil/Documents/Project/SYAMIL/Kumpulan Aplikasi/temujanji-agent"
git init
```

Create `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
node_modules/
.next/
dist/
*.pyc
.DS_Store
```

- [ ] **Step 2: Create `pyproject.toml` with uv**

```toml
[project]
name = "temujanji-agent"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.32.0",
  "sqlmodel>=0.0.22",
  "sqlalchemy[asyncio]>=2.0.36",
  "asyncpg>=0.30.0",
  "alembic>=1.14.0",
  "pydantic-settings>=2.6.0",
  "httpx>=0.28.0",
  "python-jose[cryptography]>=3.3.0",
  "passlib[bcrypt]>=1.7.4",
  "python-multipart>=0.0.17",
]

[dependency-groups]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.24.0",
  "ruff>=0.8.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["backend/tests"]
```

```bash
uv sync
```

Expected: `uv.lock` created.

- [ ] **Step 3: Write failing health test**

`backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 4: Run test — expect fail**

```bash
uv run pytest backend/tests/test_health.py -v
```

Expected: FAIL (module/app missing).

- [ ] **Step 5: Minimal FastAPI app**

`backend/app/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+asyncpg://temujanji:temujanji@localhost:5432/temujanji"
    timezone: str = "Asia/Dubai"
    agent_api_key: str = "dev-agent-key"
    jwt_secret: str = "dev-jwt-secret-change-me"
    qr_signing_secret: str = "dev-qr-secret"
    antrian_base_url: str = "http://localhost:8001/api"
    antrian_api_key: str = "dev-antrian-key"
    public_web_base: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"

settings = Settings()
```

`backend/app/db.py`:

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from backend.app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

`backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings

app = FastAPI(title="Temujanji KJRI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

`.env.example`:

```env
DATABASE_URL=postgresql+asyncpg://temujanji:temujanji@localhost:5432/temujanji
AGENT_API_KEY=dev-agent-key
JWT_SECRET=dev-jwt-secret-change-me
QR_SIGNING_SECRET=dev-qr-secret
ANTRIAN_BASE_URL=http://localhost:8001/api
ANTRIAN_API_KEY=dev-antrian-key
PUBLIC_WEB_BASE=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
```

`docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: temujanji
      POSTGRES_PASSWORD: temujanji
      POSTGRES_DB: temujanji
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
  api:
    image: ghcr.io/astral-sh/uv:python3.12-bookworm
    working_dir: /app
    command: uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./:/app
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://temujanji:temujanji@postgres:5432/temujanji
    depends_on:
      - postgres
volumes:
  pgdata:
```

Add empty `backend/app/__init__.py`.

- [ ] **Step 6: Run test — expect pass**

```bash
uv run pytest backend/tests/test_health.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add .gitignore pyproject.toml uv.lock .env.example docker-compose.yml backend
git commit -m "chore: scaffold uv FastAPI health endpoint and postgres compose"
```

---

### Task 2: Domain models + Alembic + staff auth login

**Files:**
- Create: `backend/app/models.py`, `backend/app/schemas.py`, `backend/app/auth.py`, `backend/app/deps.py`, `backend/app/routers/auth.py`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/tests/test_auth_login.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth_login.py`

**Interfaces:**
- Produces: tables per spec §5; `POST /api/v1/auth/login` → `{access_token, role}`

- [ ] **Step 1: Write failing login test**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from backend.app.main import app

@pytest.mark.asyncio
async def test_login_rejects_bad_password():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/api/v1/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code in (401, 404)
```

- [ ] **Step 2: Run — expect fail/missing route**

```bash
uv run pytest backend/tests/test_auth_login.py -v
```

- [ ] **Step 3: Implement SQLModel tables** matching spec: `ServiceCache`, `DailyQuota`, `Appointment` (+ status enum), `CheckIn`, `StaffUser` (+ role enum).

- [ ] **Step 4: Auth helpers + login router**

- `hash_password` / `verify_password` / JWT create+decode (`settings.jwt_secret`)
- Deps: `require_agent_api_key` (`X-API-Key`), `require_staff`, `require_admin`
- `POST /api/v1/auth/login` returns JWT with `sub` + `role`
- Wire under `/api/v1` in `main.py`

- [ ] **Step 5: Alembic + bootstrap admin**

```bash
uv run alembic init backend/alembic
uv run alembic revision --autogenerate -m "init temujanji models"
uv run alembic upgrade head
```

Seed admin: username `admin`, password from `ADMIN_BOOTSTRAP_PASSWORD` (default `admin123`), role `admin`.

- [ ] **Step 6: Tests pass + commit**

```bash
uv run pytest backend/tests/test_auth_login.py -v
git add backend
git commit -m "feat: add domain models, alembic, and staff login JWT"
```

---

### Task 3: Service sync + daily quotas admin API

**Files:**
- Create: `backend/app/services/antrian_client.py`, `backend/app/routers/services.py`, `backend/app/routers/admin.py`, `backend/app/services/quota.py`, `backend/tests/test_quotas.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_quotas.py`

**Interfaces:**
- Produces: `POST /api/v1/services/sync`, `GET /api/v1/services`, admin quota CRUD, `GET /api/v1/availability`

- [ ] **Step 1: Failing test** — admin creates quota capacity=2; availability remaining==2.

- [ ] **Step 2: `AntrianClient.list_services()`** — httpx GET `{ANTRIAN_BASE_URL}/public/services/`.

- [ ] **Step 3: Sync endpoint** upserts `ServiceCache`.

- [ ] **Step 4: Admin quota CRUD** — capacity >= 1; reject shrink below `booked_count`.

- [ ] **Step 5: Availability** — only days with quota rows; `remaining = capacity - booked_count`.

- [ ] **Step 6: Tests + commit**

```bash
uv run pytest backend/tests/test_quotas.py -v
git commit -am "feat: sync antrian services and admin daily quotas"
```

---

### Task 4: Appointments API (create, by-token, cancel)

**Files:**
- Create: `backend/app/services/appointments.py`, `backend/app/services/qr.py`, `backend/app/routers/appointments.py`, `backend/tests/test_appointments.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_appointments.py`

**Interfaces:**
- Produces: `POST /api/v1/appointments`, `GET /api/v1/appointments/by-token/{token}`, `POST /api/v1/appointments/{id}/cancel`

- [ ] **Step 1: Failing tests** — create increments count; duplicate 409; no quota 400; cancel decrements; by-token works.

- [ ] **Step 2: Generators**

```python
import secrets
def new_booking_code() -> str:
    return f"KJRI-{secrets.token_hex(2).upper()}"

def new_access_token() -> str:
    return secrets.token_urlsafe(32)
```

- [ ] **Step 3: `create_appointment`** — lock quota `FOR UPDATE`; date >= today Asia/Dubai; dedupe; insert `booked`; increment count; return magic URL.

- [ ] **Step 4: QR payload**

```python
import hmac, hashlib, json, base64
def make_qr_payload(booking_code: str, secret: str) -> str:
    sig = hmac.new(secret.encode(), booking_code.encode(), hashlib.sha256).hexdigest()[:16]
    raw = json.dumps({"c": booking_code, "s": sig}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode()
```

- [ ] **Step 5: Cancel** — only `booked`; decrement `booked_count`.

- [ ] **Step 6: Tests + commit**

```bash
uv run pytest backend/tests/test_appointments.py -v
git commit -am "feat: appointment create, magic-token read, and cancel"
```

---

### Task 5: Antrian patch — `external_ref` + internal queue API

**Files:**
- Modify: `../antrian/backend/services/models.py`, serializers, views, urls, settings
- Create: antrian migration for `external_ref`

**Interfaces:**
- Produces: `POST /api/internal/queue/` + `X-API-Key`; body `{service_id, external_ref}`; idempotent per `external_ref` for today

- [ ] **Step 1: Add `Queue.external_ref`** CharField null/blank, indexed.

- [ ] **Step 2: Migration**

```bash
cd "../antrian/backend"
python manage.py makemigrations services -n queue_external_ref
python manage.py migrate
```

- [ ] **Step 3: `InternalCreateQueueView`** — API key auth; create or return existing by `external_ref` today.

- [ ] **Step 4: Register URL `internal/queue/`**.

- [ ] **Step 5: Verify curl** twice → same `queue_number`.

- [ ] **Step 6: Commit in antrian repo**

```bash
git commit -am "feat: internal queue create with external_ref for temujanji check-in"
```

---

### Task 6: Check-in API (Temujanji)

**Files:**
- Create: `backend/app/services/checkin.py`, `backend/app/routers/checkin.py`, `backend/tests/test_checkin.py`
- Modify: `antrian_client.py`, `main.py`
- Test: `backend/tests/test_checkin.py`

**Interfaces:**
- Produces: `POST /api/v1/check-in` `{qr_payload}` → queue_number + appointment fields

- [ ] **Step 1: Failing tests** — happy path; antrian 500 leaves `booked`; double scan idempotent; wrong day 409.

- [ ] **Step 2: Verify QR HMAC; load by booking_code**.

- [ ] **Step 3: Enforce `appointment_date == today` Asia/Dubai**.

- [ ] **Step 4: Call antrian; success → `checked_in` + CheckIn row; failure → 502**.

- [ ] **Step 5: Tests + commit**

```bash
uv run pytest backend/tests/test_checkin.py -v
git commit -am "feat: staff check-in orchestrates antrian queue creation"
```

---

### Task 7: Next.js frontend (magic link, staff scan, admin)

**Files:**
- Create: `frontend/` app routes + `lib/api.ts`
- Modify: `docker-compose.yml` add `web`
- Test: `pnpm build`

**Interfaces:**
- Produces: `/j/[token]`, `/staff/login`, `/staff/scan`, `/admin/login`, `/admin/quotas`, `/admin/appointments`

- [ ] **Step 1: Scaffold with pnpm create next-app** (TypeScript, Tailwind, App Router).

- [ ] **Step 2: `lib/api.ts`** against `NEXT_PUBLIC_API_BASE`.

- [ ] **Step 3: User magic-link page + QR** (`pnpm add qrcode.react`).

- [ ] **Step 4: Staff login + scan** (`pnpm add html5-qrcode`); show `queue_number`.

- [ ] **Step 5: Admin quotas + appointments tables**.

- [ ] **Step 6: `pnpm build` succeeds**.

- [ ] **Step 7: Commit**

```bash
git add frontend docker-compose.yml
git commit -m "feat: Next.js magic link, staff scan, and admin quota UI"
```

---

### Task 8: Google ADK agent + Telegram webhook

**Files:**
- Create: `agent/agent.py`, `agent/tools.py`, `telegram/bot.py`
- Modify: `pyproject.toml` via `uv add`, `docker-compose.yml`, `.env.example`
- Test: mock httpx tool wrappers; manual Telegram E2E

**Interfaces:**
- Produces: ADK `root_agent` + Telegram webhook that sends magic link

- [ ] **Step 1: `uv add google-adk`** (and ADK constraints for Python version as needed).

- [ ] **Step 2: Tools** — `list_services`, `get_availability`, `create_appointment`, `cancel_appointment` with `X-API-Key`.

- [ ] **Step 3: `root_agent`** Bahasa Indonesia per spec §12.

- [ ] **Step 4: Telegram webhook** maps chat → session; sends `magic_url` after create.

- [ ] **Step 5: Compose `agent` + `telegram`; env `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`.

- [ ] **Step 6: Commit**

```bash
uv lock
git add agent telegram pyproject.toml uv.lock docker-compose.yml .env.example
git commit -m "feat: ADK booking agent and Telegram webhook adapter"
```

---

### Task 9: Admin appointments API + README smoke E2E

**Files:**
- Create: admin appointments list route, `scripts/smoke_e2e.sh`, `README.md`
- Test: smoke script against local compose

**Interfaces:**
- Produces: `GET /api/v1/admin/appointments` filters; runbook

- [ ] **Step 1: Admin list endpoint** (`date`, `service_id`, `status`).

- [ ] **Step 2: README** — uv sync, compose up, sync services, set quota, ngrok Telegram, staff scan.

- [ ] **Step 3: `scripts/smoke_e2e.sh`** curl path: sync → quota → appointment → by-token → check-in if antrian up.

- [ ] **Step 4: Commit**

```bash
git add backend scripts README.md
git commit -m "docs: README and smoke E2E path for KJRI temujanji MVP"
```

---

## Plan self-review

| Spec requirement | Task |
|------------------|------|
| uv-only Python | 1, 8 |
| Models/quotas/availability | 2, 3 |
| Appointments + magic link + QR | 4 |
| Antrian `external_ref` internal API | 5 |
| Check-in rules | 6 |
| Next.js surfaces | 7 |
| ADK + Telegram | 8 |
| E2E runbook | 9 |

No TBD placeholders. Names `booking_code`, `access_token`, `qr_payload`, `external_ref`, statuses aligned with spec.
