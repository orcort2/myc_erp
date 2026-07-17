#!/usr/bin/env bash

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PROJECT_ROOT="$ROOT"
export MYC_INTERACTIVE=1

run_and_pause() {
  "$ROOT/scripts/myc" "$@"
  local result=$?
  read -r -p "Enter para continuar..." _
  return $result
}

db_menu() {
  while true; do
    clear
    cat <<'EOF'
========================================
              BASE DE DATOS
========================================
1) Aplicar migraciones
2) Estado Alembic
3) Historial Alembic
4) Heads Alembic
5) Crear migración
6) Downgrade
7) Backup BD
8) Restaurar BD
9) Administrar tablas
10) Resetear BD de desarrollo
0) Volver
========================================
EOF

    read -r -p "Elige una opción: " option

    case "$option" in
      1)
        run_and_pause migrate
        ;;
      2)
        "$ROOT/scripts/toolkit/db/current.sh"
        read -r -p "Enter para continuar..." _
        ;;
      3)
        "$ROOT/scripts/toolkit/db/history.sh"
        read -r -p "Enter para continuar..." _
        ;;
      4)
        "$ROOT/scripts/toolkit/db/heads.sh"
        read -r -p "Enter para continuar..." _
        ;;
      5)
        read -r -p "Nombre de la migración: " name
        "$ROOT/scripts/toolkit/db/revision.sh" "$name"
        read -r -p "Enter para continuar..." _
        ;;
      6)
        read -r -p "Revision destino (-1, base o id): " revision
        "$ROOT/scripts/toolkit/db/downgrade.sh" "$revision"
        read -r -p "Enter para continuar..." _
        ;;
      7)
        run_and_pause backup
        ;;
      8)
        read -r -p "Archivo .sql: " file
        run_and_pause restore "$file"
        ;;
      9)
        "$ROOT/scripts/toolkit/db/manage/menu.sh"
        ;;
      10)
        read -r -p "ADVERTENCIA: se eliminará toda la BD. Escribe REINICIAR ERP para continuar: " confirmation
        if [[ "$confirmation" == "REINICIAR ERP" ]]; then
          MYC_ALLOW_RESET='REINICIAR ERP' "$ROOT/scripts/toolkit/db/dbreset.sh"
        else
          echo "Reset cancelado."
        fi
        read -r -p "Enter para continuar..." _
        ;;
      0)
        return
        ;;
      *)
        echo "Opción inválida"
        sleep 1
        ;;
    esac
  done
}

while true; do
  clear
  cat <<'EOF'
========================================
          MYC SYSTEM TOOLKIT
========================================
1) Desarrollo local
2) Desarrollo túnel
3) Doctor
4) Estado
5) Reiniciar local
6) Build
7) Actualizar
8) Backup BD
9) Limpiar
10) Base de datos
11) Git status
12) SAT
13) Seed de equipos
0) Salir
========================================
EOF
  read -r -p "Elige una opción: " option
  case "$option" in
    1) "$ROOT/scripts/myc" dev local ;;
    2) "$ROOT/scripts/myc" dev tunnel ;;
    3) run_and_pause doctor ;;
    4) run_and_pause status ;;
    5) "$ROOT/scripts/myc" restart ;;
    6) run_and_pause build ;;
    7) run_and_pause update ;;
    8) run_and_pause backup ;;
    9) run_and_pause clean ;;
    10) db_menu ;;
    11) run_and_pause git status ;;
    12) run_and_pause sat status ;;
    13)
      read -r -p "ID del ETS: " service_order_id
      read -r -p "Cantidad de equipos: " equipment_count
      run_and_pause seed --service-order-id "$service_order_id" --count "${equipment_count:-1}"
      ;;
    0) exit 0 ;;
    *) echo "Opción inválida"; sleep 1 ;;
  esac
done
