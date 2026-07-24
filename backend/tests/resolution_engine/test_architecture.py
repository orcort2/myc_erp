from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = (
    Path(__file__).resolve().parents[2] / "app" / "resolution_engine"
)

ALLOWED_INTERNAL_PREFIXES = {
    "domain": ("app.resolution_engine.domain",),
    "contracts": (
        "app.resolution_engine.contracts",
        "app.resolution_engine.domain",
    ),
    "application": (
        "app.resolution_engine.application",
        "app.resolution_engine.contracts",
        "app.resolution_engine.domain",
    ),
    "infrastructure": (
        "app.resolution_engine.infrastructure",
        "app.resolution_engine.contracts",
        "app.resolution_engine.domain",
    ),
}

FORBIDDEN_IMPORT_PREFIXES = (
    "app.models",
    "app.routers",
    "app.schemas",
    "app.services",
    "fastapi",
    "sqlalchemy",
)

FUTURE_PHASE_DIRECTORIES = {
    "api",
    "events",
    "gateways",
    "lifecycle",
    "persistence",
    "repositories",
    "resolutions",
    "workers",
}


def python_files(layer: str) -> list[Path]:
    return sorted((PACKAGE_ROOT / layer).rglob("*.py"))


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


@pytest.mark.parametrize("layer", sorted(ALLOWED_INTERNAL_PREFIXES))
def test_layers_do_not_import_forbidden_erp_or_framework_dependencies(layer):
    violations: list[str] = []
    for path in python_files(layer):
        for module in imported_modules(path):
            if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                violations.append(f"{path.relative_to(PACKAGE_ROOT)} -> {module}")

    assert violations == []


@pytest.mark.parametrize("layer", sorted(ALLOWED_INTERNAL_PREFIXES))
def test_layer_direction_is_enforced(layer):
    allowed = ALLOWED_INTERNAL_PREFIXES[layer]
    violations: list[str] = []
    for path in python_files(layer):
        for module in imported_modules(path):
            if module.startswith("app.resolution_engine") and not module.startswith(
                allowed
            ):
                violations.append(f"{path.relative_to(PACKAGE_ROOT)} -> {module}")

    assert violations == []


def test_phase_one_does_not_create_future_phase_packages():
    present = {
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }

    assert present.isdisjoint(FUTURE_PHASE_DIRECTORIES)


def test_registry_has_no_resolution_type_conditionals():
    registry_path = PACKAGE_ROOT / "application" / "registry.py"
    tree = ast.parse(
        registry_path.read_text(encoding="utf-8"),
        filename=str(registry_path),
    )
    compared_literals = {
        comparator.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        for comparator in node.comparators
        if isinstance(comparator, ast.Constant)
        and isinstance(comparator.value, str)
        and "." in comparator.value
    }

    assert compared_literals == set()
