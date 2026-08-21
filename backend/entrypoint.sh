#!/bin/bash
set -e

echo "==> Applying database migrations (Alembic owns the schema)..."
# Run migrations from the backend dir so alembic.ini / script_location resolve.
(cd /app/backend && alembic upgrade head)
echo "Migrations applied."

# Demo seeding is opt-in. seed.py creates accounts with well-known passwords
# (admin123 / teacher123 / student123), so it must never run by default on a
# deployment. Set SEED_DEMO_DATA=true for local or staging environments.
if [ "${SEED_DEMO_DATA:-false}" != "true" ]; then
    echo "==> SEED_DEMO_DATA is not 'true' — skipping demo seed."
    echo "==> Starting server..."
    exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
fi

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
    echo "==> Database already seeded ($NEEDS_SEED), skipping."
fi

echo "==> Starting server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
