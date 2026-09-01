from __future__ import annotations

import io
import re

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from fastapi import HTTPException

from app.core.security import create_access_token
from app.main import app
from app.models.lab_client import LabClient
from app.models.operational_ticket import OperationalTicket
from app.models.user import Role, User
from app.schemas.operational_ticket import TicketReject, TicketResolve, TicketReview
from app.services.field_sheet_pdfs import generate_field_sheet_pdf
from app.services.operational_tickets import approve_reopen_ticket, reject_ticket, resolve_operational_ticket


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
        capture_role = Role(name="Captura", description="Captura")
        tech_role = Role(name="Tecnico", description="Técnico")
        admin_role = Role(name="Administrador", description="Administrador")
        db.add_all([capture_role, tech_role, admin_role])
        db.flush()
        users = []
        for key, role in (("capture", capture_role), ("tech", tech_role), ("admin", admin_role)):
            user = User(
                username=f"lab-{key}",
                email=f"lab-{key}@example.test",
                full_name=f"LAB {key}",
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
        for key, user in zip(("capture", "tech", "admin"), users, strict=True)
    }
    try:
        yield client, factory, tokens
    finally:
        app.dependency_overrides.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_payload(client_name: str = "Cliente LAB") -> dict:
    return {
        "reception_date": "2026-08-13",
        "departure_date": "2026-08-15",
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


def _setup_order_with_equipment(client, headers, *, count: int = 2) -> tuple[int, list[int]]:
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(), headers=headers
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    equipment_ids = []
    for index in range(1, count + 1):
        added = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
            json=equipment_payload(index),
            headers=headers,
        )
        assert added.status_code == 201, added.text
        equipment_ids.append(added.json()["equipment"][-1]["id"])
    for equipment_id in equipment_ids:
        service = client.put(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
            json={"service_type": "accredited", "linked_company_id": None},
            headers=headers,
        )
        assert service.status_code == 200, service.text
    return order_id, equipment_ids


@pytest.mark.parametrize("template_key", ["vernier", "electrica"])
def test_mobile_equivalent_payload_round_trips_into_the_pdf(lab_context, template_key):
    """Mobile-equivalent payload -> update_lab_field_sheet (via PATCH) ->
    generate_field_sheet_pdf -> the direct fields and capture_values the PDF
    reads must show up in the rendered document. Guards against the
    mobile/PDF split regressing (company/address/attention/dates/units/
    method/observations must land where field_sheet_pdfs.py actually reads
    them, not silently swallowed into an unused capture_values blob)."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)

    created_sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": template_key},
        headers=headers,
    )
    assert created_sheet.status_code == 201, created_sheet.text
    sheet_id = created_sheet.json()["id"]

    # This mirrors exactly what the corrected LabTechnicalCapture.saveSheet()
    # now sends: direct FieldSheet columns at top level, equipment identity
    # fields nested under capture_values.
    mobile_payload = {
        "company": f"Cliente {template_key} actualizado",
        "address": f"Calle actualizada {template_key} 99",
        "attention": f"Ing. Responsable {template_key}",
        "reception_date": "2026-08-13",
        "calibration_date": "2026-08-14",
        "next_calibration_date": "2027-08-14",
        "units": f"unidad-{template_key}",
        "method": f"metodo-comparacion-{template_key}",
        "observations": f"observacion-relevante-{template_key}",
        "final_condition": "BUENA",
        # No hyphens/long compounds: those wrap mid-word inside the narrow PDF
        # equipment card with no literal whitespace at the break, which would
        # make a naive substring match fail on a purely cosmetic line wrap.
        "capture_values": {
            "instrument": f"Instr{template_key}9",
            "brand": f"Marca{template_key}9",
            "model": f"Modelo{template_key}9",
            "serial_number": f"Serie{template_key}9",
            "internal_id": f"Idint{template_key}9",
            "scope": f"Alcance{template_key}9",
        },
    }
    updated_sheet = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json=mobile_payload,
        headers=headers,
    )
    assert updated_sheet.status_code == 200, updated_sheet.text
    body = updated_sheet.json()
    assert body["capture_values"] == mobile_payload["capture_values"]

    with factory() as db:
        pdf_bytes, _filename = generate_field_sheet_pdf(db, sheet_id)
    raw_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages
    )
    # Long values wrap across lines inside the PDF's narrow layout cards; collapse
    # whitespace so a wrapped value still matches as one contiguous string.
    rendered_text = re.sub(r"\s+", " ", raw_text).upper()

    for expected in (
        mobile_payload["company"],
        mobile_payload["address"],
        mobile_payload["attention"],
        mobile_payload["units"],
        mobile_payload["method"],
        mobile_payload["observations"],
        mobile_payload["capture_values"]["instrument"],
        mobile_payload["capture_values"]["brand"],
        mobile_payload["capture_values"]["model"],
        mobile_payload["capture_values"]["serial_number"],
    ):
        assert expected.upper() in rendered_text, f"{expected!r} missing from {template_key} PDF"


def test_patch_field_sheet_rejects_empty_string_for_typed_date_and_boolean_fields(lab_context):
    """FieldSheetUpdate types reception_date/calibration_date/next_calibration_date as
    date | None and equipment_general_condition as bool | None. '' is not a valid value
    for either type in Pydantic — this locks in that the backend correctly rejects it
    with 422 rather than silently coercing it. Mobile's normalizeFieldSheetPayload() is
    what must turn a cleared date/boolean input into null before it ever reaches here."""
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created_sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created_sheet.status_code == 201, created_sheet.text

    for field_name in ("calibration_date", "next_calibration_date", "equipment_general_condition"):
        response = client.patch(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
            json={field_name: ""},
            headers=headers,
        )
        assert response.status_code == 422, f"{field_name}='' should be rejected: {response.text}"


def test_patch_field_sheet_accepts_null_for_typed_date_and_boolean_fields(lab_context):
    """The counterpart of the rejection test above: this is exactly the payload shape
    normalizeFieldSheetPayload() must produce (null, not '') for a technician who typed
    then cleared a date/boolean field — and it must succeed."""
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created_sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created_sheet.status_code == 201, created_sheet.text

    response = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={
            "calibration_date": None,
            "next_calibration_date": None,
            "equipment_general_condition": None,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["calibration_date"] is None
    assert body["next_calibration_date"] is None
    assert body["equipment_general_condition"] is None


def test_draft_patch_succeeds_despite_incomplete_technical_data(lab_context):
    """Saving as draft (PATCH) must never require completeness — only POST /complete
    runs _validate_ready_to_complete. A field sheet missing final_condition/observations
    must still accept a partial PATCH."""
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created_sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created_sheet.status_code == 201, created_sheet.text
    assert created_sheet.json()["final_condition"] is None
    assert created_sheet.json()["observations"] is None

    response = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"units": "mm"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "in_progress"
    assert response.json()["final_condition"] is None


def test_complete_lab_field_sheet_returns_structured_missing_fields(lab_context):
    """POST /complete on an incomplete LAB field sheet must surface the same
    structured {message, missing_fields} detail the generic engine already
    produces (_validate_ready_to_complete), not a bare/flattened string —
    mobile relies on `missing_fields` to render the bullet list."""
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created_sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created_sheet.status_code == 201, created_sheet.text

    response = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/complete",
        headers=headers,
    )
    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert isinstance(detail, dict)
    assert detail["message"]
    assert isinstance(detail["missing_fields"], list)
    assert "final_condition" in detail["missing_fields"]
    assert "observations_or_evidence_notes" in detail["missing_fields"]


def test_captura_role_cannot_delete_a_lab_field_sheet_via_generic_endpoint(lab_context):
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, tech_headers, count=1)
    created_sheet = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=tech_headers,
    )
    assert created_sheet.status_code == 201, created_sheet.text
    sheet_id = created_sheet.json()["id"]

    # Captura's generic field_sheets.update permission (productive ERP flows)
    # must not let it delete a LAB field sheet through the generic router.
    response = client.delete(
        f"/api/field-sheets/{sheet_id}",
        headers=auth(tokens["capture"]),
    )
    assert response.status_code in (403, 404)


def test_lab_client_catalog_rejects_duplicate_identity_for_internal_null_scope(lab_context):
    """Regression for the model/migration Index vs UniqueConstraint divergence:
    even under Base.metadata.create_all() (SQLite, used by these tests), two
    internal-catalog (operator_client_id IS NULL) LabClient rows with the same
    normalized identity must violate the unique index, not silently coexist."""
    _client, factory, _tokens = lab_context
    from app.services.lab_clients import normalize_lab_client_identity

    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        identity = dict(
            company="Duplicado SA",
            address="Calle 1",
            attention="Ing. Uno",
        )
        first = LabClient(
            **identity,
            normalized_company=normalize_lab_client_identity(identity["company"]),
            normalized_address=normalize_lab_client_identity(identity["address"]),
            normalized_attention=normalize_lab_client_identity(identity["attention"]),
            operator_client_id=None,
            created_by_user_id=admin.id,
        )
        db.add(first)
        db.commit()

        second = LabClient(
            **identity,
            normalized_company=normalize_lab_client_identity(identity["company"]),
            normalized_address=normalize_lab_client_identity(identity["address"]),
            normalized_attention=normalize_lab_client_identity(identity["attention"]),
            operator_client_id=None,
            created_by_user_id=admin.id,
        )
        db.add(second)
        with pytest.raises(Exception):
            db.commit()


@pytest.mark.parametrize(
    "resolver",
    [
        lambda db, ticket, user: reject_ticket(db, ticket.id, TicketReject(comment="No procede"), user),
        lambda db, ticket, user: resolve_operational_ticket(db, ticket.id, TicketResolve(comment="ok"), user),
        lambda db, ticket, user: approve_reopen_ticket(
            db, ticket.id, TicketReview(signature_policy="preserve"), user
        ),
    ],
    ids=["reject_ticket", "resolve_operational_ticket", "approve_reopen_ticket"],
)
def test_ticket_requester_cannot_resolve_their_own_ticket(lab_context, resolver):
    _client, factory, _tokens = lab_context
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "lab-admin"))
        ticket = OperationalTicket(
            type="manual_myc_folio",
            status="pending",
            requested_by_user_id=admin.id,
            reason="Motivo de prueba",
            description="Descripción de prueba",
        )
        db.add(ticket)
        db.commit()
        with pytest.raises(HTTPException) as excinfo:
            resolver(db, ticket, admin)
        assert excinfo.value.status_code == 403
        assert excinfo.value.detail == "TICKET_SELF_APPROVAL_FORBIDDEN"
