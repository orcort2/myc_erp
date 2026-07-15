#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/toolkit/lib" && pwd)/common.sh"
echo "Limpiando cachés generadas..."
find "$BACKEND_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$BACKEND_DIR" -type f -name "*.pyc" -delete
rm -rf "$FRONTEND_DIR/dist" "$FRONTEND_DIR/node_modules/.vite"
echo "Limpieza terminada."
