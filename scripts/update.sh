#!/bin/bash

ROOT="/Users/saulcortes/Desktop/myc_erp"

echo "========================================"
echo "        MYC SYSTEM UPDATE"
echo "========================================"

cd "$ROOT" || exit 1

echo "Actualizando Git..."
git pull || exit 1

echo "Instalando dependencias backend..."
cd "$ROOT/backend" || exit 1
../venv/bin/pip install -r requirements.txt || exit 1

echo "Aplicando migraciones..."
../venv/bin/alembic upgrade head || exit 1

echo "Instalando dependencias frontend..."
cd "$ROOT/frontend" || exit 1
npm install || exit 1

echo "Build general..."
"$ROOT/scripts/build.sh" || exit 1

echo "Doctor..."
"$ROOT/scripts/doctor.sh"

echo "Sistema actualizado correctamente."
