#!/bin/bash

ROOT="/Users/saulcortes/Desktop/myc_erp"

ok() { echo "OK  $1"; }
fail() { echo "NO  $1"; }
line() { echo "----------------------------------------"; }

echo "========================================"
echo "        MYC SYSTEM DOCTOR"
echo "========================================"

cd "$ROOT" || exit 1

line
echo "Proyecto"
[ -d "$ROOT/backend" ] && ok "backend encontrado" || fail "backend no encontrado"
[ -d "$ROOT/frontend" ] && ok "frontend encontrado" || fail "frontend no encontrado"
[ -d "$ROOT/venv" ] && ok "venv encontrado" || fail "venv no encontrado"

line
echo "Backend"
cd "$ROOT/backend" || exit 1
../venv/bin/python --version
../venv/bin/python -m compileall app >/dev/null && ok "compileall backend" || fail "compileall backend"
../venv/bin/alembic current && ok "alembic current" || fail "alembic current"
../venv/bin/python -c "from app.main import app; print('OK  FastAPI:', app.title, len(app.routes), 'rutas')" || fail "FastAPI import"

line
echo "Frontend"
cd "$ROOT/frontend" || exit 1
node -v && ok "node disponible" || fail "node no disponible"
npm -v && ok "npm disponible" || fail "npm no disponible"
[ -f ".env.local" ] && ok ".env.local existe" || fail ".env.local no existe"
grep -n "VITE_API_URL" .env.local 2>/dev/null || fail "VITE_API_URL no encontrado"

line
echo "Git"
cd "$ROOT" || exit 1
git branch --show-current
git status --short

line
echo "Estado general"
echo "Doctor finalizado."
echo "========================================"
