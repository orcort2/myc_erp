#!/usr/bin/env python3
"""Generate or verify the canonical FastAPI access inventory."""

from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402
from app.security.api_access import build_endpoint_inventory  # noqa: E402


DEFAULT_OUTPUT = ROOT / "docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv"


def render_inventory() -> str:
    rows = build_endpoint_inventory(app)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render_inventory()
    if args.check:
        if not args.output.exists() or args.output.read_bytes() != rendered.encode("utf-8"):
            print(f"Inventario desactualizado: {args.output}", file=sys.stderr)
            return 1
        print(f"Inventario vigente: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Inventario generado: {args.output} ({len(build_endpoint_inventory(app))} operaciones)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
