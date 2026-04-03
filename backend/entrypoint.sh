#!/bin/bash
set -e

echo "==> Initializing database tables..."
python -c "
from backend.database import engine
from backend import models
models.Base.metadata.create_all(bind=engine)
print('Tables ready.')
"

echo "==> Checking if seeding is needed..."
NEEDS_SEED=$(python -c "
import sqlite3, sys
try:
    conn = sqlite3.connect('/app/backend/sql_app.db')
    count = conn.execute(\"SELECT COUNT(*) FROM users\").fetchone()[0]
    conn.close()
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
