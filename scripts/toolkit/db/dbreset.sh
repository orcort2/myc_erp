#!/usr/bin/env bash
set -euo pipefail

# Punto de entrada del menú de Base de Datos. El flujo destructivo vive en
# system/reset-db.sh para que CLI y menú ejecuten exactamente la misma ruta.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../system/reset-db.sh" "$@"
