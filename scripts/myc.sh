#!/bin/bash

ROOT="/Users/saulcortes/Desktop/myc_erp"

db_menu() {
  while true; do
    clear
    echo "========================================"
    echo "              BASE DE DATOS"
    echo "========================================"
    echo "1) Aplicar migraciones"
    echo "2) Estado Alembic"
    echo "3) Historial Alembic"
    echo "4) Heads Alembic"
    echo "5) Crear migración"
    echo "6) Downgrade"
    echo "7) Backup BD"
    echo "8) Restaurar BD"
    echo "0) Volver"
    echo "========================================"
    read -p "Elige una opción: " db_option

    case $db_option in
      1) "$ROOT/scripts/toolkit/db/upgrade.sh" ;;
      2) "$ROOT/scripts/toolkit/db/current.sh" ;;
      3) "$ROOT/scripts/toolkit/db/history.sh" ;;
      4) "$ROOT/scripts/toolkit/db/heads.sh" ;;
      5)
        read -p "Nombre de la migración: " migration_name
        "$ROOT/scripts/toolkit/db/revision.sh" "$migration_name"
        ;;
      6)
        read -p "Revision destino (-1, base o id): " revision
        "$ROOT/scripts/toolkit/db/downgrade.sh" "$revision"
        ;;
      7) "$ROOT/scripts/toolkit/db/backup.sh" ;;
      8)
        read -p "Archivo .sql: " backup_file
        "$ROOT/scripts/toolkit/db/restore.sh" "$backup_file"
        ;;
      0) return ;;
      *) echo "Opción inválida"; sleep 1 ;;
    esac
  done
}

dev_menu() {
  while true; do
    clear
    echo "========================================"
    echo "              DESARROLLO"
    echo "========================================"
    echo "1) Backend"
    echo "2) Frontend"
    echo "3) Build"
    echo "4) Validaciones"
    echo "0) Volver"
    echo "========================================"
    read -p "Elige una opción: " dev_option

    case $dev_option in
      1) "$ROOT/scripts/toolkit/dev/backend.sh" ;;
      2) "$ROOT/scripts/toolkit/dev/frontend.sh" ;;
      3) "$ROOT/scripts/toolkit/dev/build.sh"; read -p "Enter para continuar..." ;;
      4) "$ROOT/scripts/toolkit/dev/check.sh"; read -p "Enter para continuar..." ;;
      0) return ;;
      *) echo "Opción inválida"; sleep 1 ;;
    esac
  done
}

git_menu() {
  while true; do
    clear
    echo "========================================"
    echo "                  GIT"
    echo "========================================"
    echo "1) Status"
    echo "2) Historial"
    echo "3) Ramas"
    echo "0) Volver"
    echo "========================================"
    read -p "Elige una opción: " git_option

    case $git_option in
      1) "$ROOT/scripts/toolkit/git/status.sh"; read -p "Enter para continuar..." ;;
      2) "$ROOT/scripts/toolkit/git/history.sh"; read -p "Enter para continuar..." ;;
      3) "$ROOT/scripts/toolkit/git/branch.sh"; read -p "Enter para continuar..." ;;
      0) return ;;
      *) echo "Opción inválida"; sleep 1 ;;
    esac
  done
}

seed_menu() {
  clear
  echo "========================================"
  echo "                SEED"
  echo "========================================"
  read -p "ID del ETS: " service_order_id
  read -p "Cantidad de equipos: " equipment_count
  "$ROOT/scripts/toolkit/seed/equipment.sh" --service-order-id "$service_order_id" --count "${equipment_count:-1}"
  read -p "Enter para continuar..."
}

while true; do
  clear
  echo "========================================"
  echo "          MYC SYSTEM TOOLKIT"
  echo "========================================"
  echo "1) Desarrollo local"
  echo "2) Desarrollo túnel"
  echo "3) Doctor"
  echo "4) Estado"
  echo "5) Reiniciar local"
  echo "6) Build"
  echo "7) Actualizar"
  echo "8) Backup BD"
  echo "9) Limpiar"
  echo "10) Base de datos"
  echo "11) Desarrollo"
  echo "12) Git"
  echo "13) Seed"
  echo "0) Salir"
  echo "========================================"
  read -p "Elige una opción: " option

  case $option in
    1) "$ROOT/scripts/start-local.sh" ;;
    2) "$ROOT/scripts/start-tunnel.sh" ;;
    3) "$ROOT/scripts/doctor.sh"; read -p "Enter para continuar..." ;;
    4) "$ROOT/scripts/status.sh"; read -p "Enter para continuar..." ;;
    5) "$ROOT/scripts/restart-local.sh" ;;
    6) "$ROOT/scripts/build.sh"; read -p "Enter para continuar..." ;;
    7) "$ROOT/scripts/update.sh"; read -p "Enter para continuar..." ;;
    8) "$ROOT/scripts/backup-db.sh"; read -p "Enter para continuar..." ;;
    9) "$ROOT/scripts/clean.sh"; read -p "Enter para continuar..." ;;
    10) db_menu ;;
    11) dev_menu ;;
    12) git_menu ;;
    13) seed_menu ;;
    0) exit 0 ;;
    *) echo "Opción inválida"; sleep 1 ;;
  esac
done
