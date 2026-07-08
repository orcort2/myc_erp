#!/bin/bash

source "/Users/saulcortes/Desktop/myc_erp/scripts/config.sh"

clear
echo "===================================="
echo "      ESTADO DE ALEMBIC"
echo "===================================="
echo

cd "$BACKEND_DIR" || exit 1

echo "Migración actual:"
"$ALEMBIC" current

echo
echo "Heads:"
"$ALEMBIC" heads

echo
read -p "Presiona Enter para continuar..."