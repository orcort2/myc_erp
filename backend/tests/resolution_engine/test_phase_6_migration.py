from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "d6e8f0a2b4c5_resolution_engine_phase_6_compensation.py"
)


def migration_namespace():
    namespace = {}
    exec(
        compile(MIGRATION.read_text(encoding="utf-8"), str(MIGRATION), "exec"),
        namespace,
    )
    return namespace


def test_phase_6_migration_is_reversible_and_scoped_to_compensation():
    namespace = migration_namespace()
    source = MIGRATION.read_text(encoding="utf-8")

    assert namespace["down_revision"] == "c5d7e9f1a3b4"
    for table in (
        "resolution_compensation_plans",
        "resolution_compensation_plan_steps",
        "resolution_compensation_executions",
        "resolution_compensation_step_executions",
    ):
        assert f'"{table}"' in source
        assert f'op.drop_table("{table}")' in source
    assert "users" not in source
    assert "workers" not in source
