#!/bin/bash
set -e

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

NAME="$*"

if [ -z "$NAME" ]; then
    echo "Uso: scripts/toolkit/db/revision.sh \"nombre de migracion\""
    exit 1
fi

cd "$BACKEND_DIR" || exit 1

"$ALEMBIC" revision -m "$NAME"
