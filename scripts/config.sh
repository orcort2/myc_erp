#!/usr/bin/env bash
# Shared MYC System Toolkit configuration.  It deliberately derives the root
# from this file so the project can be moved or used by another account.

_MYC_CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PROJECT_ROOT="${PROJECT_ROOT:-$(cd "$_MYC_CONFIG_DIR/.." && pwd)}"

export BACKEND_DIR="$PROJECT_ROOT/backend"
export FRONTEND_DIR="$PROJECT_ROOT/frontend"
export VENV_DIR="${VENV_DIR:-$PROJECT_ROOT/venv}"

export PYTHON="$VENV_DIR/bin/python"
export PIP="$VENV_DIR/bin/pip"
export ALEMBIC="$VENV_DIR/bin/alembic"
export UVICORN="$VENV_DIR/bin/uvicorn"

export BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"
export FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
export FRONTEND_PORT="${FRONTEND_PORT:-5174}"
export API_URL="${API_URL:-http://$BACKEND_HOST:$BACKEND_PORT/api}"
export BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
