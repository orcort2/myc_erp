#!/bin/bash
set -e

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

cd "$BACKEND_DIR" || exit 1

echo "Migración actual:"
"$ALEMBIC" current

echo
echo "Heads:"
"$ALEMBIC" heads
