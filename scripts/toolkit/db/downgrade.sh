#!/bin/bash
set -e

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

REVISION="${1:-}"

if [ -z "$REVISION" ]; then
  echo "Uso: scripts/toolkit/db/downgrade.sh <revision>"
  echo "Ejemplo: scripts/toolkit/db/downgrade.sh -1"
  exit 1
fi

cd "$BACKEND_DIR" || exit 1

"$ALEMBIC" downgrade "$REVISION"
