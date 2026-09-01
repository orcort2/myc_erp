from __future__ import annotations

import base64
import io
import re
from datetime import datetime, timezone

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
from app.core.config import settings
from app.main import app
from app.models.field_sheet import FieldSheet, FieldSheetSignature
from app.models.lab_client import LabClient
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderSignature, LabWorkOrderSignatureSession
from app.models.operational_ticket import OperationalTicket
from app.models.user import Role, User
from app.schemas.operational_ticket import TicketReject, TicketResolve, TicketReview
from app.services.field_sheet_pdfs import (
    _resolve_field_sheet_signatures,
    generate_field_sheet_pdf,
    resolve_field_sheet_pdf_renderer,
)
from app.services.field_sheets import EDITABLE_STATUSES
from app.services.operational_tickets import approve_reopen_ticket, reject_ticket, resolve_operational_ticket

PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()


def signatures_payload() -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {
            "signer_name": "Técnico LAB",
            "signed_at": signed_at,
            "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
        "client": {
            "signer_name": "Cliente LAB",
            "signed_at": signed_at,
            "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
    }


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
    # Fase 3: la captura FieldSheet sólo procede tras la recepción firmada
    # (draft -> received_signed); todo equipo aquí ya está coherente
    # (servicio + folio MYCA), así que la firma de recepción siempre procede.
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    return order_id, equipment_ids


def _create_and_complete_field_sheet(client, headers, order_id, equipment_id, template_key="general") -> int:
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": template_key},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]
    rows = [
        {
            "id": row["id"],
            "section_key": row["section_key"],
            "row_number": row["row_number"],
            "row_data": {"result": "1.00"} if index == 0 else row["row_data"],
        }
        for index, row in enumerate(created.json()["results_rows"])
    ]
    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"final_condition": "BUENA", "observations": "Sin observaciones", "results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    return sheet_id


def test_new_lab_field_sheet_uses_canonical_versioned_renderer_and_refresh_state_contract(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=2)

    first = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert first.status_code == 201, first.text
    first_body = first.json()
    assert first_body["pdf_renderer_key"] == "field_sheet_engine"
    assert first_body["pdf_renderer_version"] == 1
    assert first_body["template_definition"]["pdf_template"] == "field_sheet_engine_pdf.html"
    assert client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()["status"] == "in_progress"

    second = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[1]}/field-sheet",
        json={"template_key": "presion"},
        headers=headers,
    )
    assert second.status_code == 201, second.text
    assert client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()["status"] == "in_progress"

    with factory() as db:
        persisted = db.get(FieldSheet, first_body["id"])
        assert persisted.pdf_renderer_key == "field_sheet_engine"
        assert persisted.pdf_renderer_version == 1


def test_legacy_snapshot_resolves_only_its_allowlisted_legacy_renderer():
    sheet = FieldSheet(
        lab_equipment_id=1,
        template_key="general",
        pdf_renderer_key=None,
        pdf_renderer_version=None,
    )
    definition = {"pdf_template": "field_sheet_general_pdf.html"}
    assert resolve_field_sheet_pdf_renderer(sheet, definition) == (
        "legacy:field_sheet_general_pdf.html",
        1,
        "field_sheet_general_pdf.html",
    )


def test_historical_engine_snapshot_resolves_to_canonical_engine_v1():
    # A historical row backfilled with pdf_renderer_key=NULL (unbackfillable
    # by the migration's own rules) but whose snapshot unambiguously names the
    # canonical engine template must still resolve deterministically -- this
    # is the one case the migration's CASE and the resolver's fallback agree
    # is genuinely inferable, unlike an unrecognized/missing pdf_template.
    sheet = FieldSheet(
        lab_equipment_id=1,
        template_key="general",
        pdf_renderer_key=None,
        pdf_renderer_version=None,
    )
    definition = {"pdf_template": "field_sheet_engine_pdf.html"}
    assert resolve_field_sheet_pdf_renderer(sheet, definition) == (
        "field_sheet_engine",
        1,
        "field_sheet_engine_pdf.html",
    )


def test_historical_unrecognized_template_is_not_silently_reinterpreted():
    # No pdf_renderer_key on the row, and a pdf_template that names neither
    # the canonical engine nor any of the known legacy templates. This must
    # never fall back to the canonical engine by discard -- it must surface
    # as a clear conflict so nobody downloads a document rendered by a
    # renderer that was never actually used to produce that history.
    sheet = FieldSheet(
        lab_equipment_id=1,
        template_key="general",
        pdf_renderer_key=None,
        pdf_renderer_version=None,
    )
    for definition in (
        {"pdf_template": "some_retired_custom_template.html"},
        {},
    ):
        with pytest.raises(HTTPException) as exc_info:
            resolve_field_sheet_pdf_renderer(sheet, definition)
        assert exc_info.value.status_code == 409


def test_final_field_sheet_pdf_is_frozen_with_sha_and_reused(lab_context, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    sheet_id = _create_and_complete_field_sheet(client, headers, order_id, equipment_ids[0])

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        frozen_path = sheet.final_pdf_path
        frozen_sha = sheet.final_pdf_sha256
        frozen_at = sheet.final_pdf_generated_at
        assert frozen_path
        assert frozen_sha and len(frozen_sha) == 64
        assert sheet.final_pdf_template_definition_version == sheet.template_definition_version
        first_bytes, _ = generate_field_sheet_pdf(db, sheet_id)
        first_mtime = (tmp_path / frozen_path).stat().st_mtime_ns

    with factory() as db:
        second_bytes, _ = generate_field_sheet_pdf(db, sheet_id)
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.final_pdf_path == frozen_path
        assert sheet.final_pdf_sha256 == frozen_sha
        assert sheet.final_pdf_generated_at == frozen_at
        assert (tmp_path / frozen_path).stat().st_mtime_ns == first_mtime
    assert first_bytes == second_bytes


def test_failure_after_pdf_write_leaves_no_orphaned_artifact(lab_context, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    equipment_id = equipment_ids[0]

    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]
    rows = [
        {
            "id": row["id"],
            "section_key": row["section_key"],
            "row_number": row["row_number"],
            "row_data": {"result": "1.00"} if index == 0 else row["row_data"],
        }
        for index, row in enumerate(created.json()["results_rows"])
    ]
    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"final_condition": "BUENA", "observations": "Sin observaciones", "results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    import app.services.lab_field_sheets as lab_field_sheets_module

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated failure after the PDF was already written to disk")

    # The freeze itself (the physical write) succeeds; the very next
    # statement in the same unit of work -- the audit log write -- fails.
    # guard_final_pdf_write must catch that, delete the artifact it just
    # wrote, and roll back so the DB and the filesystem agree again.
    monkeypatch.setattr(lab_field_sheets_module, "write_audit_log", _boom)

    with pytest.raises(RuntimeError):
        client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
            headers=headers,
        )

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.status == "in_progress"
        assert sheet.final_pdf_path is None
        assert sheet.final_pdf_sha256 is None

    final_dir = tmp_path / "field-sheets" / str(sheet_id) / "final"
    assert not final_dir.exists() or list(final_dir.iterdir()) == []


def test_completed_field_sheet_never_reenters_editable_status(lab_context, monkeypatch, tmp_path):
    # Documents the current state machine: EDITABLE_STATUSES excludes
    # "completed" and "under_review", and nothing in this codebase transitions
    # a FieldSheet's status from either of those back into "rejected" or
    # "returned_to_technician" (those values are reserved on the schema but
    # have no producer). This locks that invariant so a frozen PDF can never
    # go stale behind a re-editable sheet without this test failing first.
    monkeypatch.setattr(settings, "storage_root", str(tmp_path))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    sheet_id = _create_and_complete_field_sheet(client, headers, order_id, equipment_ids[0])

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.status == "completed"
        assert sheet.status not in EDITABLE_STATUSES
        frozen_path = sheet.final_pdf_path
        frozen_sha = sheet.final_pdf_sha256

    blocked = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"observations": "Intento de edicion post-congelado"},
        headers=headers,
    )
    assert blocked.status_code == 409, blocked.text

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.final_pdf_path == frozen_path
        assert sheet.final_pdf_sha256 == frozen_sha


def test_structurally_different_families_render_through_same_canonical_engine(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=2)
    rendered: dict[str, str] = {}
    for equipment_id, template_key in zip(equipment_ids, ("general", "electrica"), strict=True):
        created = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
            json={"template_key": template_key},
            headers=headers,
        )
        assert created.status_code == 201, created.text
        assert created.json()["pdf_renderer_key"] == "field_sheet_engine"
        with factory() as db:
            pdf_bytes, _ = generate_field_sheet_pdf(db, created.json()["id"])
        rendered[template_key] = re.sub(
            r"\s+",
            " ",
            "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages),
        ).upper()

    assert "TABLA COMPARATIVA" in rendered["general"]
    assert "VOLTAJE AC" in rendered["electrica"]
    assert "CORRIENTE DC" in rendered["electrica"]
    assert "VOLTAJE AC" not in rendered["general"]


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


def test_resolve_field_sheet_signatures_returns_unchanged_rows_for_productive_sheets(lab_context):
    """Regression 1: productive (non-LAB) FieldSheets must keep using their own
    FieldSheetSignature rows untouched by the LAB resolution path."""
    _client, factory, _tokens = lab_context
    with factory() as db:
        real_signature = FieldSheetSignature(role="calibrated_by", display_label="Calibró", name="Juan Pérez")
        sheet = FieldSheet(lab_equipment_id=None, template_key="general")
        sheet.signatures = [real_signature]
        resolved = _resolve_field_sheet_signatures(db, sheet)
        assert resolved == [real_signature]
        assert resolved[0].name == "Juan Pérez"


def test_lab_field_sheet_signature_resolves_technician_and_leaves_quality_slots_pending(lab_context):
    """Regressions 2, 3 and 5: a LAB FieldSheet with lab_signature_session_id must
    resolve 'calibrated_by' (Calibró) from the session's technician signature
    (same authority the OT PDF already uses), while 'reviewed_by'/'report_made_by'
    (Calidad-stage slots not produced by the LAB closure flow) stay pending — the
    client's signature must never backfill those, and no FieldSheetSignature row
    is created/mutated in the process (no artificial records, no persistence)."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    # Fase 3: la recepción ya quedó firmada dentro de _setup_order_with_equipment
    # (requisito para poder capturar); la FieldSheet toma su
    # lab_signature_session_id de esa sesión vigente en el momento de crearse
    # (create_lab_field_sheet), sin necesidad de firmar de nuevo aquí.
    sheet_id = _create_and_complete_field_sheet(client, headers, order_id, equipment_ids[0])

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.lab_signature_session_id is not None
        before = {item.id: (item.name, item.signature_data) for item in sheet.signatures}

        resolved = _resolve_field_sheet_signatures(db, sheet)
        by_role = {item.role: item for item in resolved}
        assert by_role["calibrated_by"].name == "Técnico LAB"
        assert by_role["calibrated_by"].signature_data == PNG_DATA_URL
        assert by_role["calibrated_by"].signed_at is not None
        assert by_role["reviewed_by"].name is None
        assert by_role["report_made_by"].name is None

        # No artificial FieldSheetSignature rows were created/mutated to satisfy
        # the renderer: the persisted rows in this same session are unchanged...
        after = {item.id: (item.name, item.signature_data) for item in sheet.signatures}
        assert after == before

    with factory() as db:
        # ...and re-reading from a fresh session confirms nothing was committed.
        persisted = list(
            db.scalars(select(FieldSheetSignature).where(FieldSheetSignature.field_sheet_id == sheet_id))
        )
        assert {item.role for item in persisted} == {"calibrated_by", "reviewed_by", "report_made_by"}
        assert all(item.name is None for item in persisted)
        assert all(item.signature_data is None for item in persisted)


def test_lab_field_sheet_signature_resolution_is_historical_not_latest_group_session(lab_context):
    """Regression 4: a FieldSheet already linked to signature session v1 must
    keep resolving from v1 even after a sibling OT in the same historical group
    is signed later, creating session v2 — no 'latest signature of the group'
    lookup."""
    client, factory, tokens = lab_context
    admin_headers = auth(tokens["admin"])
    tech_headers = auth(tokens["tech"])
    payload = {**create_payload("Cliente grupo histórico"), "quantity": 2}
    group = client.post("/api/lab-work-order-groups", json=payload, headers=admin_headers)
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]
    assert len(members) == 2

    # Fase 3: la recepción se firma ANTES de capturar -- así que cada miembro
    # configura su equipo/servicio y firma su propia recepción individual
    # antes de que su FieldSheet pueda crearse. sheet[0] toma la sesión
    # vigente de member[0] (v1) al crearse; luego, cuando member[1] firma por
    # separado (v2, sobre el mismo root histórico), sheet[0] no debe migrar.
    equipment_ids = []
    for member in members:
        added = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{member['id']}/equipment",
            json=equipment_payload(member["id"]),
            headers=tech_headers,
        )
        assert added.status_code == 201, added.text
        equipment_id = added.json()["equipment"][-1]["id"]
        service = client.put(
            f"/api/mobile/v1/technician/lab-work-orders/{member['id']}/equipment/{equipment_id}/service",
            json={"service_type": "accredited", "linked_company_id": None},
            headers=tech_headers,
        )
        assert service.status_code == 200, service.text
        equipment_ids.append(equipment_id)

    first_signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{members[0]['id']}/signatures/individual",
        json=signatures_payload(),
        headers=tech_headers,
    )
    assert first_signed.status_code == 200, first_signed.text

    sheet_ids = [
        _create_and_complete_field_sheet(client, tech_headers, members[0]["id"], equipment_ids[0])
    ]

    with factory() as db:
        first_sheet = db.get(FieldSheet, sheet_ids[0])
        first_session_id = first_sheet.lab_signature_session_id
        assert first_session_id is not None
        resolved_before = _resolve_field_sheet_signatures(db, first_sheet)
        assert {item.role: item.name for item in resolved_before}["calibrated_by"] == "Técnico LAB"

    second_payload = signatures_payload()
    second_payload["technician"]["signer_name"] = "Técnico LAB posterior"
    second_signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{members[1]['id']}/signatures/individual",
        json=second_payload,
        headers=tech_headers,
    )
    assert second_signed.status_code == 200, second_signed.text
    sheet_ids.append(
        _create_and_complete_field_sheet(client, tech_headers, members[1]["id"], equipment_ids[1])
    )

    with factory() as db:
        first_sheet = db.get(FieldSheet, sheet_ids[0])
        second_sheet = db.get(FieldSheet, sheet_ids[1])
        # The second OT's own session is a distinct, later session on the same root group...
        assert second_sheet.lab_signature_session_id != first_session_id
        second_session = db.get(LabWorkOrderSignatureSession, second_sheet.lab_signature_session_id)
        first_session = db.get(LabWorkOrderSignatureSession, first_session_id)
        assert second_session.root_work_order_id == first_session.root_work_order_id
        assert second_session.version > first_session.version

        # ...but the FIRST field sheet must still resolve from its own, older,
        # frozen session — never "the latest signature of the group".
        assert first_sheet.lab_signature_session_id == first_session_id
        resolved_after = _resolve_field_sheet_signatures(db, first_sheet)
        assert {item.role: item.name for item in resolved_after}["calibrated_by"] == "Técnico LAB"


def test_generate_field_sheet_pdf_prints_technician_signature_and_keeps_quality_slots_pending(lab_context):
    """Regression 6: the actual PDF output (post-signing) must show the
    technician's name/signature under 'Calibró' and still say 'Pendiente' for
    the Calidad-stage slots that the LAB closure flow never produces."""
    # "presion" is the exact template family (field_sheet_engine_pdf.html, one of
    # the official pilot templates) used by OT 6414 in the physical QA that
    # surfaced this bug — its signature block literally prints "Pendiente".
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    sheet_id = _create_and_complete_field_sheet(client, headers, order_id, equipment_ids[0], template_key="presion")

    with factory() as db:
        pdf_bytes, _filename = generate_field_sheet_pdf(db, sheet_id)
    raw_text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages)
    rendered_text = re.sub(r"\s+", " ", raw_text).upper()

    assert "TÉCNICO LAB" in rendered_text
    # Only two of the three documental slots (Revisó, Elaboró informe) should
    # still say "Pendiente"; the technician's "Calibró" role must not.
    assert rendered_text.count("PENDIENTE") == 2


@pytest.mark.parametrize("template_key", ["general", "presion"])
def test_pdf_footer_delimits_document_code_and_revision_with_a_pipe(lab_context, template_key):
    """Presentation-only: document_code ('FCA-30') and initial_revision ('R1') are
    persisted values, unchanged here — only the footer separator changes from the
    ambiguous middle dot to an explicit pipe so code and revision read as two
    clearly delimited values, not one run-on token."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": template_key},
        headers=headers,
    )
    assert created.status_code == 201, created.text

    with factory() as db:
        pdf_bytes, _filename = generate_field_sheet_pdf(db, created.json()["id"])
    raw_text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages)
    rendered_text = re.sub(r"\s+", " ", raw_text)

    assert "FCA-30" in rendered_text
    assert "R1" in rendered_text
    assert "FCA-30 | R1" in rendered_text
    assert "FCA-30 · R1" not in rendered_text


def test_partial_close_ticket_rejects_a_lone_ot_with_no_real_cohort(lab_context):
    """Backend guard mirroring the mobile visibility rule: 'excepción de cierre
    parcial' only makes sense when the OT belongs to a group with more than one
    currently-relevant OT — never for a solo OT, even one with pending sheets."""
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    # Leave the field sheet incomplete on purpose: this must still be rejected
    # for lack of cohort plurality, before the "missing sheets" check is reached.
    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    response = client.post(
        "/api/mobile/v1/technician/tickets/partial-close",
        json={"work_order_id": order_id, "reason": "Prueba", "description": "Prueba de guard"},
        headers=headers,
    )
    assert response.status_code == 409, response.text
    assert "grupo" in response.json()["detail"].lower()


def test_partial_close_ticket_accepted_for_a_real_multi_ot_cohort(lab_context):
    """The counterpart of the guard above: a genuine multi-OT group with a
    pending sheet on one member is a legitimate partial-close candidate."""
    client, factory, tokens = lab_context
    admin_headers = auth(tokens["admin"])
    tech_headers = auth(tokens["tech"])
    payload = {**create_payload("Cliente grupo parcial"), "quantity": 2}
    group = client.post("/api/lab-work-order-groups", json=payload, headers=admin_headers)
    assert group.status_code == 201, group.text
    members = group.json()["related_work_orders"]

    with factory() as db:
        # _missing_completed_sheets only counts equipment for OTs that carry a
        # lab_client_id; stamp one so the "OT has pending sheets" branch is
        # actually exercised by this test, not short-circuited beforehand.
        work_order = db.get(LabWorkOrder, members[0]["id"])
        client_row = LabClient(
            company="Cliente grupo parcial",
            address="",
            attention="",
            normalized_company="cliente grupo parcial",
            normalized_address="",
            normalized_attention="",
            operator_client_id=None,
            created_by_user_id=work_order.created_by_user_id,
        )
        db.add(client_row)
        db.flush()
        work_order.lab_client_id = client_row.id
        db.commit()

    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{members[0]['id']}/equipment",
        json=equipment_payload(members[0]["id"]),
        headers=tech_headers,
    )
    assert added.status_code == 201, added.text
    equipment_id = added.json()["equipment"][-1]["id"]
    client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{members[0]['id']}/equipment/{equipment_id}/service",
        json={"service_type": "accredited", "linked_company_id": None},
        headers=tech_headers,
    )
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{members[0]['id']}/signatures/individual",
        json=signatures_payload(),
        headers=tech_headers,
    )
    assert signed.status_code == 200, signed.text
    client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{members[0]['id']}/equipment/{equipment_id}/field-sheet",
        json={"template_key": "general"},
        headers=tech_headers,
    )

    response = client.post(
        "/api/mobile/v1/technician/tickets/partial-close",
        json={"work_order_id": members[0]["id"], "reason": "Prueba", "description": "Prueba de guard"},
        headers=tech_headers,
    )
    assert response.status_code == 201, response.text


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
