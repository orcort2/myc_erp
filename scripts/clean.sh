#!/bin/bash

ROOT="/Users/saulcortes/Desktop/myc_erp"

echo "Limpiando archivos temporales..."

find "$ROOT/backend" -type d -name "__pycache__" -prune -exec rm -rf {} +
find "$ROOT/backend" -type f -name "*.pyc" -delete

rm -rf "$ROOT/frontend/dist"
rm -rf "$ROOT/frontend/node_modules/.vite"

echo "Limpieza terminada."
