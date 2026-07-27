from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "c5d7e9f1a3b4_resolution_engine_phase_5_review.py"
)


def migration_namespace():
    namespace = {}
    exec(
        compile(MIGRATION.read_text(encoding="utf-8"), str(MIGRATION), "exec"),
        namespace,
    )
    return namespace


def test_phase_5_review_migration_is_minimal_and_reversible():
    namespace = migration_namespace()
    source = MIGRATION.read_text(encoding="utf-8")

    assert namespace["down_revision"] == "b4c6d8e0f2a3"
    assert '"resolution_outbox_events"' in source
    assert '"failed_at"' in source
    assert "op.add_column" in source
    assert "op.drop_column" in source
