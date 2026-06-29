#!/bin/bash

ROOT="/Users/saulcortes/Desktop/myc_erp"

echo "=================================="
echo " MYC SYSTEM - BUILD CHECK"
echo "=================================="

cd "$ROOT/backend" || exit 1

echo "Verificando backend..."
../venv/bin/python -m compileall app || exit 1

echo "Verificando migraciones..."
../venv/bin/alembic upgrade head || exit 1

echo "Verificando app..."
../venv/bin/python -c "from app.main import app; print(app.title, len(app.routes))" || exit 1

cd "$ROOT/frontend" || exit 1

echo "Compilando frontend..."
npm run build || exit 1

echo "=================================="
echo " TODO OK"
echo "=================================="
