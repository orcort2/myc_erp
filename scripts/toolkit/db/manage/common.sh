#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/config.sh"

DB_NAME="${DB_NAME:-erp_myc}"
DB_URL="${DATABASE_URL:-postgresql://localhost:5432/$DB_NAME}"

require_psql() {
  if ! command -v psql >/dev/null 2>&1; then
    echo "ERROR: psql no está disponible."
    exit 1
  fi
}

check_database_connection() {
  if ! psql "$DB_URL" -Atqc "SELECT 1;" >/dev/null 2>&1; then
    echo "ERROR: No fue posible conectarse a la base '$DB_NAME'."
    echo "URL utilizada: $DB_URL"
    exit 1
  fi
}

validate_table_name() {
  local table_name="${1:-}"

  if [[ -z "$table_name" ]]; then
    echo "ERROR: Debes indicar una tabla."
    return 1
  fi

  if [[ ! "$table_name" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
    echo "ERROR: Nombre de tabla inválido."
    return 1
  fi

  local exists
  exists="$(
    psql "$DB_URL" -Atqc "
      SELECT EXISTS (
        SELECT 1
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename = '$table_name'
      );
    "
  )"

  if [[ "$exists" != "t" ]]; then
    echo "ERROR: La tabla '$table_name' no existe en el esquema public."
    return 1
  fi
}

get_table_count() {
  local table_name="$1"

  validate_table_name "$table_name"

  psql "$DB_URL" -Atqc \
    "SELECT COUNT(*) FROM public.\"$table_name\";"
}

list_dependent_tables() {
  local table_name="$1"

  validate_table_name "$table_name"

  psql "$DB_URL" -F '|' -Atqc "
    SELECT DISTINCT
      tc.table_name,
      kcu.column_name,
      ccu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.constraint_schema = kcu.constraint_schema
    JOIN information_schema.constraint_column_usage ccu
      ON ccu.constraint_name = tc.constraint_name
     AND ccu.constraint_schema = tc.constraint_schema
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND ccu.table_schema = 'public'
      AND ccu.table_name = '$table_name'
    ORDER BY tc.table_name, kcu.column_name;
  "
}

require_psql
check_database_connection