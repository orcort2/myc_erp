#!/bin/bash
set -e

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

cd "$BACKEND_DIR" || exit 1

echo "Aplicando migraciones Alembic..."
"$ALEMBIC" upgrade head
