#!/bin/bash

source "/Users/saulcortes/Desktop/myc_erp/scripts/config.sh"

cd "$BACKEND_DIR" || exit 1

echo "Aplicando migraciones Alembic..."
"$ALEMBIC" upgrade head

echo
read -p "Enter para continuar..."