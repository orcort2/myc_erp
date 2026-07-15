#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/database.sh"

echo "Inicialización segura de MYC System"
myc_require_venv
myc_check_postgres
if ! myc_database_exists; then
  echo "Creando base de datos $(myc_database_name)..."
  myc_create_database
fi
myc_run_alembic upgrade head
echo "Base inicializada y migraciones aplicadas."
echo "Para cargar catálogos SAT ejecuta: scripts/myc sat import"
echo "La creación de administradores permanece en el flujo de usuarios para no aceptar contraseñas por línea de comandos."
