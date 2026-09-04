from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.db import Base
import app.models  # noqa: F401


ROOT = Path(__file__).resolve().parents[2]


def test_current_revision_is_the_single_head() -> None:
    """El nombre del test es la garantía real: un único head en la cadena de
    migraciones. La revisión concreta cambia con cada migración nueva y no es
    parte del contrato -- hardcodearla (como "b0b560e714db", agregada antes
    de toda la cadena de este WIP y nunca actualizada) sólo produce un test
    frágil que se rompe con cada migración legítima sin detectar nada real.
    Una segunda cabeza (branch sin mergear) sí sería un problema genuino."""
    config = Config(ROOT / "backend" / "alembic.ini")
    config.set_main_option(
        "script_location", str(ROOT / "backend" / "migrations")
    )
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1, f"se esperaba un único head de Alembic, se encontraron {len(heads)}: {heads}"


def test_schema_metadata_matches_legacy_integrity_contracts() -> None:
    participants = Base.metadata.tables["communication_participants"]
    assert {index.name for index in participants.indexes} == {
        "ix_communication_participants_user_id"
    }
    assert not participants.constraints.difference(
        {participants.primary_key, *participants.foreign_key_constraints}
    )

    work_orders = Base.metadata.tables["service_work_orders"]
    work_order_index = next(
        index
        for index in work_orders.indexes
        if index.name == "ix_service_work_orders_work_order_number"
    )
    assert work_order_index.unique is False
    assert any(
        constraint.columns.keys() == ["work_order_number"]
        for constraint in work_orders.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    )


def test_historical_downgrades_own_only_their_objects() -> None:
    signature_fix = (
        ROOT
        / "backend/migrations/versions/28eed747a29b_fix_service_order_signature_columns.py"
    ).read_text(encoding="utf-8")
    duplicate_table = (
        ROOT
        / "backend/migrations/versions/c3fb78821edc_add_service_order_signatures.py"
    ).read_text(encoding="utf-8")
    advisor = (
        ROOT
        / "backend/migrations/versions/917baf3a5378_add_quotation_advisor.py"
    ).read_text(encoding="utf-8")

    assert "op.create_table(\n        \"service_order_signatures\"" in signature_fix
    assert "DROP TABLE IF EXISTS service_order_signatures" in duplicate_table
    assert "quotations_advisor_id_fkey" in advisor
