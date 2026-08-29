#!/usr/bin/env bash
# Build and (re)start the production stack. Safe to re-run: migrations are
# applied on container boot, so a deploy is just pull + this script.
#
# Reads PUBLIC_HOST / API_HOST / ACME_EMAIL / POSTGRES_PASSWORD / SECRET_KEY
# from the repository-root .env, which Compose loads automatically.
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

# Fail early with a readable message instead of a wall of Compose errors.
for required in PUBLIC_HOST API_HOST ACME_EMAIL POSTGRES_PASSWORD SECRET_KEY; do
    if ! grep -qE "^${required}=.+" .env 2>/dev/null && [ -z "${!required:-}" ]; then
        echo "Missing ${required}. Set it in ./.env — see DEPLOY.md section 8.5." >&2
        exit 1
    fi
done

if [ ! -f backend/.env ]; then
    echo "Missing backend/.env. Copy backend/.env.example and fill it in." >&2
    exit 1
fi

if grep -qE "^SEED_DEMO_DATA=true" backend/.env; then
    echo "Refusing to deploy: SEED_DEMO_DATA=true creates accounts with published passwords." >&2
    exit 1
fi

echo "==> Building images"
"${COMPOSE[@]}" build

echo "==> Starting stack"
"${COMPOSE[@]}" up -d --remove-orphans

echo "==> Waiting for the API to report healthy"
for _ in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "API is up."
        "${COMPOSE[@]}" ps
        exit 0
    fi
    sleep 5
done

echo "API did not come up in five minutes. Recent logs:" >&2
"${COMPOSE[@]}" logs --tail 40 backend >&2
exit 1
