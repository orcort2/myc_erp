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
from app.models.field_sheet_template_definition import FieldSheetTemplateDefinition
from app.models.lab_client import LabClient
from app.models.lab_work_order import LabWorkOrder, LabWorkOrderSignature, LabWorkOrderSignatureSession
from app.models.operational_ticket import OperationalTicket
from app.models.user import Role, User
from app.schemas.operational_ticket import TicketReject, TicketResolve, TicketReview
from app.models.field_sheet import FieldSheetResult
from app.services.field_sheet_pdfs import (
    _group_sections,
    _resolve_field_sheet_signatures,
    _trim_trailing_empty_rows,
    generate_field_sheet_pdf,
    resolve_field_sheet_pdf_renderer,
)
from app.services.field_sheet_templates import get_template_snapshot
from app.services.field_sheets import EDITABLE_STATUSES, _validate_canonical_common_fields
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


def _setup_order_with_equipment(client, headers, *, count: int = 2, **equipment_extra) -> tuple[int, list[int]]:
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(), headers=headers
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    equipment_ids = []
    for index in range(1, count + 1):
        added = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
            json=equipment_payload(index, **equipment_extra),
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


def _complete_existing_field_sheet(client, headers, order_id, equipment_id) -> None:
    """Como _create_and_complete_field_sheet pero para una hoja ya creada
    (evita el 409 'ya tiene una hoja de campo' de volver a POSTear)."""
    loaded = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    )
    assert loaded.status_code == 200, loaded.text
    rows = [
        {
            "id": row["id"],
            "section_key": row["section_key"],
            "row_number": row["row_number"],
            "row_data": {"result": "1.00"} if index == 0 else row["row_data"],
        }
        for index, row in enumerate(loaded.json()["results_rows"])
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


@pytest.mark.parametrize("template_key", ["general", "manometro"])
def test_two_operational_families_complete_freeze_and_redownload_identically(
    lab_context, monkeypatch, tmp_path, template_key
):
    """QA Fase 6: comparación directa y presión recorren el mismo contrato
    create→prefill→capture→complete→freeze→download con hash estable."""
    monkeypatch.setattr(settings, "storage_root", str(tmp_path / template_key))
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(
        client,
        headers,
        count=1,
        model="Modelo QA",
    )
    sheet_id = _create_and_complete_field_sheet(
        client, headers, order_id, equipment_ids[0], template_key=template_key
    )
    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.capture_values["model"] == "Modelo QA"
        # Cierre UX 2026-09: "scope" ya no se prellena desde el equipo
        # (range_or_capacity se revirtió del alta) -- el técnico lo captura
        # directamente en la hoja cuando la plantilla lo pide.
        assert "scope" not in sheet.capture_values
        frozen_sha = sheet.final_pdf_sha256
        first_bytes, _ = generate_field_sheet_pdf(db, sheet_id)
    with factory() as db:
        second_bytes, _ = generate_field_sheet_pdf(db, sheet_id)
        assert db.get(FieldSheet, sheet_id).final_pdf_sha256 == frozen_sha
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
    them, not silently swallowed into an unused capture_values blob).

    Cierre de contrato canonico LAB (2026-09): company/address/attention son
    ahora snapshot readonly (ver CANONICAL_FIELD_SHEET_KEYS) -- un PATCH ya
    no puede cambiarlas, asi que este test ya no las incluye en el payload
    de actualizacion ni las verifica como "actualizadas" en el PDF (siguen
    apareciendo, pero con su valor original de creacion). instrument/brand/
    model/serial_number/internal_id son la misma historia (identidad del
    equipo dentro de capture_values) -- el payload los sigue enviando (asi
    lo hace Mobile hoy, reenvia el bloque completo) pero deben quedar
    intactos, no con el valor "actualizado" que el payload intento fijar.
    """
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
    original_capture_values = created_sheet.json()["capture_values"]

    # This mirrors what LabTechnicalCapture.saveSheet() sends: direct
    # FieldSheet columns at top level (only the captura-tecnica ones, since
    # company/address/attention/reception_date are readonly and Mobile no
    # longer renders them as editable Fields), plus the full capture_values
    # blob (identity keys included, exactly as read from the sheet).
    mobile_payload = {
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
            **original_capture_values,
            # Un intento de "actualizar" identidad vía capture_values -- debe
            # ser ignorado por completo, restaurado a lo que ya existia.
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
    # Identidad readonly: nunca cambia sin importar lo que el payload pida.
    for key in ("instrument", "brand", "model", "serial_number", "internal_id"):
        assert body["capture_values"][key] == original_capture_values[key], key
    # scope SI es captura tecnica -- ese si debe aceptar el nuevo valor.
    assert body["capture_values"]["scope"] == mobile_payload["capture_values"]["scope"]
    # company/address/attention nunca viajaron en este payload (ya no son
    # editables) -- siguen siendo el snapshot original de creacion.
    assert body["company"] == created_sheet.json()["company"]
    assert body["address"] == created_sheet.json()["address"]
    assert body["attention"] == created_sheet.json()["attention"]

    with factory() as db:
        pdf_bytes, _filename = generate_field_sheet_pdf(db, sheet_id)
    raw_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages
    )
    # Long values wrap across lines inside the PDF's narrow layout cards; collapse
    # whitespace so a wrapped value still matches as one contiguous string.
    rendered_text = re.sub(r"\s+", " ", raw_text).upper()

    for expected in (
        body["company"],
        body["address"],
        body["attention"],
        mobile_payload["units"],
        mobile_payload["method"],
        mobile_payload["observations"],
        original_capture_values["instrument"],
        original_capture_values["brand"],
        original_capture_values["serial_number"],
    ):
        assert expected.upper() in rendered_text, f"{expected!r} missing from {template_key} PDF"

    # Los valores que el payload intento colar por capture_values NUNCA
    # deben aparecer -- confirma que el PDF tampoco los recibio.
    for rejected in (
        mobile_payload["capture_values"]["instrument"],
        mobile_payload["capture_values"]["brand"],
        mobile_payload["capture_values"]["serial_number"],
    ):
        assert rejected.upper() not in rendered_text, f"{rejected!r} should have been ignored in {template_key} PDF"


# --------------------------------------------------------------------------
# Cierre de contrato canonico LAB (2026-09): ninguna plantilla (block.fields[])
# puede cambiar la obligatoriedad de un campo canonico; los campos
# especializados (fuera del contrato) siguen bajo autoridad de plantilla.
# --------------------------------------------------------------------------

def _inject_block_field_requirement(factory, sheet_id: int, *, key: str, required: bool) -> None:
    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        definition = dict(sheet.template_definition_json or {})
        blocks = [dict(block) for block in definition.get("blocks") or []]
        blocks.append(
            {
                "key": "test_injected_block",
                "block_key": "test_injected_block",
                "block_type": "CustomFieldsBlock",
                "title": "Bloque de prueba",
                "capture_visible": True,
                "visible_fields": [key],
                "fields": [{"key": key, "label": f"{key} (override de prueba)", "required": required, "order": 0}],
            }
        )
        definition["blocks"] = blocks
        sheet.template_definition_json = definition
        db.add(sheet)
        db.commit()


def test_template_cannot_make_a_canonical_field_required(lab_context):
    """Hallazgo 4: template_definition_json.blocks[].fields[].required ya no
    puede alterar la obligatoriedad de un campo canonico -- 'scope' es
    canonico (captura tecnica) y nunca se prellena al crear la hoja, asi que
    si la plantilla pudiera exigirlo, completar fallaria con 'scope' en
    missing_fields. Debe completarse igual, ignorando el override."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]
    assert not (created.json().get("capture_values") or {}).get("scope")

    _inject_block_field_requirement(factory, sheet_id, key="scope", required=True)

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
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"final_condition": "BUENA", "observations": "Sin observaciones", "results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text


def test_specialized_template_field_required_is_still_enforced(lab_context):
    """Un campo FUERA del contrato canonico (aqui 'pattern_used', legado de
    Patrones/StandardsBlock) sigue bajo autoridad real de la plantilla -- si
    la declara required=True y queda vacio, completar debe seguir
    rechazando con esa clave en missing_fields, exactamente como antes de
    separar canonico/especializado."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]

    _inject_block_field_requirement(factory, sheet_id, key="pattern_used", required=True)

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
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"final_condition": "BUENA", "observations": "Sin observaciones", "results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 422, completed.text
    assert "pattern_used" in completed.json()["detail"]["missing_fields"]


def test_final_condition_only_blocks_completion_when_a_template_declares_it_specialized_required(lab_context):
    """Fase 1 del contrato canonico LAB (2026-09, items 6 y 7):
    initial_condition/final_condition ya no son requisito universal (6) --
    completar sin llenarlos no bloquea por default -- pero si una plantilla
    especifica los declara required=True como campo especializado, si deben
    bloquear completitud (7), exactamente como cualquier otro campo
    especializado required."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]
    assert not created.json().get("final_condition")

    _inject_block_field_requirement(factory, sheet_id, key="final_condition", required=True)

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
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"observations": "Sin observaciones", "results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    blocked = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/complete",
        headers=headers,
    )
    assert blocked.status_code == 422, blocked.text
    assert "final_condition" in blocked.json()["detail"]["missing_fields"]

    filled = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"final_condition": "BUENA"},
        headers=headers,
    )
    assert filled.status_code == 200, filled.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text


def test_canonical_common_fields_validator_introduces_no_additional_requirements(lab_context):
    """Item B del cierre 2026-09: _validate_canonical_common_fields sigue
    siendo la unica autoridad de obligatoriedad del contrato canonico, pero
    hoy no agrega NINGUN requisito nuevo -- deliberado, para preservar el
    comportamiento existente. Prueba directa sobre una hoja recien creada
    con TODOS los campos canonicos de captura tecnica vacios (scope,
    calibration_place, environment_*, etc.): si la funcion agregara algun
    requisito, esta hoja los reportaria como faltantes."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]
    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert _validate_canonical_common_fields(sheet) == []


def test_equipment_update_syncs_identity_snapshot_of_the_editable_current_field_sheet(lab_context):
    """Fase 1 del contrato canonico LAB (2026-09, item 1.2/3): mientras la
    FieldSheet vigente sigue editable (draft/in_progress/rejected/
    returned_to_technician), cambiar instrument/brand/model/serial_number/
    identification via el flujo real de actualizacion de equipo
    (update_equipment/_update_equipment_core) debe sincronizar el snapshot
    congelado en capture_values -- direccion EXCLUSIVA Equipment -> FieldSheet
    editable, nunca al reves.

    Nota de alcance: hoy la unica forma de volver a dejar la OT en 'draft'
    (requisito de _ensure_members_editable para poder tocar el equipo) es
    reabrir una OT ya completed/partially_closed -- y para llegar a ese
    estado, TODAS sus FieldSheets ya deben estar 'completed' (nunca
    editable). Por eso esta prueba fuerza directamente la precondicion
    (OT en draft con una FieldSheet vigente todavia editable) para probar el
    mecanismo real en aislamiento, en vez de una secuencia de API que hoy no
    puede producir esa combinacion de estados -- reutiliza el endpoint/
    servicio real (PATCH .../equipment/{id} -> update_equipment ->
    _update_equipment_core -> _sync_field_sheet_identity_snapshot), no un
    mecanismo nuevo."""
    from app.models.lab_work_order import LabWorkOrderEquipment

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
    assert created.json()["capture_values"]["brand"] == "MYC Test"
    assert created.json()["capture_values"]["serial_number"] == "SER-1"

    with factory() as db:
        work_order = db.get(LabWorkOrder, order_id)
        work_order.status = "draft"
        # Misma limpieza que _reopen_closed_cohort hace para politica
        # 'invalidate' -- sin ella, _ensure_members_editable rechaza con "la
        # cohorte ya fue firmada" antes de llegar a la sincronizacion.
        work_order.signature_session_id = None
        db.commit()

    edited = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        json={
            "instrument": "Instrumento 1 corregido",
            "brand": "Marca corregida",
            "identification": "ID-1-CORREGIDO",
            "serial_number": "SER-1-CORREGIDO",
            "model": "Modelo corregido",
            "report_number": None,
            "is_good_condition": True,
        },
        headers=headers,
    )
    assert edited.status_code == 200, edited.text

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.status == "draft"
        assert sheet.capture_values["instrument"] == "Instrumento 1 corregido"
        assert sheet.capture_values["brand"] == "Marca corregida"
        assert sheet.capture_values["model"] == "Modelo corregido"
        assert sheet.capture_values["serial_number"] == "SER-1-CORREGIDO"
        assert sheet.capture_values["internal_id"] == "ID-1-CORREGIDO"
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.instrument == "Instrumento 1 corregido"


def test_field_sheet_edit_never_writes_back_into_equipment(lab_context):
    """Fase 1 (item 1.2/5): la sincronizacion es de UNA sola direccion --
    editar capture_values desde el lado FieldSheet (PATCH de captura) nunca
    debe escribir de vuelta en LabWorkOrderEquipment."""
    from app.models.lab_work_order import LabWorkOrderEquipment

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
    with factory() as db:
        equipment_before = db.get(LabWorkOrderEquipment, equipment_id)
        brand_before = equipment_before.brand
        serial_before = equipment_before.serial_number

    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"capture_values": {"instrument": "Hackeado", "brand": "Hackeado", "serial_number": "Hackeado"}},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    with factory() as db:
        equipment_after = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment_after.brand == brand_before
        assert equipment_after.serial_number == serial_before


def test_update_lab_field_sheet_keeps_identity_and_client_snapshot_readonly(lab_context):
    """Hallazgos 3 y 5: attention/company/address/reception_date (columnas
    directas) e instrument/brand/model/serial_number/internal_id (dentro de
    capture_values) son snapshot -- update_lab_field_sheet debe ignorar por
    completo cualquier intento de cambiarlos, y LabWorkOrderEquipment nunca
    se toca desde este flujo."""
    from app.models.lab_work_order import LabWorkOrderEquipment

    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    original = created.json()
    with factory() as db:
        equipment_before = db.get(LabWorkOrderEquipment, equipment_ids[0])
        equipment_snapshot_before = {
            "instrument": equipment_before.instrument,
            "brand": equipment_before.brand,
            "model": equipment_before.model,
            "serial_number": equipment_before.serial_number,
            "identification": equipment_before.identification,
        }

    attempted = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={
            "attention": "Suplantacion de atencion",
            "company": "Suplantacion de empresa",
            "address": "Suplantacion de domicilio",
            "reception_date": "2020-01-01",
            "capture_values": {
                **original["capture_values"],
                "instrument": "Suplantacion instrumento",
                "brand": "Suplantacion marca",
                "model": "Suplantacion modelo",
                "serial_number": "Suplantacion serie",
                "internal_id": "Suplantacion id",
            },
        },
        headers=headers,
    )
    assert attempted.status_code == 200, attempted.text
    body = attempted.json()

    assert body["attention"] == original["attention"]
    assert body["company"] == original["company"]
    assert body["address"] == original["address"]
    assert body["reception_date"] == original["reception_date"]
    for key in ("instrument", "brand", "model", "serial_number", "internal_id"):
        assert body["capture_values"][key] == original["capture_values"][key], key

    with factory() as db:
        equipment_after = db.get(LabWorkOrderEquipment, equipment_ids[0])
        assert equipment_after.instrument == equipment_snapshot_before["instrument"]
        assert equipment_after.brand == equipment_snapshot_before["brand"]
        assert equipment_after.model == equipment_snapshot_before["model"]
        assert equipment_after.serial_number == equipment_snapshot_before["serial_number"]
        assert equipment_after.identification == equipment_snapshot_before["identification"]


def test_four_official_templates_share_the_identical_canonical_block_structure(lab_context):
    """Tests 1/2 del encargo: anemometro/calibradores/presion/bascula deben
    producir exactamente el mismo contrato de captura comun -- mismos
    block_type en el mismo orden, con el mismo visible_fields, para los
    bloques que hoy alimentan el contrato canonico (Header/Client/Equipment/
    CalibrationData/Environmental/Observations). Sólo la tabla de resultados
    (7mo bloque) y las firmas cambian entre plantillas."""
    from app.services.field_sheet_templates import get_template_snapshot

    client, factory, tokens = lab_context
    with factory() as db:
        snapshots = {
            key: get_template_snapshot(db, key)[0]
            for key in ("anemometro", "calibradores", "presion", "bascula")
        }

    common_block_types = [
        "HeaderBlock", "ClientBlock", "EquipmentBlock",
        "CalibrationDataBlock", "EnvironmentalBlock", "ObservationsBlock",
    ]
    reference = snapshots["anemometro"]
    reference_blocks = {block["block_type"]: block for block in reference["blocks"] if block["block_type"] in common_block_types}
    assert set(reference_blocks) == set(common_block_types)

    for template_key, snapshot in snapshots.items():
        blocks_by_type = {block["block_type"]: block for block in snapshot["blocks"] if block["block_type"] in common_block_types}
        assert set(blocks_by_type) == set(common_block_types), template_key
        for block_type in common_block_types:
            assert blocks_by_type[block_type]["visible_fields"] == reference_blocks[block_type]["visible_fields"], (
                template_key,
                block_type,
            )


def test_official_templates_expose_organization_and_magnitude_metadata(lab_context):
    """Fase 2 del catalogo LAB (2026-09, items 2.1/2.4/2.5): las 4 plantillas
    oficiales llevan metadata.organization_key/organization_label/
    magnitude_key/magnitude_label/supported_equipment/search_aliases, y esa
    metadata viaja intacta a traves del endpoint que consume Mobile
    (GET .../field-sheet-templates) -- sin endpoint nuevo, sin catalogo
    estatico duplicado. Una plantilla sin esta metadata (aqui 'general',
    fallback sin organization_key) no debe fallar: metadata queda como dict
    vacio, fallback seguro sólo de presentacion."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    response = client.get(
        "/api/mobile/v1/technician/lab-work-orders/field-sheet-templates",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    by_key = {item["template_key"]: item for item in response.json()}

    expectations = {
        "anemometro": {"magnitude_key": "air_velocity", "magnitude_label": "Velocidad de aire", "equipment": "anemómetro", "variant_key": None, "variant_label": None},
        "calibradores": {"magnitude_key": "dimensional", "magnitude_label": "Dimensional", "equipment": "calibrador vernier", "variant_key": "calibradores", "variant_label": "Calibradores"},
        "presion": {"magnitude_key": "pressure", "magnitude_label": "Presión", "equipment": "manómetro", "variant_key": None, "variant_label": None},
        "bascula": {"magnitude_key": "mass", "magnitude_label": "Masa", "equipment": "báscula", "variant_key": None, "variant_label": None},
    }
    for template_key, expected in expectations.items():
        metadata = by_key[template_key]["metadata"]
        assert metadata["organization_key"] == "myc", template_key
        assert metadata["organization_label"] == "MYC", template_key
        assert metadata["magnitude_key"] == expected["magnitude_key"], template_key
        assert metadata["magnitude_label"] == expected["magnitude_label"], template_key
        assert expected["equipment"] in metadata["supported_equipment"], template_key
        assert isinstance(metadata["search_aliases"], list) and metadata["search_aliases"], template_key
        # Micro-cierre Fases 1/2 (hallazgo 2): document_variant distingue
        # variante documental dentro de la magnitud -- sólo 'calibradores'
        # tiene una hoy; el resto queda null (no es obligatorio inventar
        # una variante cuando sólo existe una hoja oficial por magnitud).
        assert metadata.get("document_variant_key") == expected["variant_key"], template_key
        assert metadata.get("document_variant_label") == expected["variant_label"], template_key

    # Plantilla fallback sin metadata de organizacion/magnitud (item 2.5):
    # no rompe, sólo no trae esas claves -- Mobile debe caer a `name`.
    general_metadata = by_key["general"]["metadata"]
    assert general_metadata.get("organization_key") is None
    assert general_metadata.get("magnitude_label") is None
    assert general_metadata.get("document_variant_label") is None


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
    # Micro-cierre Fases 1/2 (hallazgo 1): initial_condition/final_condition/
    # observations_or_evidence_notes ya NO son requisito universal para LAB --
    # una hoja "general" recien creada, sin ninguno de esos textos, sigue sin
    # poder completarse, pero ÚNICAMENTE porque le faltan resultados
    # estructurados (results_rows), la última validación real de la cadena.
    assert "final_condition" not in detail["missing_fields"]
    assert "initial_condition" not in detail["missing_fields"]
    assert "observations_or_evidence_notes" not in detail["missing_fields"]
    assert detail["missing_fields"] == ["results_rows"]


def test_lab_field_sheet_completes_with_observations_and_evidence_notes_both_empty(lab_context):
    """Micro-cierre Fases 1/2 (hallazgo 1, test A): una FieldSheet LAB
    completa con observations/evidence_notes/final_condition vacios (nunca
    llenados por el usuario), siempre que resultados y demas requisitos
    reales (aqui: results_rows) esten satisfechos -- ninguno de esos campos
    es requisito universal para LAB. (initial_condition ya llega prellenado
    por defecto al crear la hoja -- comportamiento previo sin relacion con
    este hallazgo, no se toca.)"""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert not created.json().get("observations")
    assert not created.json().get("evidence_notes")
    assert not created.json().get("final_condition")

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
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert not patched.json().get("observations")
    assert not patched.json().get("evidence_notes")

    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_specialized_evidence_notes_required_still_blocks_completion(lab_context):
    """Micro-cierre Fases 1/2 (hallazgo 1, test B): evidence_notes ya no
    pertenece al contrato canonico comun, pero sigue disponible como campo
    especializado -- si una plantilla lo declara required=True, debe seguir
    bloqueando completitud exactamente igual que cualquier otro campo
    especializado required."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_id = created.json()["id"]

    _inject_block_field_requirement(factory, sheet_id, key="evidence_notes", required=True)

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
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text

    blocked = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/complete",
        headers=headers,
    )
    assert blocked.status_code == 422, blocked.text
    assert "evidence_notes" in blocked.json()["detail"]["missing_fields"]

    filled = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"evidence_notes": "Evidencia adjunta"},
        headers=headers,
    )
    assert filled.status_code == 200, filled.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text


def test_productive_field_sheet_still_requires_observations_or_evidence_notes(lab_context):
    """Micro-cierre Fases 1/2 (hallazgo 1, test C): el FieldSheet productivo
    central (equipment_id, no lab_equipment_id) conserva exactamente su
    comportamiento actual -- observations_or_evidence_notes sigue siendo
    requisito universal fuera del dominio LAB."""
    from app.services.field_sheets import _validate_ready_to_complete

    sheet = FieldSheet(
        lab_equipment_id=None,
        template_key="general",
        initial_condition="BUENA",
        final_condition="BUENA",
        observations=None,
        evidence_notes=None,
    )
    with pytest.raises(HTTPException) as exc_info:
        _validate_ready_to_complete(sheet)
    assert exc_info.value.status_code == 422
    assert "observations_or_evidence_notes" in exc_info.value.detail["missing_fields"]


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


def _result_row(row_number: int, **row_data) -> FieldSheetResult:
    return FieldSheetResult(section_key="s", row_number=row_number, row_data=row_data)


def test_trim_trailing_empty_rows_keeps_only_up_to_the_last_meaningful_row():
    columns = [{"source": "pattern_value"}, {"source": "notes"}]
    rows = [
        _result_row(1, pattern_value="1.00"),
        _result_row(2, pattern_value="2.00"),
        _result_row(3),
        _result_row(4),
    ]
    trimmed = _trim_trailing_empty_rows(rows, columns)
    assert [row.row_number for row in trimmed] == [1, 2]


def test_trim_trailing_empty_rows_preserves_interior_gaps():
    columns = [{"source": "pattern_value"}]
    rows = [
        _result_row(1, pattern_value="1.00"),
        _result_row(2),
        _result_row(3, pattern_value="3.00"),
        _result_row(4),
        _result_row(5),
    ]
    trimmed = _trim_trailing_empty_rows(rows, columns)
    assert [row.row_number for row in trimmed] == [1, 2, 3]


def test_trim_trailing_empty_rows_prints_nothing_without_any_captured_data():
    columns = [{"source": "pattern_value"}]
    rows = [_result_row(1), _result_row(2), _result_row(3)]
    assert _trim_trailing_empty_rows(rows, columns) == []


def test_trim_trailing_empty_rows_ignores_whitespace_only_values():
    columns = [{"source": "notes"}]
    rows = [_result_row(1, notes="   "), _result_row(2, notes="real")]
    trimmed = _trim_trailing_empty_rows(rows, columns)
    assert [row.row_number for row in trimmed] == [1, 2]


@pytest.mark.parametrize("template_key", ["general", "manometro"])
def test_field_sheet_pdf_omits_trailing_empty_rows_across_families(lab_context, template_key):
    """Autoridad backend/documental (no sólo Mobile): la sección de resultados
    de la hoja congelada sólo trae hasta la última fila con captura real,
    para cualquier familia declarativa -- sin recortar huecos intermedios."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": template_key},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    sheet_json = created.json()
    result_section = sheet_json["template_definition"]["result_sections"][0]
    first_column_source = result_section["columns"][0]["source"]
    section_key = result_section["key"]
    section_rows = [row for row in sheet_json["results_rows"] if row["section_key"] == section_key]
    assert len(section_rows) >= 3, "family fixture must have at least 3 rows to prove the trim"
    rows_payload = [
        {
            "id": row["id"],
            "section_key": row["section_key"],
            "row_number": row["row_number"],
            "row_data": (
                {first_column_source: "1.00"}
                if row["row_number"] in (1, 3)
                else row["row_data"]
            ),
        }
        for row in sheet_json["results_rows"]
    ]
    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"final_condition": "BUENA", "observations": "Sin observaciones", "results_rows": rows_payload},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    sheet_id = completed.json()["id"]

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        sections = _group_sections(sheet, sheet.template_definition_json)
        target = next(section for section in sections if section.key == section_key)
        # Fila 1 y 3 tienen datos (huecos intermedio en la 2 se conserva);
        # de la 4 en adelante -- vacías -- no se imprimen.
        assert [row.row_number for row in target.rows] == [1, 2, 3]

        pdf_bytes, _filename = generate_field_sheet_pdf(db, sheet_id)
    raw_text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_bytes)).pages)
    rendered_text = re.sub(r"\s+", " ", raw_text)
    assert "1.00" in rendered_text


def test_mobile_can_download_the_completed_field_sheet_pdf(lab_context):
    """Cierre UX 2026-09: Mobile antes no tenía ninguna forma de descargar el
    PDF de una FieldSheet -- expone generate_field_sheet_pdf (mismo backend
    ya congelado) vía auth Mobile, sin renderer nuevo."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    _create_and_complete_field_sheet(client, headers, order_id, equipment_ids[0])

    downloaded = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet/pdf",
        headers=headers,
    )
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.headers["content-type"] == "application/pdf"
    assert downloaded.content.startswith(b"%PDF")


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


# --------------------------------------------------------------------------
# Fase 4 -- Mesa Técnica: cliente documental por equipo, prefill, permisos,
# frontera de estados y Ticket de plantilla faltante.
# --------------------------------------------------------------------------


def test_documentary_client_is_resolved_per_equipment_not_from_the_receiving_order(lab_context):
    """Cliente receptor A, cliente documental B -> FieldSheet.company/address/
    attention = B. Un tercer equipo sin 'different' sigue heredando A."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders",
        json=create_payload(client_name="Cliente Receptor A"),
        headers=headers,
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    equipment_ids = []
    for index in range(1, 3):
        added = client.post(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
            json=equipment_payload(index),
            headers=headers,
        )
        assert added.status_code == 201, added.text
        equipment_ids.append(added.json()["equipment"][-1]["id"])

    # Sólo el equipo 0 recibe un cliente documental distinto; se fija en
    # draft, como en el flujo real de recepción (LabEquipmentForm).
    different = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/certificate-client",
        json={
            "certificate_client_mode": "different",
            "final_client_company_snapshot": "Cliente Documental B",
            "final_client_address_snapshot": "Calle Documental B",
            "final_client_attention_snapshot": "Ing. Documental B",
        },
        headers=headers,
    )
    assert different.status_code == 200, different.text

    for equipment_id in equipment_ids:
        service = client.put(
            f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
            json={"service_type": "accredited", "linked_company_id": None},
            headers=headers,
        )
        assert service.status_code == 200, service.text
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text

    documental_b = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert documental_b.status_code == 201, documental_b.text
    assert documental_b.json()["company"] == "Cliente Documental B"
    assert documental_b.json()["address"] == "Calle Documental B"
    assert documental_b.json()["attention"] == "Ing. Documental B"

    receptor_a = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[1]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert receptor_a.status_code == 201, receptor_a.text
    assert receptor_a.json()["company"] == "Cliente Receptor A"
    assert receptor_a.json()["address"] == "Av. Prueba 123"
    assert receptor_a.json()["attention"] == "Persona Cliente"


def test_field_sheet_capture_values_prefill_from_available_equipment_fields(lab_context):
    """Cierre UX 2026-09: prefill con la identidad disponible en
    LabWorkOrderEquipment -- model ya es columna propia del equipo (mismo
    criterio que Equipment productivo) y se prellena; location/
    minimum_division/scope siguen siendo datos de la captura/servicio (ya
    viven en FieldSheet, scope ya no en el equipo desde que
    range_or_capacity se revirtió del alta) y no se prellenan desde el
    equipo. Sin model capturado en el equipo, queda explícitamente None (no
    se omite la clave, para que el contrato sea estable); "scope" no
    aparece en absoluto -- el técnico lo captura directamente en la hoja."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    capture_values = created.json()["capture_values"]
    assert capture_values == {
        "instrument": "Instrumento 1",
        "brand": "MYC Test",
        "serial_number": "SER-1",
        "internal_id": "ID-1",
        "model": None,
    }


def test_field_sheet_capture_values_prefill_includes_model_but_never_scope(lab_context):
    """Cierre UX 2026-09: cuando el equipo LAB trae model, la FieldSheet lo
    prefillea igual que instrument/brand/serial_number, pero "scope" nunca
    se prefillea desde el equipo -- range_or_capacity ya no es un dato de
    alta (ver migración 5e58473f1be6); el técnico lo captura en la hoja."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(
        client, headers, count=1, model="Modelo X-100",
    )
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    capture_values = created.json()["capture_values"]
    assert capture_values["model"] == "Modelo X-100"
    assert "scope" not in capture_values


def test_field_sheet_template_selection_freezes_snapshot_and_version(lab_context):
    """Seleccionar plantilla -> template_definition_json/version quedan
    congelados en la hoja, tal como los devolvió get_template_snapshot."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["template_key"] == "general"
    assert body["template_definition_version"] >= 1
    assert body["template_definition"]["pdf_template"] == "field_sheet_engine_pdf.html"
    with factory() as db:
        sheet = db.get(FieldSheet, body["id"])
        assert sheet.template_definition_json["pdf_template"] == body["template_definition"]["pdf_template"]
        assert sheet.template_definition_json["type"] == "general"
        assert sheet.template_definition_version == body["template_definition_version"]


def test_persisted_snapshot_wins_after_catalog_definition_changes(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    original_definition = created.json()["template_definition"]
    with factory() as db:
        changed = dict(original_definition)
        changed["name"] = "CATÁLOGO CAMBIADO DESPUÉS"
        db.add(FieldSheetTemplateDefinition(
            template_key="general",
            name=changed["name"],
            status="active",
            version=99,
            definition_json=changed,
        ))
        db.commit()
    loaded = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        headers=headers,
    )
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["template_definition"] == original_definition
    assert loaded.json()["template_definition"]["name"] != "CATÁLOGO CAMBIADO DESPUÉS"


def test_user_without_capture_permission_gets_403_creating_a_field_sheet(lab_context):
    """Un usuario sin field_sheets.capture/lab_work_orders.use/
    lab_field_sheets.capture (ninguna de las 3 autoridades del OR-gate) no
    puede crear una FieldSheet LAB -- el backend sigue siendo la autoridad,
    no un botón oculto en Mobile."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    with factory() as db:
        comercial_role = Role(name="Comercial", description="Comercial")
        db.add(comercial_role)
        db.flush()
        comercial = User(
            username="lab-comercial",
            email="lab-comercial@example.test",
            full_name="LAB Comercial",
            hashed_password="unused",
            account_type="internal",
            status="active",
            is_active=True,
            role_id=comercial_role.id,
            roles=[comercial_role],
        )
        db.add(comercial)
        db.commit()
        db.refresh(comercial)
        comercial_id = comercial.id
    comercial_token = create_access_token(
        str(comercial_id), extra_claims={"roles": ["Comercial"], "auth_context": "internal"}
    )
    denied = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=auth(comercial_token),
    )
    assert denied.status_code == 403, denied.text
    with factory() as db:
        assert db.get(LabWorkOrder, order_id).equipment  # OT intacta, nada se creó a medias


def test_opening_mesa_tecnica_never_mutates_status_only_creating_field_sheets_does(lab_context):
    """Abrir Mesa Técnica (leer la OT) no cambia received_signed. Crear la
    primera hoja -> in_progress; la segunda -> sigue in_progress; completar
    todas -> ready_to_close. Contrato de Fase 3, reverificado aquí porque
    Fase 4 toca el mismo create_lab_field_sheet que dispara la transición."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=2)

    with factory() as db:
        assert db.get(LabWorkOrder, order_id).status == "received_signed"
    for _ in range(3):
        opened = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers)
        assert opened.status_code == 200, opened.text
        assert opened.json()["status"] == "received_signed"

    first = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[0]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert first.status_code == 201, first.text
    assert client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()["status"] == "in_progress"

    second = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_ids[1]}/field-sheet",
        json={"template_key": "general"},
        headers=headers,
    )
    assert second.status_code == 201, second.text
    assert client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()["status"] == "in_progress"

    for equipment_id in equipment_ids:
        _complete_existing_field_sheet(client, headers, order_id, equipment_id)

    assert client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()["status"] == "ready_to_close"


def test_missing_template_ticket_is_created_and_no_field_sheet_is_invented(lab_context):
    """'No encuentro la hoja necesaria' reutiliza field_sheet_template_request
    (ya existente): crea el Ticket, nunca una FieldSheet ni una plantilla
    arbitraria."""
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_ids = _setup_order_with_equipment(client, headers, count=1)
    equipment_id = equipment_ids[0]

    ticket = client.post(
        "/api/mobile/v1/technician/tickets/field-sheet-template",
        json={
            "work_order_id": order_id,
            "equipment_id": equipment_id,
            "reason": "No existe plantilla para este instrumento",
            "description": "El instrumento es un patron de referencia sin plantilla configurada en el catalogo.",
        },
        headers=headers,
    )
    assert ticket.status_code == 201, ticket.text
    body = ticket.json()
    assert body["type"] == "field_sheet_template_request"
    assert body["status"] == "pending"
    assert body["work_order_id"] == order_id
    assert body["equipment_id"] == equipment_id

    with factory() as db:
        ticket_row = db.get(OperationalTicket, body["id"])
        assert ticket_row is not None
        assert ticket_row.work_order_id == order_id
        assert ticket_row.equipment_id == equipment_id

    order = client.get(f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers)
    assert order.status_code == 200, order.text
    equipment = next(item for item in order.json()["equipment"] if item["id"] == equipment_id)
    assert equipment["field_sheet_id"] is None
    assert equipment["field_sheet_status"] is None
