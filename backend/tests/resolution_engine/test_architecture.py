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
)

CORE_FORBIDDEN_IMPORT_PREFIXES = FORBIDDEN_IMPORT_PREFIXES + ("sqlalchemy",)

FUTURE_PHASE_DIRECTORIES = {
    "api",
    "events",
    "gateways",
    "lifecycle",
    "repositories",
    "resolutions",
    "workers",
}

FORBIDDEN_SECURITY_LITERALS = {
    "Administrador",
    "Cliente",
    "users.id",
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
            forbidden = (
                FORBIDDEN_IMPORT_PREFIXES
                if layer == "infrastructure"
                else CORE_FORBIDDEN_IMPORT_PREFIXES
            )
            if module.startswith(forbidden):
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


def test_current_phases_do_not_create_unapproved_packages():
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


def test_security_core_does_not_embed_erp_roles_or_user_table():
    violations = []
    for layer in ("domain", "contracts", "application", "infrastructure"):
        for path in python_files(layer):
            if "security" not in path.name:
                continue
            source = path.read_text(encoding="utf-8")
            for literal in FORBIDDEN_SECURITY_LITERALS:
                if literal in source:
                    violations.append(
                        f"{path.relative_to(PACKAGE_ROOT)} -> {literal}"
                    )

    assert violations == []


def test_phase_4_orchestrator_does_not_cross_into_execution_or_outbox():
    path = PACKAGE_ROOT / "application" / "orchestration.py"
    source = path.read_text(encoding="utf-8")

    assert "ComponentKind.EXECUTOR" not in source
    assert "execute(" not in source
    assert "ResolutionExecution" not in source
    assert "ResolutionOutboxEvent" not in source


def test_lifecycle_state_changes_are_confined_to_its_sql_adapter():
    assignments: list[str] = []
    owned_record_updates = {
        (Path("infrastructure/execution.py"), "execution"),
        (Path("infrastructure/execution.py"), "row"),
        (Path("infrastructure/execution_control.py"), "record"),
        (Path("infrastructure/compensation.py"), "row"),
        (Path("infrastructure/compensation.py"), "execution"),
    }
    for layer in ("domain", "contracts", "application", "infrastructure"):
        for path in python_files(layer):
            relative = path.relative_to(PACKAGE_ROOT)
            if relative in {
                Path("infrastructure/lifecycle.py"),
                Path("infrastructure/persistence/core.py"),
            }:
                continue
            tree = ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
            )
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = (
                    node.targets
                    if isinstance(node, ast.Assign)
                    else [node.target]
                )
                for target in targets:
                    if not (
                        isinstance(target, ast.Attribute)
                        and target.attr == "status"
                    ):
                        continue
                    owner = (
                        target.value.id
                        if isinstance(target.value, ast.Name)
                        else ""
                    )
                    if (relative, owner) not in owned_record_updates:
                        assignments.append(f"{relative}:{owner}")

    assert assignments == []


def test_phase_5_execution_has_no_future_recovery_or_worker_dependencies():
    execution_paths = [
        PACKAGE_ROOT / "application" / "execution.py",
        PACKAGE_ROOT / "application" / "action_runner.py",
        PACKAGE_ROOT / "application" / "outbox.py",
        PACKAGE_ROOT / "infrastructure" / "execution.py",
        PACKAGE_ROOT / "infrastructure" / "execution_control.py",
        PACKAGE_ROOT / "infrastructure" / "outbox.py",
    ]
    forbidden_modules = ("celery", "rq", "apscheduler")
    violations = []
    for path in execution_paths:
        for module in imported_modules(path):
            if module.startswith(forbidden_modules):
                violations.append(f"{path.name} -> {module}")

    assert violations == []
    assert not (PACKAGE_ROOT / "workers").exists()
    assert not (PACKAGE_ROOT / "gateways").exists()


def test_phase_7_audit_adapter_is_read_only_and_has_no_future_dependencies():
    mutating_calls = []
    paths = (
        PACKAGE_ROOT / "infrastructure" / "audit.py",
        PACKAGE_ROOT / "infrastructure" / "audit_projection.py",
    )
    forbidden_modules = ("celery", "rq", "apscheduler", "fastapi")
    imported = []
    for path in paths:
        imported.extend(imported_modules(path))
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if (
                isinstance(function, ast.Attribute)
                and function.attr
                in {
                    "add",
                    "delete",
                    "flush",
                    "commit",
                    "rollback",
                    "execute",
                }
            ):
                mutating_calls.append(function.attr)

    assert mutating_calls == []
    assert not any(
        module.startswith(forbidden_modules) for module in imported
    )


def test_action_handlers_are_invoked_only_by_action_runner():
    violations = []
    for path in python_files("application"):
        if path.name in {
            "action_runner.py",
            "compensation_runner.py",
        }:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "execute"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "handler"
            ):
                violations.append(str(path.relative_to(PACKAGE_ROOT)))

    assert violations == []
