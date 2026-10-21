"""Fase 3B: grafo Alembic y concurrencia real, sólo PostgreSQL desechable."""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url

from app.core.config import settings
from app.models.lab_delivery_item_correction_impact import LabDeliveryItemCorrectionImpact
from app.models.lab_work_order import LabWorkOrder
from app.models.user import User
from app.services.operational_tickets import reopen_work_order_directly
from app.services.service_order_mobile_execution import cohort_revision
from test_lab_delivery_correction_impacts import _deliver, _freeze
from test_service_order_mobile_execution import ctx  # noqa: F401

URL = os.getenv("MYC_PHASE3B_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(not URL, reason="requiere PostgreSQL aislado MYC_PHASE3B_POSTGRES_TEST_URL")
ROOT = Path(__file__).resolve().parents[1]


def test_migration_from_main_head_constraints_and_reversible_empty_table(monkeypatch):
    target = make_url(URL)
    assert target.host == "127.0.0.1" and target.database == "myc_phase3b_test"
    schema = f"phase3b_migration_{uuid.uuid4().hex}"
    admin = create_engine(URL)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(URL, connect_args={"options": f"-csearch_path={schema}"})
    monkeypatch.setattr(settings, "database_url", f"{URL}?options=-csearch_path={schema}")
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["a3c5e7f9b1d2"]
    assert scripts.get_revision("a3c5e7f9b1d2").down_revision == "ffcd7b40ac46"
    try:
        command.upgrade(config, "ffcd7b40ac46")
        inspector = inspect(engine)
        for table in ("lab_delivery_items", "users", "lab_work_order_revisions", "field_sheets"):
            assert inspector.has_table(table)
            assert inspector.get_pk_constraint(table)["constrained_columns"] == ["id"]
        command.upgrade(config, "head")
        inspector = inspect(engine)
        table = "lab_delivery_item_correction_impacts"
        fks = {fk["constrained_columns"][0]: (fk["referred_table"], fk["options"].get("ondelete")) for fk in inspector.get_foreign_keys(table)}
        assert fks == {
            "delivery_item_id": ("lab_delivery_items", "RESTRICT"),
            "created_by_user_id": ("users", "RESTRICT"),
            "resolved_by_user_id": ("users", "RESTRICT"),
            "source_work_order_revision_id": ("lab_work_order_revisions", "SET NULL"),
            "source_field_sheet_id": ("field_sheets", "RESTRICT"),
        }
        index = next(i for i in inspector.get_indexes(table) if i["name"] == "uq_lab_delivery_item_correction_impact_pending")
        assert index["unique"] and "pending" in str(index["dialect_options"]["postgresql_where"])
        assert len(inspector.get_check_constraints(table)) == 2
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "a3c5e7f9b1d2"
        command.downgrade(config, "ffcd7b40ac46")
        assert not inspect(engine).has_table(table)
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_concurrent_reopenings_have_one_winner_and_preserve_delivery(ctx):
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    frozen = _freeze(ctx, delivered["delivery_id"])
    barrier = Barrier(2)
    with ctx["factory"]() as db:
        revision = cohort_revision(list(db.scalars(select(LabWorkOrder))))
    def reopen():
        with ctx["factory"]() as db:
            user = db.get(User, ctx["users"]["Administrador"])
            # Both sessions preload the old row before either obtains the lock.
            db.get(LabWorkOrder, ctx["root"])
            barrier.wait(timeout=10)
            try:
                reopen_work_order_directly(
                    db, ctx["root"], user, signature_policy="preserve", reason="Concurrent correction",
                    equipment_id=ctx["e1"], delivery_impact="documentation_reissue",
                    expected_cohort_revision=revision,
                )
                return 200
            except HTTPException as error:
                assert error.detail["code"] == "COHORT_REVISION_CONFLICT"
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(reopen) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == [200, 409]
    with ctx["factory"]() as db:
        assert len(list(db.scalars(select(LabDeliveryItemCorrectionImpact)))) == 1
    assert _freeze(ctx, delivered["delivery_id"]) == frozen


@pytest.mark.parametrize("impact_status", ["pending", "resolved", "cancelled"])
def test_populated_downgrade_refused_without_losing_history(ctx, monkeypatch, impact_status):
    delivered = _deliver(ctx, [ctx["e1"]], receipt=True)
    frozen = _freeze(ctx, delivered["delivery_id"])
    with ctx["factory"]() as db:
        reopen_work_order_directly(db, ctx["root"], db.get(User, ctx["users"]["Administrador"]),
            signature_policy="preserve", reason="Protect historical impact", equipment_id=ctx["e1"],
            delivery_impact="documentation_reissue")
        impact = db.scalar(select(LabDeliveryItemCorrectionImpact))
        impact.status = impact_status
        db.commit()
        schema = db.scalar(text("SELECT current_schema()"))
        before = db.execute(text("SELECT * FROM lab_delivery_item_correction_impacts")).all()
        indexes = inspect(db.get_bind()).get_indexes("lab_delivery_item_correction_impacts")
    monkeypatch.setattr(settings, "database_url", f"{URL}?options=-csearch_path={schema}")
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.stamp(config, "head")
    with pytest.raises(RuntimeError, match="historical correction impacts must be preserved"):
        command.downgrade(config, "ffcd7b40ac46")
    with ctx["factory"]() as db:
        assert db.execute(text("SELECT * FROM lab_delivery_item_correction_impacts")).all() == before
        assert inspect(db.get_bind()).get_indexes("lab_delivery_item_correction_impacts") == indexes
        assert db.scalar(text("SELECT version_num FROM alembic_version")) == "a3c5e7f9b1d2"
    assert _freeze(ctx, delivered["delivery_id"]) == frozen


def test_concurrent_successive_sheet_corrections_have_one_winner(ctx):
    from app.services.lab_field_sheets import reopen_lab_field_sheet_directly
    with ctx["factory"]() as db:
        reopen_work_order_directly(db, ctx["root"], db.get(User, ctx["users"]["Administrador"]),
            signature_policy="preserve", reason="Authorized correction session", equipment_id=ctx["e1"])
        orders = list(db.scalars(select(LabWorkOrder)))
        revision = cohort_revision(orders)
        versions = {item.id: item.revision_number for item in orders}
    barrier = Barrier(2)
    def reopen():
        with ctx["factory"]() as db:
            user = db.get(User, ctx["users"]["Administrador"])
            db.get(LabWorkOrder, ctx["child"])
            barrier.wait(timeout=10)
            try:
                reopen_lab_field_sheet_directly(db, ctx["child"], ctx["e2"], user,
                    reason="Successive correction", expected_cohort_revision=revision)
                return 200
            except HTTPException as error:
                assert error.detail["code"] == "COHORT_REVISION_CONFLICT"
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(reopen) for _ in range(2)]
        assert sorted(f.result(timeout=30) for f in futures) == [200, 409]
    with ctx["factory"]() as db:
        assert {item.id: item.revision_number for item in db.scalars(select(LabWorkOrder))} == versions
