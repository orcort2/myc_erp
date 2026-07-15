#!/bin/bash
set -e

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

FILE="${1:-}"

if [ -z "$FILE" ]; then
  echo "Uso: scripts/toolkit/db/restore.sh <archivo.sql>"
  exit 1
fi

if [ ! -f "$FILE" ]; then
  echo "No existe el respaldo: $FILE"
  exit 1
fi

DB_URL="${DATABASE_URL:-postgresql://localhost:5432/erp_myc}"

psql "$DB_URL" -f "$FILE"
