#!/bin/bash

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

cd "$FRONTEND_DIR" || exit 1

VITE_API_URL="$API_URL" npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
