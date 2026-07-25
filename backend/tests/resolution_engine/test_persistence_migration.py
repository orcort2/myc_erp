import ast
from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "9d3e5f7a1b2c_add_resolution_engine_persistence.py"
)


def migration_tree():
    return ast.parse(MIGRATION.read_text(encoding="utf-8"))


def called_table_names(function_name: str, operation_name: str) -> set[str]:
    tree = migration_tree()
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    names = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != operation_name or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            names.add(first.value)
    return names


def test_migration_has_expected_parent_and_all_tables_are_reversible():
    namespace = {}
    exec(
        compile(MIGRATION.read_text(encoding="utf-8"), str(MIGRATION), "exec"),
        namespace,
    )

    assert namespace["down_revision"] == "8c2d4e6f7a9b"
    created = called_table_names("upgrade", "create_table")
    dropped = called_table_names("downgrade", "drop_table")
    assert len(created) == 21
    assert created == dropped


def test_migration_installs_database_level_historical_guards():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "resolution_engine_prevent_mutation" in source
    assert "resolution_engine_prevent_delete" in source
    assert "resolution_engine_guard_plan_update" in source
    assert "resolution_engine_guard_plan_child" in source
    assert "BEFORE UPDATE OR DELETE" in source
    assert "OLD.status <> 'draft'" in source


def test_migration_adds_and_removes_deferred_root_foreign_keys():
    created = called_table_names("upgrade", "create_foreign_key")
    dropped = called_table_names("downgrade", "drop_constraint")

    assert created == {
        "fk_resolutions_current_context_same_resolution",
        "fk_resolutions_current_plan_same_resolution",
        "fk_resolutions_current_strategy_same_resolution",
    }
    assert created.issubset(dropped)
