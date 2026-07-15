#!/usr/bin/env bash
set -o pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/toolkit/lib" && pwd)/database.sh"

ok() { echo "OK  $1"; }
fail() { echo "NO  $1"; }
check() { "$2" >/dev/null 2>&1 && ok "$1" || fail "$1"; }
echo "MYC SYSTEM DOCTOR"
check "backend encontrado" test -d "$BACKEND_DIR"
check "frontend encontrado" test -d "$FRONTEND_DIR"
check "entorno virtual" test -x "$PYTHON"
check "PostgreSQL disponible" myc_check_postgres
if [[ -x "$PYTHON" ]]; then
  check "compileall backend" "$PYTHON" -m compileall -q "$BACKEND_DIR/app"
  check "FastAPI importable" "$PYTHON" -c "from app.main import app"
  check "Alembic current" myc_run_alembic current
fi
check "node disponible" node --version
check "npm disponible" npm --version
check "frontend/.env.local" test -f "$FRONTEND_DIR/.env.local"
echo "Puertos configurados: backend $BACKEND_PORT, frontend $FRONTEND_PORT"
echo "Git: $(cd "$PROJECT_ROOT" && git branch --show-current)"
