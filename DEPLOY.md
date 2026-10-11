# Deploy ke VPS (akses via IP publik — minimal)

Panduan ini untuk menjalankan aplikasi di VPS yang diakses lewat IP publik
(tanpa domain/HTTPS), dengan aplikasi sibling **Antrian** berjalan di host VPS
yang sama pada port `8001`. Ini adalah setup "cepat jalan dulu", bukan
production-ready (masih pakai `runserver` + `next dev`).

## Prasyarat VPS

- Docker Engine + Docker Compose plugin (`docker compose version` harus jalan)
- Python 3.12 / `uv` hanya dibutuhkan untuk sibling **Antrian** (bukan repo ini)
- Firewall dibuka untuk port: `8000`, `3000` (dan `8002`/`4041` bila pakai Telegram/ngrok)

## Langkah

### 1. Clone & siapkan env

```bash
git clone <repo-url> temujanji-agent
cd temujanji-agent
cp .env.example .env
```

`.env` **tidak ikut git** (gitignored), jadi wajib dibuat manual.

### 2. Jalankan sibling Antrian di host VPS

Pastikan repo **Antrian** berjalan di host VPS dan listen di `0.0.0.0:8001`.
`host.docker.internal:8001` pada compose ini mengarah ke host VPS.

### 3. Isi `.env`

Ganti `<VPS_IP>` dengan IP publik VPS:

```dotenv
PUBLIC_WEB_BASE=http://<VPS_IP>:3000
CORS_ORIGINS=http://<VPS_IP>:3000
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,api,0.0.0.0,<VPS_IP>
NEXT_PUBLIC_API_BASE=http://<VPS_IP>:8000
```

Wajib ganti secret dari nilai dev (sudah bocor di repo):

```dotenv
JWT_SECRET=<random-panjang>
QR_SIGNING_SECRET=<random-panjang>
AGENT_API_KEY=<random-panjang>
ADMIN_BOOTSTRAP_PASSWORD=<password-kuat>
```

Jika pakai Telegram + ngrok, isi juga:

```dotenv
GEMINI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBHOOK_SECRET=...
NGROK_AUTHTOKEN=...
```

### 4. Jalankan core stack

```bash
docker compose up -d postgres api web
docker compose logs -f api    # tunggu migrate + bootstrap selesai
```

Cek health:

```bash
curl -sS http://<VPS_IP>:8000/health
```

### 5. (Opsional) Telegram + agent

```bash
docker compose up -d agent telegram ngrok
docker compose logs -f telegram   # tunggu "Webhook set: https://…/webhook"
```

### 6. Setup layanan & kuota (sekali)

```bash
curl -sS http://<VPS_IP>:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<ADMIN_BOOTSTRAP_PASSWORD>"}'
# simpan access_token sebagai ADMIN_TOKEN

curl -sS -X POST http://<VPS_IP>:8000/api/v1/services/sync \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Port & URL

| URL | Fungsi |
|-----|--------|
| http://<VPS_IP>:8000/health | Health API |
| http://<VPS_IP>:8000/admin/ | Django admin |
| http://<VPS_IP>:3000 | Web (user / petugas / admin) |
| http://<VPS_IP>:8011 | ADK web (jika `agent` dijalankan) |
| http://<VPS_IP>:8002 | Telegram webhook (jika `telegram` dijalankan) |

## Keamanan minimum

- **Jangan** expose port `5432` (Postgres) dan `5050` (pgAdmin) ke internet.
  Di compose, `postgres` memetakan `5432:5432` — hapus/comment baris `ports`
  di service `postgres` dan `pgadmin` sebelum expose ke publik, atau batasi
  lewat firewall.
- `DJANGO_DEBUG=1`, `runserver`, dan `pnpm dev` hanya untuk sementara.
  Segera migrasi ke gunicorn + `next build && next start` + reverse proxy TLS.

## Troubleshooting

- **400 DisallowedHost**: pastikan `DJANGO_ALLOWED_HOSTS` di `.env` memuat IP publik.
- **Frontend tak bisa panggil API**: `NEXT_PUBLIC_API_BASE` harus mengarah ke
  `http://<VPS_IP>:8000`, bukan `localhost`. Ganti lalu rebuild container web
  (`docker compose up -d --force-recreate web`).
- **Magic link/QR mengarah ke localhost**: pastikan `PUBLIC_WEB_BASE` memakai IP publik.
- **Antrian tidak terhubung**: pastikan Antrian listen di `0.0.0.0:8001` di host,
  dan `ANTRIAN_API_KEY` sama dengan `INTERNAL_API_KEY` di Antrian.
