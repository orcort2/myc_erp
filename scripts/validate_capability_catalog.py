#!/usr/bin/env python3
"""Valida catálogo institucional contra bootstrap e inventario HTTP."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
CATALOG = ROOT / "docs/architecture/CATALOGO_INSTITUCIONAL_CAPACIDADES_PERMISOS_ERP_MYC_2026-08-04.md"
INVENTORY = ROOT / "docs/architecture/security/API_ENDPOINT_INVENTORY_2026-08-03.csv"
PERMISSION_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z0-9_*]+)+$")


def parse_catalog() -> tuple[set[str], list[dict[str, str]], set[str], set[str]]:
    module = action = None
    headers: list[str] | None = None
    modules: set[str] = set()
    actions: set[str] = set()
    rows: list[dict[str, str]] = []

    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        module_match = re.match(r"# (\d+)\. (.+)", line)
        if module_match:
            module = module_match.group(2)
            modules.add(module_match.group(1))
        action_match = re.match(r"## (\d+\.\d+)\. (.+)", line)
        if action_match:
            action = action_match.group(2)
            actions.add(action_match.group(1))
        if not line.startswith("|"):
            headers = None
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if "Permiso propuesto" in cells:
            headers = cells
            continue
        if headers and len(cells) == len(headers) and not all(
            set(cell) <= set("-: ") for cell in cells
        ):
            row = dict(zip(headers, cells))
            row["Módulo"] = module or ""
            row["Acción"] = action or ""
            rows.append(row)

    permissions: set[str] = set()
    for row in rows:
        match = re.fullmatch(r"`([^`]+)`", row["Permiso propuesto"])
        if not match:
            raise ValueError(f"Permiso sin formato canónico: {row['Permiso propuesto']}")
        permission = match.group(1)
        if not PERMISSION_PATTERN.fullmatch(permission):
            raise ValueError(f"Clave institucional inválida: {permission}")
        if not row["Módulo"] or not row["Acción"]:
            raise ValueError(f"Microacción sin jerarquía: {permission}")
        permissions.add(permission)

    return permissions, rows, modules, actions


def current_permissions() -> set[str]:
    sys.path.insert(0, str(BACKEND))
    from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS  # noqa: PLC0415

    role_permissions = {
        permission
        for values in ROLE_PERMISSIONS.values()
        for permission in values
        if permission != "*"
    }
    return set(PERMISSIONS.values()) | role_permissions


def inventory_permissions() -> set[str]:
    with INVENTORY.open(newline="", encoding="utf-8") as stream:
        return {
            row["permission"]
            for row in csv.DictReader(stream)
            if row["permission"]
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    catalog_permissions, rows, modules, actions = parse_catalog()
    current = current_permissions()
    inventory = inventory_permissions()
    states = Counter(row["Estado"] for row in rows)

    facts = {
        "modules": len(modules),
        "actions": len(actions),
        "rows": len(rows),
        "existing": states["Existe en backend"],
        "granular": states["Requiere granularización"],
        "catalog_permissions": len(catalog_permissions),
        "current_permissions": len(current),
        "current_matches": len(current & catalog_permissions),
        "current_gaps": len(current - catalog_permissions),
        "inventory_permissions": len(inventory),
        "inventory_catalog_gaps": len(inventory - catalog_permissions),
        "inventory_bootstrap_gaps": len(inventory - current),
        "future_permissions": len(catalog_permissions - current),
    }
    expected = {
        "modules": 36,
        "actions": 213,
        "rows": 798,
        "existing": 305,
        "granular": 493,
        "catalog_permissions": 658,
        "current_permissions": 156,
        "current_matches": 63,
        "current_gaps": 93,
        "inventory_permissions": 83,
        "inventory_catalog_gaps": 29,
        "inventory_bootstrap_gaps": 0,
        "future_permissions": 595,
    }

    for key, value in facts.items():
        print(f"{key}={value}")
    if args.check and facts != expected:
        print("El catálogo, bootstrap o inventario cambió sin reconciliar el snapshot.", file=sys.stderr)
        return 1
    print("Catálogo institucional consistente con el snapshot de Etapa 2B.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
