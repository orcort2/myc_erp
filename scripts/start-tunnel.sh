#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/toolkit/lib" && pwd)/common.sh"

[[ -f "$FRONTEND_DIR/.env.tunnel" ]] && cp "$FRONTEND_DIR/.env.tunnel" "$FRONTEND_DIR/.env.local"
echo "Levantando frontend para API pública en $FRONTEND_HOST:$FRONTEND_PORT..."
(cd "$FRONTEND_DIR" && npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT")
