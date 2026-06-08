#!/bin/bash
set -e

echo "==> Applying database migrations (Alembic owns the schema)..."
# Run migrations from the backend dir so alembic.ini / script_location resolve.
(cd /app/backend && alembic upgrade head)
echo "Migrations applied."

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
    python /app/backend/seed_data.py
else
    echo "==> Database already seeded ($NEEDS_SEED), skipping."
fi

echo "==> Starting server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
