#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "$ROOT/scripts/config.sh"

BACKUP_FILE="${1:-$ROOT/backup_erp_myc_antes_prueba.sql}"
[[ -f "$BACKUP_FILE" && -s "$BACKUP_FILE" ]] || {
  echo "Respaldo inexistente o vacío: $BACKUP_FILE" >&2
  exit 2
}

for command_name in createdb dropdb psql; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Falta $command_name; instala las herramientas cliente de PostgreSQL." >&2
    exit 1
  }
done

TEMP_BASE_URL="${MYC_TEMP_DATABASE_BASE_URL:-postgresql://localhost:5432}"
DRILL_DB="erp_myc_restore_drill_$(date +%Y%m%d_%H%M%S)_$$"
[[ "$DRILL_DB" =~ ^erp_myc_restore_drill_[0-9_]+$ ]] || {
  echo "Nombre temporal inválido." >&2
  exit 2
}
DRILL_URL="$TEMP_BASE_URL/$DRILL_DB"

cleanup() {
  if [[ "${MYC_KEEP_DRILL_DB:-0}" != "1" ]]; then
    dropdb --if-exists "$DRILL_DB" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

createdb "$DRILL_DB"
psql "$DRILL_URL" --set ON_ERROR_STOP=1 --quiet -f "$BACKUP_FILE" >/dev/null

export DATABASE_URL="$DRILL_URL"
cd "$BACKEND_DIR"
"$ALEMBIC" upgrade head
"$ALEMBIC" check

RESTORED_REVISION="$(psql "$DRILL_URL" -Atqc 'SELECT version_num FROM alembic_version')"
TABLE_COUNT="$(psql "$DRILL_URL" -Atqc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")"

echo "Restore validado: revision=$RESTORED_REVISION tablas_publicas=$TABLE_COUNT base=$DRILL_DB"
