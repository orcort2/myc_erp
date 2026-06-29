#!/bin/bash

ROOT="/Users/saulcortes/Desktop/myc_erp"

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
    0) exit 0 ;;
    *) echo "Opción inválida"; sleep 1 ;;
  esac
done
