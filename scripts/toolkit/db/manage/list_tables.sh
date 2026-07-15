#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

echo
echo "Tablas disponibles en '$DB_NAME':"
echo "----------------------------------------"

psql "$DB_URL" -Atqc "
  SELECT tablename
  FROM pg_tables
  WHERE schemaname = 'public'
  ORDER BY tablename;
" | nl -w2 -s') '

echo "----------------------------------------"