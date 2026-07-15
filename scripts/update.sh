#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/toolkit/lib" && pwd)/common.sh"
echo "MYC SYSTEM UPDATE"
(cd "$PROJECT_ROOT" && git pull)
(cd "$BACKEND_DIR" && "$PIP" install -r requirements.txt)
myc_run_alembic upgrade head
(cd "$FRONTEND_DIR" && npm install)
"$PROJECT_ROOT/scripts/build.sh"
"$PROJECT_ROOT/scripts/doctor.sh"
