#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Shutdown hook ─────────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "⏹  Shutting down backend..."
  kill "$BACKEND_PID" 2>/dev/null
  wait "$BACKEND_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

# ── Start Database ────────────────────────────────────────────────────────────
echo "🐳  Ensuring Postgres container is running..."
docker compose up -d db

# ── Start Backend ─────────────────────────────────────────────────────────────
echo "🚀  Starting Backend on http://localhost:8000..."
"$SCRIPT_DIR/backend/venv/bin/python" -m uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# ── Start Frontend ────────────────────────────────────────────────────────────
echo "🌐  Starting Frontend..."
cd "$SCRIPT_DIR/frontend" && npm run dev

# cleanup() runs here via trap
