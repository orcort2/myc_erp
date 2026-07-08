#!/bin/bash

ROOT="/Users/saulcortes/Desktop/myc_erp"

clear
echo "===================================="
echo "    HISTORIAL DE MIGRACIONES"
echo "===================================="
echo

cd "$ROOT/backend" || exit 1

../venv/bin/alembic history --verbose

echo
read -p "Presiona Enter para continuar..."
