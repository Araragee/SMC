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

## 8. Walkthrough: Oracle Cloud Always Free + DuckDNS

A single Always Free ARM VM runs the whole stack at no cost, with real TLS from
Let's Encrypt. Roughly 40 minutes end to end, most of it waiting on Oracle.

### 8.1 Create the VM

1. Sign up at <https://cloud.oracle.com>. A card is required for identity
   verification; Always Free resources are not charged. Pick the home region
   closest to your users — **it cannot be changed later**.
2. Compute → Instances → **Create instance**.
   - Image: **Canonical Ubuntu 24.04**
   - Shape: **Ampere VM.Standard.A1.Flex**, 2 OCPU / 12 GB RAM (Always Free
     covers 4 OCPU / 24 GB total, so this leaves room for a second instance)
   - Networking: keep the default VCN, **assign a public IPv4 address**
   - SSH keys: upload your public key (`~/.ssh/id_ed25519.pub`) or let Oracle
     generate one and download the private key
3. If you get *"Out of host capacity"*, that shape is full in your region right
   now. Retry later, or try another availability domain. This is common and not
   something you can pay your way out of on the free tier.

### 8.2 Open the ports

Two layers block traffic by default; both must be opened.

Oracle security list — Networking → Virtual Cloud Networks → your VCN → its
subnet → Security Lists → default → **Add ingress rules**:

| Source | Protocol | Port |
| --- | --- | --- |
| `0.0.0.0/0` | TCP | 80 |
| `0.0.0.0/0` | TCP | 443 |

Then on the VM itself (Oracle's Ubuntu images ship a restrictive iptables):

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### 8.3 Point a hostname at it

DuckDNS gives free subdomains and needs no signup beyond a social login.

1. Go to <https://duckdns.org>, sign in, and create **two** subdomains, e.g.
   `smc-yourname` and `smc-yourname-api`.
2. Set both to the VM's public IPv4 address.
3. Confirm from your laptop before continuing — Let's Encrypt will fail if DNS
   is not live yet:

```bash
dig +short smc-yourname.duckdns.org
dig +short smc-yourname-api.duckdns.org
```

### 8.4 Install Docker on the VM

```bash
ssh ubuntu@<vm-ip>
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit   # log back in so the group membership applies
```

The stack builds from source on the VM, so the ARM architecture is handled
automatically — no cross-building or registry needed.

### 8.5 Deploy

```bash
git clone https://github.com/Araragee/SMC.git
cd SMC
git checkout dev

cp backend/.env.example backend/.env
nano backend/.env          # see the table in section 2
```

Set at minimum, in `backend/.env`:

```
SECRET_KEY=<openssl rand -hex 32>
POSTGRES_PASSWORD=<strong password>
DEFAULT_ADMIN_PASSWORD=<your own>
SEED_DEMO_DATA=false
DEBUG=false
REFRESH_COOKIE_SECURE=true
UPLOADS_DIR=/app/uploads
```

Then the deployment hostnames, in a `.env` file at the repository root (Compose
reads this one for variable substitution):

```
POSTGRES_PASSWORD=<same as above>
SECRET_KEY=<same as above>
PUBLIC_HOST=smc-yourname.duckdns.org
API_HOST=smc-yourname-api.duckdns.org
ACME_EMAIL=you@example.com
```

Bring it up:

```bash
./scripts/deploy.sh
```

First build takes several minutes on 2 OCPUs. Caddy requests certificates as
soon as it starts; watch for it:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f caddy
```

### 8.6 Verify

```bash
curl https://smc-yourname-api.duckdns.org/health     # {"status":"ok"}
curl -sI https://smc-yourname.duckdns.org | head -1  # HTTP/2 200
```

Then open the site, log in with `DEFAULT_ADMIN_USERNAME`, change the password
when prompted, and work through the checklist in section 7.

### 8.7 Redeploying

```bash
cd SMC && git pull && ./scripts/deploy.sh
```

Migrations run on every boot, so a pull-and-restart is the whole procedure.

### 8.8 Keeping the free tier

Oracle reclaims idle Always Free compute instances in some regions. A VM
running this stack continuously is not idle by their metric (CPU, network),
so a live deployment is generally safe — but do not treat the free tier as a
backed-up host. Take periodic dumps:

```bash
docker exec smc-db-1 pg_dump -U smc smc | gzip > ~/smc-$(date +%F).sql.gz
docker run --rm -v smc_smc_uploads:/u -v ~:/out alpine tar czf /out/uploads-$(date +%F).tar.gz -C /u .
```
