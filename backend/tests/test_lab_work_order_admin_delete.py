"""DELETE administrativo de OT LAB: purga de FieldSheets protegidas + storage.

Cubre el ajuste que sólo permite el DELETE físico de una OT con FieldSheets
completed/históricas cuando la OT ya está cancelled (purga administrativa),
y el fix P0 de delete_work_order(): el borrado en PostgreSQL es la operación
principal -- una vez comprometido (commit), un fallo posterior al limpiar el
PDF físico en storage nunca debe convertirse en un 409/rollback aparente."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.audit_log import AuditLog
from app.models.certificate import Certificate
from app.models.client import Client
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet, FieldSheetResult, FieldSheetSignature
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.service_order import ServiceOrder, ServiceWorkOrder
from app.models.user import Role, User
from app.services import lab_field_sheets as lab_field_sheets_service


@pytest.fixture()
def lab_context():
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
        technician_role = Role(name="Tecnico", description="Técnico")
        admin_role = Role(name="Administrador", description="Administrador")
        db.add_all([technician_role, admin_role])
        db.flush()
        users = []
        for key, role in (("tech", technician_role), ("admin", admin_role)):
            user = User(
                username=f"admdel-{key}",
                email=f"admdel-{key}@example.test",
                full_name=f"ADMDEL {key}",
                hashed_password="unused",
                account_type="internal",
                status="active",
                is_active=True,
                role_id=role.id,
                roles=[role],
            )
            users.append(user)
        db.add_all(users)
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    tokens = {
        key: create_access_token(
            str(user.id),
            extra_claims={"roles": [user.roles[0].name], "auth_context": "internal"},
        )
        for key, user in zip(("tech", "admin"), users, strict=True)
    }
    try:
        yield client, factory, tokens
    finally:
        app.dependency_overrides.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_payload(client_name: str = "Cliente Admin Delete") -> dict:
    return {
        "reception_date": "2026-08-13",
        "client_name": client_name,
        "address": "Av. Prueba 123",
        "contact_name": "Persona Cliente",
        "contact_phone": "3312345678",
        "contact_email": "cliente@example.com",
        "postal_code": "45601",
        "city": "Tlaquepaque",
        "state_name": "Jalisco",
        "purchase_order": "OC-123",
        "notes": "Recepción LAB",
    }


def equipment_payload(index: int, **extra) -> dict:
    return {
        "instrument": f"Instrumento {index}",
        "brand": "MYC Test",
        "identification": f"ID-{index}",
        "serial_number": f"SER-{index}",
        "report_number": None,
        "is_good_condition": True,
        **extra,
    }


def _work_order_with_equipment(client: TestClient, tech_token: str, client_name: str) -> dict:
    headers = auth(tech_token)
    created = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(client_name), headers=headers
    ).json()
    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{created['id']}/equipment",
        json=equipment_payload(1),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{created['id']}", headers=headers
    ).json()


def _attach_completed_field_sheet(
    factory, lab_equipment_id: int, *, revision_number: int = 1, supersedes_field_sheet_id: int | None = None
) -> int:
    with factory() as db:
        sheet = FieldSheet(
            lab_equipment_id=lab_equipment_id,
            template_key="general",
            status="completed",
            is_current=True,
            revision_number=revision_number,
            supersedes_field_sheet_id=supersedes_field_sheet_id,
            final_pdf_path=f"storage/fixture-{lab_equipment_id}-{revision_number}.pdf",
            final_pdf_sha256="0" * 64,
        )
        db.add(sheet)
        db.flush()
        db.add(FieldSheetResult(field_sheet_id=sheet.id, section_key="general", row_number=1))
        db.add(FieldSheetSignature(
            field_sheet_id=sheet.id, role="calibrated_by", display_label="Calibró", name="Técnico",
        ))
        db.commit()
        return sheet.id


def test_case_a_non_cancelled_ot_with_completed_field_sheet_blocks_delete(lab_context):
    client, factory, tokens = lab_context
    admin_headers = auth(tokens["admin"])
    work_order = _work_order_with_equipment(client, tokens["tech"], "Cliente caso A")
    lab_equipment_id = work_order["equipment"][0]["id"]
    sheet_id = _attach_completed_field_sheet(factory, lab_equipment_id)

    response = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}", headers=admin_headers
    )
    assert response.status_code == 409
    assert "hoja de campo" in response.json()["detail"]

    with factory() as db:
        assert db.get(LabWorkOrder, work_order["id"]) is not None
        assert db.get(FieldSheet, sheet_id) is not None


def test_case_b_cancelled_ot_with_completed_field_sheet_purges_ot_and_sheets(lab_context):
    client, factory, tokens = lab_context
    admin_headers = auth(tokens["admin"])
    work_order = _work_order_with_equipment(client, tokens["tech"], "Cliente caso B")
    lab_equipment_id = work_order["equipment"][0]["id"]
    sheet_id = _attach_completed_field_sheet(factory, lab_equipment_id)

    cancel = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/cancel",
        json={"reason": "Cancelar para purga administrativa"},
        headers=admin_headers,
    )
    assert cancel.status_code == 200, cancel.text

    response = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}", headers=admin_headers
    )
    assert response.status_code == 204, response.text

    with factory() as db:
        assert db.get(LabWorkOrder, work_order["id"]) is None
        assert db.get(LabWorkOrderEquipment, lab_equipment_id) is None
        assert db.get(FieldSheet, sheet_id) is None
        assert db.get(FieldSheetResult, db.scalar(select(FieldSheetResult.id))) is None


def test_case_c_cleanup_failure_after_commit_does_not_report_a_false_conflict(lab_context, monkeypatch):
    """P0: si delete_purged_lab_field_sheet_files revienta DESPUÉS del commit
    principal, el DELETE debe seguir respondiendo éxito -- la OT ya está
    eliminada en PostgreSQL y no hay marcha atrás honesta posible."""
    client, factory, tokens = lab_context
    admin_headers = auth(tokens["admin"])
    work_order = _work_order_with_equipment(client, tokens["tech"], "Cliente caso C")
    lab_equipment_id = work_order["equipment"][0]["id"]
    sheet_id = _attach_completed_field_sheet(factory, lab_equipment_id)

    cancel = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/cancel",
        json={"reason": "Cancelar para purga administrativa"},
        headers=admin_headers,
    )
    assert cancel.status_code == 200, cancel.text

    def _boom(*_args, **_kwargs):
        raise OSError("disco lleno simulado")

    monkeypatch.setattr(lab_field_sheets_service, "delete_purged_lab_field_sheet_files", _boom)

    response = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}", headers=admin_headers
    )
    assert response.status_code == 204, (
        f"un fallo de limpieza de storage post-commit no debe reportarse como conflicto: {response.text}"
    )

    with factory() as db:
        assert db.get(LabWorkOrder, work_order["id"]) is None, "el DELETE en DB debe haberse confirmado igual"
        assert db.get(FieldSheet, sheet_id) is None


def test_case_d_audit_log_preserves_purged_field_sheet_snapshot(lab_context):
    client, factory, tokens = lab_context
    admin_headers = auth(tokens["admin"])
    work_order = _work_order_with_equipment(client, tokens["tech"], "Cliente caso D")
    lab_equipment_id = work_order["equipment"][0]["id"]
    sheet_id = _attach_completed_field_sheet(factory, lab_equipment_id)

    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/cancel",
        json={"reason": "Cancelar"},
        headers=admin_headers,
    )
    response = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}", headers=admin_headers
    )
    assert response.status_code == 204, response.text

    with factory() as db:
        entry = db.scalar(
            select(AuditLog)
            .where(AuditLog.action == "lab_work_order.deleted", AuditLog.entity_id == work_order["id"])
        )
        assert entry is not None
        purged = entry.previous_values["purged_field_sheets"]
        assert len(purged) == 1
        assert purged[0]["id"] == sheet_id
        assert purged[0]["status"] == "completed"


def test_case_e_linked_production_certificate_is_unlinked_not_destroyed(lab_context):
    """Un certificado productivo enlazado (inesperadamente) a una FieldSheet
    LAB no debe destruirse -- sólo pierde la FK opcional field_sheet_id."""
    client, factory, tokens = lab_context
    admin_headers = auth(tokens["admin"])
    work_order = _work_order_with_equipment(client, tokens["tech"], "Cliente caso E")
    lab_equipment_id = work_order["equipment"][0]["id"]
    sheet_id = _attach_completed_field_sheet(factory, lab_equipment_id)

    with factory() as db:
        production_client = Client(legal_name="Cliente productivo E")
        db.add(production_client)
        db.flush()
        service_order = ServiceOrder(
            folio="OSMYC-ADMDEL-0001",
            work_order_number=990001,
            client_id=production_client.id,
            status="in_progress",
            total_equipment=1,
            completed_equipment=0,
        )
        db.add(service_order)
        db.flush()
        service_work_order = ServiceWorkOrder(
            service_order_id=service_order.id,
            work_order_number=990001,
            sequence=1,
            status="in_progress",
        )
        db.add(service_work_order)
        db.flush()
        equipment = Equipment(
            service_order_id=service_order.id,
            work_order_id=service_work_order.id,
            name="Equipo productivo enlazado",
            status="registered",
        )
        db.add(equipment)
        db.flush()
        certificate = Certificate(
            folio="CERT-ADMDEL-0001",
            service_order_id=service_order.id,
            equipment_id=equipment.id,
            field_sheet_id=sheet_id,
            certificate_type="calibration",
            status="draft",
        )
        db.add(certificate)
        db.commit()
        certificate_id = certificate.id

    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/cancel",
        json={"reason": "Cancelar"},
        headers=admin_headers,
    )
    response = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}", headers=admin_headers
    )
    assert response.status_code == 204, response.text

    with factory() as db:
        assert db.get(FieldSheet, sheet_id) is None
        reloaded_certificate = db.get(Certificate, certificate_id)
        assert reloaded_certificate is not None, "el certificado productivo nunca debe destruirse"
        assert reloaded_certificate.field_sheet_id is None


def test_case_f_purges_a_multi_revision_supersedes_chain(lab_context):
    """Varias revisiones encadenadas (supersedes_field_sheet_id) del mismo
    equipo LAB deben purgarse todas, junto con sus hijos, en una sola
    eliminación administrativa."""
    client, factory, tokens = lab_context
    admin_headers = auth(tokens["admin"])
    work_order = _work_order_with_equipment(client, tokens["tech"], "Cliente caso F")
    lab_equipment_id = work_order["equipment"][0]["id"]

    first_id = _attach_completed_field_sheet(factory, lab_equipment_id, revision_number=1)
    with factory() as db:
        first = db.get(FieldSheet, first_id)
        first.is_current = False
        db.commit()
    second_id = _attach_completed_field_sheet(
        factory, lab_equipment_id, revision_number=2, supersedes_field_sheet_id=first_id
    )

    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}/cancel",
        json={"reason": "Cancelar"},
        headers=admin_headers,
    )
    response = client.delete(
        f"/api/mobile/v1/technician/lab-work-orders/{work_order['id']}", headers=admin_headers
    )
    assert response.status_code == 204, response.text

    with factory() as db:
        assert db.get(FieldSheet, first_id) is None
        assert db.get(FieldSheet, second_id) is None
        assert db.scalars(select(FieldSheetResult)).first() is None
        assert db.scalars(select(FieldSheetSignature)).first() is None
