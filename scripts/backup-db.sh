#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/toolkit/lib" && pwd)/database.sh"
myc_backup_database "$@"
