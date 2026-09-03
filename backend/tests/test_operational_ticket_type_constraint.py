from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.models  # noqa: F401
from app.core.db import Base
from app.models.operational_ticket import OperationalTicket, TICKET_TYPES
from app.models.user import Role, User


# Tipos vigentes al momento de 9f3a2c7d1e84 -- NUNCA se toca esa migración
# (ver docstring). Tipos agregados por migraciones posteriores (hoy:
# 'partial_delivery' via c2d4e6f8a0b1) se validan aparte, no aquí.
EXPECTED_TYPES = {
    "reopen_work_order",
    "manual_myc_folio",
    "linked_folio",
    "partial_close",
    "certificate_folio_block",
    "field_sheet_template_request",
    "field_sheet_reopen",
    "reception_date_change",
}
TYPES_ADDED_AFTER_9F3A2C7D1E84 = {"partial_delivery"}


def _migration_module():
    path = Path(__file__).parents[1] / "migrations/versions/9f3a2c7d1e84_add_reception_date_change_ticket_type.py"
    spec = importlib.util.spec_from_file_location("ticket_type_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ticket_type_model_and_migration_contract_match():
    migration = _migration_module()
    assert set(TICKET_TYPES) == EXPECTED_TYPES | TYPES_ADDED_AFTER_9F3A2C7D1E84
    assert set(migration._CURRENT_TYPES) == EXPECTED_TYPES
    assert migration.down_revision == "b0b560e714db"
    assert set(migration._PREVIOUS_TYPES) == EXPECTED_TYPES - {"reception_date_change"}


def test_all_ticket_types_are_valid_and_arbitrary_type_is_rejected():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        role = Role(name="Constraint", description="Constraint")
        user = User(
            username="constraint-user",
            email="constraint@example.test",
            full_name="Constraint User",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            role_id=None,
            roles=[role],
        )
        db.add(user)
        db.flush()
        for ticket_type in TICKET_TYPES:
            db.add(OperationalTicket(
                type=ticket_type,
                status="pending",
                requested_by_user_id=user.id,
                reason="Prueba",
                description="Tipo permitido",
            ))
        db.commit()
        db.add(OperationalTicket(
            type="arbitrary_type",
            status="pending",
            requested_by_user_id=user.id,
            reason="Prueba",
            description="Tipo inválido",
        ))
        with pytest.raises(IntegrityError):
            db.commit()
