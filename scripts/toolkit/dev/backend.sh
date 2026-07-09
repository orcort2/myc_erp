#!/bin/bash

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

cd "$BACKEND_DIR" || exit 1

"$UVICORN" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" --reload
