#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/toolkit/lib" && pwd)/common.sh"

echo "MYC SYSTEM - BUILD CHECK"
myc_require_venv
(cd "$BACKEND_DIR" && "$PYTHON" -m compileall app && "$PYTHON" -c "from app.main import app; print(app.title, len(app.routes))")
(cd "$FRONTEND_DIR" && npm run build)
echo "TODO OK"
