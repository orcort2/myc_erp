"""Cierre UX 2026-09: pruebas de seguridad para el script de limpieza LAB
local (app/scripts/reset_lab_dev_data.py). No ejerce el borrado real contra
una base viva -- eso se validó manualmente contra Postgres local desechable
(dry-run + --confirm, ver docs/entrega). Aquí sólo se cubre lo que puede
probarse sin una base real: el guard de entorno/host, y que la lista de
tipos de ticket LAB del script nunca quede desincronizada en silencio de
TICKET_TYPES del modelo (si alguien agrega un tipo nuevo no-LAB al modelo,
este test obliga a decidir explícitamente si el reset debe incluirlo)."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.models.operational_ticket import TICKET_TYPES
from app.scripts.reset_lab_dev_data import LAB_TICKET_TYPES, _assert_safe_environment


def test_lab_ticket_types_are_exactly_the_models_ticket_types_today():
    """Hoy los 7 tipos de OperationalTicket son todos LAB (ver
    operational_ticket.py, docstring: 'inicialmente soporta reaperturas
    LAB'). Si esto deja de ser cierto, este test falla a propósito -- el
    script no debe truncar silenciosamente tipos no-LAB nuevos."""
    assert set(LAB_TICKET_TYPES) == set(TICKET_TYPES)


def test_assert_safe_environment_aborts_on_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(SystemExit, match="producción"):
        _assert_safe_environment()


def test_assert_safe_environment_aborts_on_non_local_host(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(
        settings, "database_url", "postgresql+psycopg://prod-db.internal:5432/erp_myc",
    )
    with pytest.raises(SystemExit, match="localhost"):
        _assert_safe_environment()


def test_assert_safe_environment_allows_local_dev(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "database_url", "postgresql+psycopg://localhost:5432/erp_myc")
    _assert_safe_environment()  # no debe lanzar
