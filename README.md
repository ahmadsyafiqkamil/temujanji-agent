# Temujanji KJRI

MVP booking janji temu layanan KJRI Dubai: agent (Telegram/ADK), halaman magic-link + QR, scan check-in petugas, dan pembuatan nomor antrian di sistem Antrian yang sudah ada.

## Prasyarat

- [uv](https://docs.astral.sh/uv/)
- Docker Desktop + Docker Compose
- Node.js 22 (untuk frontend; Corepack/pnpm)
- Aplikasi sibling **Antrian** (`../antrian`) untuk sync layanan dan create queue saat check-in

Salin konfigurasi dan pasang dependensi Python:

```bash
cp .env.example .env
uv sync
```

Nilai default development (`AGENT_API_KEY=dev-agent-key`, password admin bootstrap `admin123`) **hanya untuk lokal**. Ganti semua secret sebelum akses publik.

**Catatan port:** Antrian biasanya memakai host `8001`. Service ADK Temujanji di compose juga memakai `8001`. Untuk uji lokal, jalankan Antrian + `postgres`/`api`/`web` Temujanji dulu; `agent`/`telegram` belakangan (atau ubah port agent).

Pastikan di `.env`:

- `ANTRIAN_BASE_URL` mengarah ke API Antrian (contoh: `http://localhost:8001/api`)
- `ANTRIAN_API_KEY` sama dengan `INTERNAL_API_KEY` di Antrian

## Menjalankan lokal

```bash
# 1) Antrian (dari folder sibling)
cd ../antrian
docker compose up -d
docker compose exec backend python manage.py migrate

# 2) Temujanji
cd ../temujanji-agent
docker compose up -d postgres api web
uv run alembic -c backend/alembic.ini upgrade head
docker compose restart api
```

Layanan:

| URL | Fungsi |
|-----|--------|
| http://localhost:8000/health | Health API |
| http://localhost:8000/docs | OpenAPI |
| http://localhost:3000 | Web (user / petugas / admin) |
| http://localhost:8001 | ADK web (jika service `agent` dijalankan) |
| http://localhost:8002 | Telegram webhook (jika service `telegram` dijalankan) |

Login admin setelah bootstrap:

- Username: `admin`
- Password: `admin123` (atau `ADMIN_BOOTSTRAP_PASSWORD` di env)

```bash
curl -sS http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

Simpan `access_token` sebagai `ADMIN_TOKEN`.

## Siapkan layanan dan kuota

Sync layanan aktif dari Antrian:

```bash
curl -sS -X POST http://localhost:8000/api/v1/services/sync \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Buka kuota per `antrian_service_id` dan tanggal (zona waktu **Asia/Dubai**, format `YYYY-MM-DD`):

```bash
curl -sS -X POST http://localhost:8000/api/v1/admin/quotas \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"antrian_service_id":1,"day":"2026-08-07","capacity":10}'
```

UI admin: http://localhost:3000/admin/login → `/admin/quotas`

Daftar janji temu:

```bash
curl -sS "http://localhost:8000/api/v1/admin/appointments?date=2026-08-07&service_id=1&status=booked" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Buat janji (tanpa Telegram)

```bash
curl -sS -X POST http://localhost:8000/api/v1/appointments \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"antrian_service_id":1,"full_name":"Ahmad Test","document_number":"A1234567","appointment_date":"2026-08-07"}'
```

Buka magic link dari response: `http://localhost:3000/j/<access_token>` (detail + QR).

## Check-in petugas

1. Login di http://localhost:3000/staff/login (`admin` juga boleh memakai halaman scan).
2. Buka `/staff/scan`.
3. Izinkan kamera dan scan QR dari halaman janji temu, atau tempel `qr_payload`.
4. Sistem memanggil Antrian (`POST …/internal/queue/`) dan menampilkan nomor antrian.

Check-in hanya diizinkan pada **tanggal janji** (Asia/Dubai).

## Telegram + ngrok (opsional)

Pola sama seperti Chatbot KJRI: Compose menjalankan webhook + tunnel ngrok; bot mendaftarkan webhook otomatis saat startup (dengan `TELEGRAM_WEBHOOK_SECRET`).

1. Isi di `.env`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `GEMINI_API_KEY`, dan `NGROK_AUTHTOKEN`.
2. Hindari bentrok port dengan Antrian: jangan jalankan service `agent` di host `:8001` bersamaan dengan Antrian.
3. Jalankan:

```bash
docker compose up -d telegram ngrok
```

4. Cek log sampai muncul `Webhook set: https://…/webhook`:

```bash
docker compose logs -f telegram
```

5. UI inspeksi ngrok: http://localhost:4041 (port host `4041` agar tidak bentrok dengan Chatbot KJRI di `4040`).
6. Chat bot di Telegram. Magic link masih memakai `PUBLIC_WEB_BASE` (default `http://localhost:3000`) — HP di luar LAN perlu tunnel/host terpisah untuk membuka tautan.

Fallback tanpa tunnel (long polling, menghapus webhook):

```bash
uv run python -m telegram.poll
```

Jangan pakai URL ngrok / token development di produksi.

## Smoke E2E

Dengan API, Postgres, dan Antrian berjalan:

```bash
chmod +x scripts/smoke_e2e.sh
./scripts/smoke_e2e.sh
```

Script akan: login admin → sync layanan → buka/update kuota hari ini (Dubai) → buat janji via agent key → baca magic token → check-in jika health Antrian tersedia.

Variabel opsional: `API_BASE`, `AGENT_API_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ANTRIAN_HEALTH_URL`.

## Stack singkat

- Python 3.12+ dikelola **uv** (`pyproject.toml` + `uv.lock`)
- FastAPI + PostgreSQL 16 + Alembic
- Next.js (App Router) + pnpm
- Google ADK 2.x + Telegram webhook
- Integrasi Antrian lewat HTTP + API key

## Konteks

Proyek internal untuk alur janji kedatangan KJRI Dubai. Hari-H WNI tetap mengambil antrian walk-in; Temujanji mengatur janji + check-in yang menautkan nomor antrian.
