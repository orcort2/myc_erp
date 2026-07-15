#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/toolkit/lib" && pwd)/common.sh"

echo "========================================"
echo "        MYC SYSTEM STATUS"
echo "========================================"
for pair in "Backend:$BACKEND_PORT" "Frontend:$FRONTEND_PORT"; do
  label="${pair%%:*}"; port="${pair##*:}"
  echo "$label puerto $port:"
  pids="$(myc_listener_pids "$port")"
  if [[ -n "$pids" ]]; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN
  else
    echo "No hay proceso escuchando."
  fi
  echo "----------------------------------------"
done
echo "Git:"
(cd "$PROJECT_ROOT" && git branch --show-current && git status --short)
