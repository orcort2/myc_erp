#!/bin/bash
set -e

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

cd "$BACKEND_DIR" || exit 1

"$ALEMBIC" heads

echo
read -p "Enter para continuar..."
