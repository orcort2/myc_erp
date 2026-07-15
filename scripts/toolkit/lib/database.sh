#!/usr/bin/env bash

MYC_DB_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$MYC_DB_LIB_DIR/common.sh"

myc_database_url() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    printf '%s\n' "$DATABASE_URL"
  else
    printf 'postgresql://localhost:5432/erp_myc\n'
  fi
}

myc_database_name() {
  local url
  url="$(myc_database_url)"
  url="${url%%\?*}"
  printf '%s\n' "${url##*/}"
}

myc_database_exists() {
  command -v psql >/dev/null 2>&1 || return 1
  psql "$(myc_database_url)" -tAc 'SELECT 1' >/dev/null 2>&1
}

myc_create_database() {
  command -v createdb >/dev/null 2>&1 || { echo "createdb no está instalado." >&2; return 1; }
  createdb "$(myc_database_name)"
}

myc_terminate_database_connections() {
  command -v psql >/dev/null 2>&1 || { echo "psql no está instalado." >&2; return 1; }
  local name
  name="$(myc_database_name)"
  psql postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$name' AND pid <> pg_backend_pid();"
}

myc_check_postgres() {
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -d "$(myc_database_url)"
  else
    echo "pg_isready no está instalado." >&2
    return 1
  fi
}

myc_backup_database() {
  local output="${1:-$BACKUP_DIR/erp_myc_$(date +%Y%m%d_%H%M%S).sql}"
  mkdir -p "$BACKUP_DIR"
  if ! command -v pg_dump >/dev/null 2>&1; then
    echo "pg_dump no está instalado." >&2
    return 1
  fi
  echo "Generando backup en: $output"
  if ! pg_dump "$(myc_database_url)" --no-owner --no-privileges -f "$output"; then
    rm -f "$output"
    echo "El backup falló; se eliminó el archivo incompleto." >&2
    return 1
  fi
  if [[ ! -s "$output" ]]; then
    rm -f "$output"
    echo "El backup quedó vacío; se eliminó." >&2
    return 1
  fi
  echo "Backup validado: $(du -h "$output" | awk '{print $1}')"
  printf '%s\n' "$output"
}

myc_restore_database() {
  local file="$1"
  [[ -f "$file" && -s "$file" ]] || { echo "Respaldo inválido: $file" >&2; return 1; }
  command -v psql >/dev/null 2>&1 || { echo "psql no está instalado." >&2; return 1; }
  psql "$(myc_database_url)" --set ON_ERROR_STOP=1 -f "$file"
}
