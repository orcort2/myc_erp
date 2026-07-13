#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-5173}"
CHROME="${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
OUTPUT_DIR="$ROOT_DIR/output/pdf/field-sheet-lab"

templates=(
  anemometro angulimetro bascula calibradores cronometro detector_gases
  dimensional electrica flujo general maestro_altura par_torsional pesas
  presion reglas sonido tacometro temperatura tld_6_canales tld
  valvula_seguridad verificacion_equipos copa
)

mkdir -p "$OUTPUT_DIR"

for template in "${templates[@]}"; do
  "$CHROME" \
    --headless=new \
    --disable-gpu \
    --no-sandbox \
    --run-all-compositor-stages-before-draw \
    --virtual-time-budget=2500 \
    --print-to-pdf="$OUTPUT_DIR/$template.pdf" \
    "http://127.0.0.1:$PORT/dashboard/field-sheet-lab?template=$template&print=1"
  echo "$template.pdf"
done

