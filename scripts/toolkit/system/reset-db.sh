#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/database.sh"

myc_reset_environment() {
  printf '%s' "${APP_ENV:-${ENVIRONMENT:-${ENV:-development}}}" | tr '[:upper:]' '[:lower:]'
}

myc_require_development_reset() {
  local environment_name database_url
  environment_name="$(myc_reset_environment)"
  database_url="$(myc_database_url | tr '[:upper:]' '[:lower:]')"
  case "$environment_name" in
    production|prod|staging) echo "Reset bloqueado para entorno '$environment_name'." >&2; return 1 ;;
  esac
  [[ "$database_url" != *"production"* && "$database_url" != *"prod_db"* ]] || {
    echo "Reset bloqueado: DATABASE_URL parece ser de producción." >&2; return 1;
  }
}

myc_run_existing_initializers() {
  local sat_importer="$BACKEND_DIR/scripts/import_sat_official_xls_catalogs.py" sat_version
  # init.sh es el inicializador canónico: crea si falta y aplica Alembic.
  "$PROJECT_ROOT/scripts/toolkit/system/init.sh"
  if [[ -f "$sat_importer" ]]; then
    sat_version="$(myc_sat_catalog_version)"
    echo "Importando catálogos SAT iniciales..."
    (cd "$BACKEND_DIR" && "$PYTHON" scripts/import_sat_official_xls_catalogs.py --version "$sat_version" --publication-date "${SAT_PUBLICATION_DATE:-2026-07-14}" --activate)
  fi
}

myc_reset_summary() {
  local revision
  revision="$(cd "$BACKEND_DIR" && "$ALEMBIC" current 2>/dev/null | awk 'NR==1 {print $1}')"
  echo
  echo "Reset de desarrollo completado"
  echo "  Base:       $(myc_database_name)"
  echo "  Migración:  ${revision:-no disponible}"
  echo "  SAT:        importado (versión $(myc_sat_catalog_version))"
  echo "  Seeds:      no existe seed inicial reutilizable"
  echo "  Admin:      no existe script de administrador reutilizable"
}

[[ "${MYC_ALLOW_RESET:-}" == "REINICIAR ERP" ]] || {
  echo "Operación bloqueada. Usa exactamente: MYC_ALLOW_RESET='REINICIAR ERP' scripts/myc reset db" >&2
  exit 2
}
myc_require_development_reset
myc_require_venv
myc_check_postgres
if [[ "${MYC_SKIP_BACKUP:-0}" != "1" ]] && myc_database_exists; then
  myc_backup_database
fi
myc_terminate_database_connections
dropdb --if-exists "$(myc_database_name)"
myc_create_database
myc_run_existing_initializers
myc_database_exists || { echo "La verificación final de conexión falló." >&2; exit 1; }
myc_reset_summary
