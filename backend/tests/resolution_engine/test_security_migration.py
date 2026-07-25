from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions"
    / "b4c6d8e0f2a3_resolution_engine_phase_3_security.py"
)


def migration_namespace():
    namespace = {}
    exec(
        compile(MIGRATION.read_text(encoding="utf-8"), str(MIGRATION), "exec"),
        namespace,
    )
    return namespace


def test_phase_3_migration_follows_phase_2_and_is_reversible():
    namespace = migration_namespace()
    source = MIGRATION.read_text(encoding="utf-8")

    assert namespace["down_revision"] == "9d3e5f7a1b2c"
    assert "def upgrade()" in source
    assert "def downgrade()" in source
    assert "resolution_security_decisions" in source


def test_phase_3_migration_removes_direct_user_foreign_keys():
    namespace = migration_namespace()
    actor_columns = namespace["ACTOR_COLUMNS"]

    assert len(actor_columns) == 11
    assert all(old.endswith("_user_id") for _, old, _, _ in actor_columns)
    assert all(new.endswith("_actor_id") for _, _, new, _ in actor_columns)
    assert all(constraint.endswith("_fkey") for *_, constraint in actor_columns)


def test_phase_3_security_evidence_is_exact_and_append_only():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "fk_resolution_security_decisions_exact_plan" in source
    assert "fk_resolution_security_decisions_exact_simulation" in source
    assert "fk_resolution_security_decisions_simulation_hash" in source
    assert "fk_resolution_security_decisions_authorization" in source
    assert "trg_resolution_security_decisions_immutable" in source
    assert "resolution_engine_prevent_mutation" in source

