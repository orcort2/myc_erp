#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/database.sh"

[[ "${MYC_ALLOW_RESET:-}" == "REINICIAR ERP" ]] || {
  echo "Operación bloqueada. Usa exactamente: MYC_ALLOW_RESET='REINICIAR ERP' scripts/myc reset db" >&2
  exit 2
}
myc_require_venv
myc_check_postgres
if [[ "${MYC_SKIP_BACKUP:-0}" != "1" ]] && myc_database_exists; then
  myc_backup_database
fi
myc_terminate_database_connections
dropdb "$(myc_database_name)"
myc_create_database
myc_run_alembic upgrade head
echo "Base reiniciada. Los catálogos SAT y seeds no se cargan automáticamente."
