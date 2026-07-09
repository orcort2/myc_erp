#!/bin/bash

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

cd "$BACKEND_DIR" || exit 1
"$PYTHON" -m compileall app

cd "$FRONTEND_DIR" || exit 1
npm run build
