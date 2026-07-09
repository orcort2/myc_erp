#!/bin/bash

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

cd "$BACKEND_DIR" || exit 1

"$PYTHON" "$PROJECT_ROOT/scripts/toolkit/seed/equipment.py" "$@"
