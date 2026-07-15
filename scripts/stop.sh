#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/toolkit/lib" && pwd)/common.sh"
echo "Deteniendo procesos MYC conocidos..."
myc_stop_port "$BACKEND_PORT"
myc_stop_port "$FRONTEND_PORT"
