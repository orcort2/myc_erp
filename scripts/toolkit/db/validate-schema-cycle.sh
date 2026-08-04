#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "$ROOT/scripts/config.sh"

for command_name in createdb dropdb; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Falta $command_name; instala las herramientas cliente de PostgreSQL." >&2
    exit 1
  }
done

TEMP_BASE_URL="${MYC_TEMP_DATABASE_BASE_URL:-postgresql://localhost:5432}"
DRILL_DB="erp_myc_schema_cycle_$(date +%Y%m%d_%H%M%S)_$$"
[[ "$DRILL_DB" =~ ^erp_myc_schema_cycle_[0-9_]+$ ]] || {
  echo "Nombre temporal inválido." >&2
  exit 2
}

cleanup() {
  if [[ "${MYC_KEEP_DRILL_DB:-0}" != "1" ]]; then
    dropdb --if-exists "$DRILL_DB" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

createdb "$DRILL_DB"
export DATABASE_URL="$TEMP_BASE_URL/$DRILL_DB"

cd "$BACKEND_DIR"
"$ALEMBIC" upgrade head
"$ALEMBIC" check
"$ALEMBIC" downgrade base
"$ALEMBIC" upgrade head
"$ALEMBIC" check
"$ALEMBIC" current

echo "Ciclo reproducible base→head→base→head validado en $DRILL_DB."
