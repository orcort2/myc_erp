#!/bin/bash
set -e

source "$(cd "$(dirname "$0")/../.." && pwd)/config.sh"

mkdir -p "$BACKUP_DIR"
"$PROJECT_ROOT/scripts/backup-db.sh"

echo
read -p "Enter para continuar..."