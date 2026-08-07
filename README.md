# Temujanji KJRI

MVP untuk tempahan temujanji perkhidmatan KJRI, semakan QR di kaunter, dan
penyelarasan nombor giliran Antrian.

## Prasyarat

- [uv](https://docs.astral.sh/uv/)
- Docker Desktop dan Docker Compose
- Node.js 22 dengan Corepack (untuk aplikasi web)

Salin konfigurasi contoh dan pasang kebergantungan Python menggunakan uv:

```bash
cp .env.example .env
uv sync
```

Nilai pembangunan lalai (`AGENT_API_KEY=dev-agent-key` dan kata laluan bootstrap
admin `admin123`) hanya sesuai untuk mesin tempatan. Tukar semua rahsia sebelum
sebarang pendedahan awam.

## Jalankan secara tempatan

```bash
docker compose up --build
```

Perkhidmatan tersedia di:

- API: `http://localhost:8000` (`/docs` untuk OpenAPI)
- Web: `http://localhost:3000`
- ADK web: `http://localhost:8001`
- Telegram webhook: `http://localhost:8002`

Selepas API dan Postgres sihat, log masuk sebagai admin untuk menerima JWT:

```bash
curl -sS http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

Simpan `access_token` daripada respons sebagai `ADMIN_TOKEN`.

## Sediakan perkhidmatan dan kuota

Penyelarasan membaca perkhidmatan aktif daripada Antrian:

```bash
curl -sS -X POST http://localhost:8000/api/v1/services/sync \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

Buka kuota mengikut ID perkhidmatan Antrian dan tarikh Dubai (`YYYY-MM-DD`):

```bash
curl -sS -X POST http://localhost:8000/api/v1/admin/quotas \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"antrian_service_id":7,"day":"2026-08-10","capacity":10}'
```

Pentadbir boleh menyemak temujanji dan menapis mengikut tarikh, perkhidmatan,
atau status (`booked`, `checked_in`, `cancelled`):

```bash
curl -sS "http://localhost:8000/api/v1/admin/appointments?date=2026-08-10&service_id=7&status=booked" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Telegram melalui ngrok

1. Isi `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, dan `GEMINI_API_KEY` di
   `.env`.
2. Dedahkan webhook tempatan: `ngrok http 8002`.
3. Daftarkan `https://<ngrok-id>.ngrok.app/webhook` sebagai webhook bot Telegram.
4. Pastikan secret header Telegram sepadan dengan `TELEGRAM_WEBHOOK_SECRET`.

Jangan gunakan URL ngrok atau token pembangunan dalam persekitaran produksi.

## Daftar hadir petugas

1. Log masuk melalui `http://localhost:3000/staff/login`.
2. Buka `/staff/scan`.
3. Benarkan akses kamera dan imbas QR daripada halaman temujanji; atau tampal
   payload QR jika kamera tidak tersedia.
4. Sistem menghantar temujanji ke Antrian dan memaparkan nombor giliran.

## Smoke E2E

Dengan API, Postgres, dan Antrian berjalan, skrip ini log masuk sebagai admin,
sync perkhidmatan, membuka/mengemas kini kuota esok, mencipta temujanji melalui
agent API key, membaca magic token, dan check-in jika endpoint kesihatan Antrian
tersedia:

```bash
chmod +x scripts/smoke_e2e.sh
./scripts/smoke_e2e.sh
```

Pemboleh ubah pilihan: `API_BASE`, `AGENT_API_KEY`, `ADMIN_USERNAME`,
`ADMIN_PASSWORD`, dan `ANTRIAN_HEALTH_URL`.
