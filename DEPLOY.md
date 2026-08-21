# Deploying SMC

The app ships as three containers: `db` (Postgres 16), `backend` (FastAPI on
uvicorn), `frontend` (Vue build served by nginx). A single small VM runs all
three; the compose files below assume that shape.

## 1. Files

| File | When it applies | What it does |
| --- | --- | --- |
| `docker-compose.yml` | always | base service definitions |
| `docker-compose.override.yml` | local dev (Compose loads it automatically) | source bind mounts, host-visible `uploads/`, demo seeding on |
| `docker-compose.prod.yml` | production (passed explicitly) | no bind mounts, uploads in a named volume, ports bound to loopback, demo seeding off |

Production never picks up the override file, because Compose only auto-loads it
when you don't pass `-f` flags yourself:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## 2. Environment

Copy `backend/.env.example` to `backend/.env` and set every value. The ones that
matter for a public deployment:

| Variable | Production value |
| --- | --- |
| `SECRET_KEY` | long random string; rotating it invalidates all sessions and signed upload URLs |
| `POSTGRES_PASSWORD` | strong password (also read by compose) |
| `DEFAULT_ADMIN_PASSWORD` | your own; the bootstrap admin is forced to change it on first login |
| `SEED_DEMO_DATA` | `false` — `seed.py` creates accounts with published passwords |
| `DEBUG` | `false` — `/debug/users` is only registered when true |
| `ALLOWED_ORIGINS` | JSON list containing the real frontend origin |
| `REFRESH_COOKIE_SECURE` | `true` behind HTTPS, or the refresh cookie travels in plaintext |
| `UPLOADS_DIR` | `/app/uploads` (the named volume mount point) |

The prod overlay also needs two variables in your shell or an env file beside it:

```bash
export ALLOWED_ORIGINS='["https://smc.example.com"]'
export PUBLIC_API_URL='https://api.smc.example.com'
```

`PUBLIC_API_URL` is injected into the frontend at container start (not at build
time) and drives both the API base URL and the CSP `connect-src`, including the
`wss://` origin for the messaging WebSocket.

## 3. TLS and routing

Both containers publish to `127.0.0.1` only, so put a reverse proxy in front:

- `https://smc.example.com` → `127.0.0.1:3000` (frontend)
- `https://api.smc.example.com` → `127.0.0.1:8000` (backend)

The API proxy must pass WebSocket upgrade headers for `/ws/{user_id}`.

## 4. Database and migrations

`backend/entrypoint.sh` runs `alembic upgrade head` on every boot, so a deploy
is just a rebuild. Postgres data lives in the `smc_pgdata` volume; back it up
with `docker exec smc-db-1 pg_dump -U smc smc`.

## 5. Uploads

Proof and homework files are written to `UPLOADS_DIR` and served through
auth-gated, HMAC-signed URLs. On a single VM the `smc_uploads` named volume is
enough. On any host with an ephemeral or replicated filesystem (Cloud Run,
Koyeb, multi-replica setups) files will vanish or 404 across instances — move
`save_upload` and the download route in `backend/routers/uploads.py` to object
storage (S3/R2/Supabase Storage) before deploying there.

## 6. Optional

- Web Push: generate VAPID keys with `python backend/scripts/gen_vapid.py` and
  set `VAPID_*`. Without them `/push/*` returns 503 and the rest of the app is
  unaffected.
- Email: set `NOTIFIER_TYPE=email` plus the `SMTP_*` values. The default
  (`console`) only logs notifications.

## 7. First boot checklist

1. `docker compose -f docker-compose.yml -f docker-compose.prod.yml ps` — all three healthy.
2. `curl https://api.smc.example.com/health` → `{"status":"ok"}`.
3. Log in as `DEFAULT_ADMIN_USERNAME`; the app forces a password change.
4. Create the real teacher and student accounts under Users, then place them on
   rosters under Roster.
5. Confirm no demo accounts exist (`admin@smc.com`, `juansantos`, …). If any
   appear, `SEED_DEMO_DATA` was true — delete them before going live.
