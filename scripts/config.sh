#!/usr/bin/env bash

# Shared MYC System Toolkit configuration. It deliberately derives the root
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

# Backend listener.
# 0.0.0.0 allows physical devices on the local network, such as Expo Go,
# to reach the development API through the Mac's LAN address.
export BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"

# ERP web frontend remains local to this computer.
export FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
export FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# URL consumed by the local ERP web frontend.
# Do not derive this from BACKEND_HOST because 0.0.0.0 is a listener address,
# not the client-facing API address.
export API_HOST="${API_HOST:-127.0.0.1}"
export API_URL="${API_URL:-http://$API_HOST:$BACKEND_PORT/api}"

export BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
