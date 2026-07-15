#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

TABLE="${1:-}"

if [[ -n "$TABLE" ]]; then
  validate_table_name "$TABLE"
  COUNT="$(get_table_count "$TABLE")"

  echo
  echo "Tabla: $TABLE"
  echo "Registros: $COUNT"
  exit 0
fi

echo
echo "Conteo de registros por tabla"
echo "----------------------------------------"

while IFS= read -r table_name; do
  count="$(get_table_count "$table_name")"
  printf "%-48s %12s\n" "$table_name" "$count"
done < <(
  psql "$DB_URL" -Atqc "
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY tablename;
  "
)

echo "----------------------------------------"