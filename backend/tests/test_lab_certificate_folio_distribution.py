"""Acción administrativa "Distribuir folios disponibles".

Repara equipo LAB de cliente operativo externo que quedó atrapado en
service_type in (accredited, traceable) + certificate_folio=NULL +
folio_status="pending" -- el estado que _assign_equipment_service_core ahora
bloquea en el alta (ver test_lab_phase2_integrated_alta.py), pero que ya
podía existir en datos legacy antes de ese fix, o simplemente porque el pool
todavía no se autorizaba en el momento del alta.

No migra datos automáticamente ni inventa folios: sólo consume folios ya
resueltos de un ticket certificate_folio_block del MISMO operator_client_id,
todo-o-nada por prefijo, con locking igual al que ya usa
_assign_equipment_service_core, y auditado.
"""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base
from app.models.audit_log import AuditLog
from app.models.client import Client
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.operational_ticket import OperationalTicket
from app.models.user import Role, User
from app.schemas.lab_work_order import LabWorkOrderCreate
from app.services.lab_work_orders import (
    create_work_order,
    distribute_pending_certificate_folios,
    preview_pending_certificate_folio_distribution,
)


@pytest.fixture()
def folio_context():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        admin_role = Role(name="Administrador", description="Administrador")
        db.add(admin_role)
        db.flush()
        admin = User(
            username="lab-admin",
            email="lab-admin@example.test",
            full_name="LAB admin",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            role_id=admin_role.id,
            roles=[admin_role],
        )
        db.add(admin)
        client_a = Client(legal_name="Tenant A", commercial_name="Tenant A")
        client_b = Client(legal_name="Tenant B", commercial_name="Tenant B")
        db.add_all([client_a, client_b])
        db.commit()
        yield factory, admin.id, client_a.id, client_b.id


def create_payload(**extra) -> dict:
    return {
        "reception_date": "2026-08-13",
        "client_name": "Cliente LAB",
        "address": "Av. Prueba 123",
        "contact_name": "Persona Cliente",
        "contact_phone": "3312345678",
        "contact_email": "cliente@example.com",
        "postal_code": "45601",
        "city": "Tlaquepaque",
        "state_name": "Jalisco",
        "purchase_order": "OC-123",
        "notes": "Recepción LAB",
        **extra,
    }


def make_order(db, admin_id, operator_client_id: int) -> int:
    admin = db.get(User, admin_id)
    order = create_work_order(
        db, LabWorkOrderCreate(**create_payload()), admin, operator_client_id=operator_client_id
    )
    return order.id


def make_pending_equipment(
    db, order_id: int, *, service_type: str, position: int, instrument: str = "Instrumento"
) -> int:
    equipment = LabWorkOrderEquipment(
        work_order_id=order_id,
        position=position,
        instrument=instrument,
        brand="MYC Test",
        identification=f"ID-{position}",
        serial_number=f"SER-{position}",
        is_good_condition=True,
        service_type=service_type,
        folio_status="pending",
        certificate_folio=None,
    )
    db.add(equipment)
    db.commit()
    return equipment.id


def make_resolved_ticket(
    db, admin_id: int, operator_client_id: int, *, myca: list[str], myct: list[str], used: dict | None = None
) -> int:
    ticket = OperationalTicket(
        type="certificate_folio_block",
        status="resolved",
        work_order_id=None,
        operator_client_id=operator_client_id,
        requested_by_user_id=admin_id,
        reason="Prueba",
        description="Reserva de folios de prueba",
        accredited_quantity=len(myca),
        traceable_quantity=len(myct),
        resolution_snapshot={"folios": {"MYCA": myca, "MYCT": myct}, "used": used or {}},
    )
    db.add(ticket)
    db.commit()
    return ticket.id


def test_preview_never_mutates_and_reports_exact_counts(folio_context):
    factory, admin_id, client_a, _client_b = folio_context
    with factory() as db:
        order_id = make_order(db, admin_id, client_a)
        make_pending_equipment(db, order_id, service_type="accredited", position=1)
        make_pending_equipment(db, order_id, service_type="accredited", position=2)
        make_pending_equipment(db, order_id, service_type="traceable", position=3)
        make_resolved_ticket(
            db, admin_id, client_a,
            myca=["MYCA-01-26-0001", "MYCA-01-26-0002"], myct=["MYCT-01-26-0001"],
        )

        preview = preview_pending_certificate_folio_distribution(db, order_id)
        assert preview.pending_accredited_count == 2
        assert preview.pending_traceable_count == 1
        assert preview.available_myca_count == 2
        assert preview.available_myct_count == 1
        assert [item.folio for item in preview.items] == [
            "MYCA-01-26-0001", "MYCA-01-26-0002", "MYCT-01-26-0001",
        ]
        assert [item.position for item in preview.items] == [1, 2, 3]

        # Sólo lectura: nada mutó.
        db.rollback()
        equipment = db.scalars(
            select(LabWorkOrderEquipment).where(LabWorkOrderEquipment.work_order_id == order_id)
        ).all()
        assert all(item.folio_status == "pending" and item.certificate_folio is None for item in equipment)


def test_distribute_assigns_all_in_position_order_and_marks_folios_used(folio_context):
    factory, admin_id, client_a, _client_b = folio_context
    with factory() as db:
        order_id = make_order(db, admin_id, client_a)
        first_id = make_pending_equipment(db, order_id, service_type="accredited", position=1)
        second_id = make_pending_equipment(db, order_id, service_type="accredited", position=2)
        ticket_id = make_resolved_ticket(
            db, admin_id, client_a, myca=["MYCA-01-26-0001", "MYCA-01-26-0002"], myct=[],
        )
        admin = db.get(User, admin_id)

        result = distribute_pending_certificate_folios(db, order_id, admin)
        assert {item.equipment_id: item.folio for item in result.assigned} == {
            first_id: "MYCA-01-26-0001",
            second_id: "MYCA-01-26-0002",
        }

        first = db.get(LabWorkOrderEquipment, first_id)
        second = db.get(LabWorkOrderEquipment, second_id)
        assert first.certificate_folio == first.automatic_certificate_folio == "MYCA-01-26-0001"
        assert second.certificate_folio == second.automatic_certificate_folio == "MYCA-01-26-0002"
        assert first.folio_status == second.folio_status == "reserved"

        ticket = db.get(OperationalTicket, ticket_id)
        used = ticket.resolution_snapshot["used"]
        assert set(used) == {"MYCA-01-26-0001", "MYCA-01-26-0002"}
        assert used["MYCA-01-26-0001"]["equipment_id"] == first_id

        log = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "lab_work_order.pending_certificate_folios_distributed",
                AuditLog.entity_id == order_id,
            )
        )
        assert log is not None
        assert log.new_values["operator_client_id"] == client_a
        assert len(log.new_values["assigned"]) == 2


def test_distribute_is_idempotent_on_rerun(folio_context):
    factory, admin_id, client_a, _client_b = folio_context
    with factory() as db:
        order_id = make_order(db, admin_id, client_a)
        make_pending_equipment(db, order_id, service_type="accredited", position=1)
        make_resolved_ticket(db, admin_id, client_a, myca=["MYCA-01-26-0001"], myct=[])
        admin = db.get(User, admin_id)

        first_run = distribute_pending_certificate_folios(db, order_id, admin)
        assert len(first_run.assigned) == 1

        second_run = distribute_pending_certificate_folios(db, order_id, admin)
        assert second_run.assigned == []


def test_distribute_is_all_or_nothing_when_pool_is_insufficient(folio_context):
    factory, admin_id, client_a, _client_b = folio_context
    with factory() as db:
        order_id = make_order(db, admin_id, client_a)
        first_id = make_pending_equipment(db, order_id, service_type="accredited", position=1)
        second_id = make_pending_equipment(db, order_id, service_type="accredited", position=2)
        make_resolved_ticket(db, admin_id, client_a, myca=["MYCA-01-26-0001"], myct=[])
        admin = db.get(User, admin_id)

        with pytest.raises(Exception) as excinfo:
            distribute_pending_certificate_folios(db, order_id, admin)
        assert getattr(excinfo.value, "status_code", None) == 409
        detail = excinfo.value.detail
        assert detail["code"] == "LAB_CERTIFICATE_FOLIOS_INSUFFICIENT"
        assert detail["prefix"] == "MYCA"
        assert detail["required"] == 2
        assert detail["available"] == 1

        db.rollback()
        first = db.get(LabWorkOrderEquipment, first_id)
        second = db.get(LabWorkOrderEquipment, second_id)
        assert first.folio_status == "pending" and first.certificate_folio is None
        assert second.folio_status == "pending" and second.certificate_folio is None


def test_distribute_never_touches_linked_or_another_tenants_folios(folio_context):
    factory, admin_id, client_a, client_b = folio_context
    with factory() as db:
        order_id = make_order(db, admin_id, client_a)
        accredited_id = make_pending_equipment(db, order_id, service_type="accredited", position=1)
        linked_id = make_pending_equipment(db, order_id, service_type="linked", position=2)
        # Pool de OTRO tenant -- nunca debe ser visible para client_a.
        make_resolved_ticket(db, admin_id, client_b, myca=["MYCA-99-26-9999"], myct=[])
        make_resolved_ticket(db, admin_id, client_a, myca=["MYCA-01-26-0001"], myct=[])
        admin = db.get(User, admin_id)

        preview = preview_pending_certificate_folio_distribution(db, order_id)
        assert preview.pending_accredited_count == 1
        assert preview.available_myca_count == 1  # sólo el pool propio, no el de client_b

        result = distribute_pending_certificate_folios(db, order_id, admin)
        assert [item.equipment_id for item in result.assigned] == [accredited_id]
        assert result.assigned[0].folio == "MYCA-01-26-0001"

        linked = db.get(LabWorkOrderEquipment, linked_id)
        assert linked.folio_status == "pending" and linked.certificate_folio is None


def test_postgresql_concurrent_distribution_across_two_orders_never_reuses_a_folio():
    """Regresión PostgreSQL real: _available_external_certificate_folios usa
    SELECT ... FOR UPDATE sobre la fila del ticket certificate_folio_block --
    SQLite no aplica bloqueo de fila real entre transacciones concurrentes,
    así que sólo Postgres puede demostrar que dos distribuciones concurrentes
    (dos OT distintas, mismo pool de dos folios) nunca consumen el mismo
    folio dos veces."""
    database_url = os.getenv("LAB_POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("requiere LAB_POSTGRES_TEST_URL para probar locking PostgreSQL real")

    from sqlalchemy import text as sa_text

    schema = f"lab_certificate_folio_distribution_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(sa_text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(database_url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as db:
            role = Role(name="Administrador", description="Administrador")
            db.add(role)
            db.flush()
            admin = User(
                username="pg-folio-admin",
                email="pg-folio-admin@example.test",
                full_name="PostgreSQL admin",
                hashed_password="unused",
                account_type="internal",
                status="active",
                is_active=True,
                role_id=role.id,
                roles=[role],
            )
            client = Client(legal_name="Tenant PG", commercial_name="Tenant PG")
            db.add_all([admin, client])
            db.commit()
            admin_id, client_id = admin.id, client.id

            order_a = create_work_order(
                db, LabWorkOrderCreate(**create_payload()), admin, operator_client_id=client_id
            ).id
            order_b = create_work_order(
                db, LabWorkOrderCreate(**create_payload()), admin, operator_client_id=client_id
            ).id
            make_pending_equipment(db, order_a, service_type="accredited", position=1)
            make_pending_equipment(db, order_b, service_type="accredited", position=1)
            make_resolved_ticket(
                db, admin_id, client_id, myca=["MYCA-01-26-0001", "MYCA-01-26-0002"], myct=[]
            )

        def distribute(order_id: int) -> str:
            with factory() as db:
                admin_user = db.get(User, admin_id)
                result = distribute_pending_certificate_folios(db, order_id, admin_user)
                assert len(result.assigned) == 1
                return result.assigned[0].folio

        with ThreadPoolExecutor(max_workers=2) as pool:
            folios = sorted(pool.map(distribute, [order_a, order_b]))
        assert folios == ["MYCA-01-26-0001", "MYCA-01-26-0002"]
    finally:
        engine.dispose()
        with create_engine(database_url).begin() as connection:
            connection.execute(sa_text(f'DROP SCHEMA "{schema}" CASCADE'))
