#!/bin/bash
set -e

echo "==> Applying database migrations (Alembic owns the schema)..."
# Run migrations from the backend dir so alembic.ini / script_location resolve.
(cd /app/backend && alembic upgrade head)
echo "Migrations applied."

# Demo seeding is opt-in. seed.py creates accounts with well-known passwords
# (admin123 / teacher123 / student123), so it must never run by default on a
# deployment. Set SEED_DEMO_DATA=true for local or staging environments.
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    echo "==> Checking if seeding is needed..."
    NEEDS_SEED=$(python -c "
import sys
try:
    from backend.database import SessionLocal
    from backend.models import User
    db = SessionLocal()
    count = db.query(User).count()
    db.close()
    print('skip' if count > 3 else 'seed')
except Exception as e:
    print('seed')
")
    if [ "$NEEDS_SEED" = "seed" ]; then
        echo "==> Seeding database..."
        python /app/backend/seed.py
    else
        echo "==> Database already seeded, skipping."
    fi
else
    echo "==> SEED_DEMO_DATA is not 'true' — skipping demo seed."
fi

# ── Serve ─────────────────────────────────────────────────────────────────────
# PORT is assigned by the platform (Render injects it; so do Fly, Heroku and
# Cloud Run) and the container must listen on exactly that port or the health
# check never passes. Falling back to 8000 keeps docker-compose unchanged.
#
# --forwarded-allow-ips is the load-bearing flag here. uvicorn already parses
# proxy headers by default, but only from peers in its trust list, and that
# list defaults to 127.0.0.1 alone. Render's load balancer reaches the
# container from an internal address, never loopback, so by default every
# X-Forwarded-* header it sends is discarded and uvicorn reports the balancer
# as the client. Two things then break quietly:
#
#   * slowapi keys its rate limits on get_remote_address(), so every visitor
#     shares one bucket. Measured: with the default trust list, five requests
#     from one address return 429 to *everybody else* as well — one noisy
#     client locks out the whole school and the login throttle stops being
#     per-attacker. With this flag, the noisy client alone gets the 429.
#   * SecurityHeadersMiddleware only emits HSTS when request.url.scheme is
#     "https", which it never is while X-Forwarded-Proto is being dropped.
#
# The list is "*" because the balancer's address is internal to Render and not
# knowable ahead of time. That is safe only because nothing but the platform
# can reach this container's port: anything able to connect directly could
# otherwise spoof its own client IP. Do not copy it to a process exposed
# straight to the internet. --proxy-headers is passed explicitly only so the
# dependency is visible at the call site.
echo "==> Starting server on port ${PORT:-8000}..."
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --proxy-headers \
    --forwarded-allow-ips="*" \
    ${UVICORN_RELOAD:+--reload}
