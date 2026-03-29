#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_SRC="$SCRIPT_DIR/backend/sql_app.db"
DB_TMP="/tmp/smc_sql_app.db"

# ── Sync DB back to project on exit ──────────────────────────────────────────
cleanup() {
  echo ""
  echo "⏹  Shutting down backend..."
  kill "$BACKEND_PID" 2>/dev/null
  wait "$BACKEND_PID" 2>/dev/null

  echo "💾  Saving database back to $DB_SRC..."
  cp "$DB_TMP" "$DB_SRC" && echo "✅  Database saved." || echo "⚠️  Could not save DB (check file permissions)."
}
trap cleanup EXIT INT TERM

# ── Copy latest saved DB to /tmp ──────────────────────────────────────────────
if [ -f "$DB_SRC" ]; then
  echo "📦  Loading database from $DB_SRC..."
  cp "$DB_SRC" "$DB_TMP"
else
  echo "⚠️  No existing database found, starting fresh."
fi

# ── Start Backend ─────────────────────────────────────────────────────────────
echo "🚀  Starting Backend on http://localhost:8000..."
export DATABASE_URL="sqlite:////tmp/smc_sql_app.db"
"$SCRIPT_DIR/backend/venv/bin/python" -m uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# ── Start Frontend ────────────────────────────────────────────────────────────
echo "🌐  Starting Frontend..."
cd "$SCRIPT_DIR/frontend" && npm run dev

# cleanup() runs here via trap
