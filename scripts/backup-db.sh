#!/bin/bash

ROOT="/Users/saulcortes/Desktop/myc_erp"
DATE=$(date +"%Y_%m_%d_%H%M")
BACKUP_DIR="$ROOT/backups"
FILE="$BACKUP_DIR/erp_myc_$DATE.sql"

mkdir -p "$BACKUP_DIR"

echo "Generando backup en:"
echo "$FILE"

pg_dump erp_myc > "$FILE"

echo "Backup terminado."
