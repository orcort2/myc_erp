#!/bin/bash

ROOT="/Users/saulcortes/Desktop/myc_erp"

clear
echo "===================================="
echo "      NUEVA MIGRACIÓN"
echo "===================================="
echo

read -p "Nombre de la migración: " NAME

if [ -z "$NAME" ]; then
    echo
    echo "No se especificó un nombre."
    exit 1
fi

cd "$ROOT/backend" || exit 1

../venv/bin/alembic revision -m "$NAME"

echo
read -p "Presiona Enter para continuar..."
