#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/toolkit/lib" && pwd)/common.sh"

[[ -f "$FRONTEND_DIR/.env.dev" ]] && cp "$FRONTEND_DIR/.env.dev" "$FRONTEND_DIR/.env.local"
myc_require_venv
echo "Levantando backend en $BACKEND_HOST:$BACKEND_PORT..."
(cd "$BACKEND_DIR" && "$UVICORN" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload) &
backend_pid=$!
cleanup() { kill "$backend_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
echo "Levantando frontend en $FRONTEND_HOST:$FRONTEND_PORT..."
(cd "$FRONTEND_DIR" && VITE_API_URL="$API_URL" npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT")
