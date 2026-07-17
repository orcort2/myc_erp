#!/usr/bin/env bash

set -o pipefail

MYC_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$MYC_LIB_DIR/../../config.sh"

myc_pause() {
  if [[ "${MYC_INTERACTIVE:-0}" == "1" ]]; then
    read -r -p "Enter para continuar..." _
  fi
}

myc_require_venv() {
  if [[ ! -x "$PYTHON" ]]; then
    echo "Entorno virtual no disponible: $VENV_DIR" >&2
    echo "Crea el entorno en la raíz del proyecto (venv) o define VENV_DIR." >&2
    return 1
  fi
}

myc_run_alembic() {
  myc_require_venv || return
  (cd "$BACKEND_DIR" && "$ALEMBIC" "$@")
}

myc_sat_catalog_version() {
  local version_file version
  if [[ -n "${SAT_CATALOG_VERSION:-}" ]]; then
    printf '%s\n' "$SAT_CATALOG_VERSION"
    return
  fi
  version_file="$BACKEND_DIR/resources/sat/VERSION.txt"
  [[ -f "$version_file" ]] || { echo "No se encontró la versión SAT: $version_file" >&2; return 1; }
  version="$(grep -Eo '[0-9]{8}' "$version_file" | tail -n 1)"
  [[ -n "$version" ]] || { echo "No se encontró una versión YYYYMMDD en $version_file" >&2; return 1; }
  printf '%s\n' "$version"
}

myc_listener_pids() {
  lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null || true
}

myc_is_myc_process() {
  local pid="$1" command
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ "$command" == *"$PROJECT_ROOT"* || "$command" == *"uvicorn app.main:app"* || "$command" == *"vite"* ]]
}

myc_stop_port() {
  local port="$1" pid
  local found=0
  for pid in $(myc_listener_pids "$port"); do
    found=1
    if myc_is_myc_process "$pid"; then
      kill "$pid" && echo "Proceso MYC detenido en puerto $port (PID $pid)."
    else
      echo "No se detuvo PID $pid en puerto $port: no pertenece claramente a MYC." >&2
    fi
  done
  [[ "$found" == "0" ]] && echo "No hay proceso escuchando en puerto $port."
}
