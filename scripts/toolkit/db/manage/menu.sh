#!/usr/bin/env bash

set -euo pipefail

MANAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pause_menu() {
  read -r -p "Enter para continuar..." _
}

while true; do
  clear

  cat <<'EOF'
========================================
          ADMINISTRAR TABLAS
========================================
1) Ver tablas
2) Conteo de todas las tablas
3) Conteo de una tabla
4) Vaciar o eliminar registros de una tabla
5) Vaciar clientes sin historial
0) Volver
========================================
EOF

  read -r -p "Elige una opción: " option

  case "$option" in
    1)
      "$MANAGE_DIR/list_tables.sh"
      pause_menu
      ;;
    2)
      "$MANAGE_DIR/table_counts.sh"
      pause_menu
      ;;
    3)
      read -r -p "Nombre exacto de la tabla: " table_name
      "$MANAGE_DIR/table_counts.sh" "$table_name"
      pause_menu
      ;;
    4)
      read -r -p "Nombre exacto de la tabla: " table_name
      "$MANAGE_DIR/truncate_table.sh" "$table_name"
      pause_menu
      ;;
    5) 
      "$MANAGE_DIR/purge_clients.sh"
      pause_menu
      ;;  
    0)
      exit 0
      ;;
    *)
      echo "Opción inválida."
      sleep 1
      ;;
  esac
done