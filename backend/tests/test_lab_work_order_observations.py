"""observations por equipo LAB: schema, round-trip y su lugar en el PDF final.

Formato esperado en el PDF: "INSTRUMENTO -> IDENTIFICACIÓN : OBSERVACIÓN",
en el orden: 1) notas generales de la OT, 2) observaciones por equipo
(siguiendo position), 3) nota de reapertura -- nunca reutiliza report_number
ni certificate_folio para esto.

También cubre el snapshot inicial FieldSheet.observations <-
LabWorkOrderEquipment.observations que toma create_lab_field_sheet(): es una
copia congelada al crear la hoja, no un vínculo vivo -- ver el docstring de
esa función en app/services/lab_field_sheets.py."""

from __future__ import annotations

import base64
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
import io
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.field_sheet import FieldSheet
from app.models.lab_work_order import LabWorkOrderEquipment
from app.models.user import Role, User
from app.schemas.lab_work_order import LabEquipmentWrite


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def _equipment_payload(**overrides) -> dict:
    return {
        "instrument": "Manómetro",
        "brand": "MYC",
        "identification": "MAN-02",
        "serial_number": "SER-1",
        "is_good_condition": True,
        **overrides,
    }


def test_schema_accepts_observations():
    payload = LabEquipmentWrite(**_equipment_payload(observations="No tiene empaque"))
    assert payload.observations == "No tiene empaque"


def test_schema_normalizes_whitespace_only_observations_to_none():
    payload = LabEquipmentWrite(**_equipment_payload(observations="   \n\t  "))
    assert payload.observations is None


def test_schema_strips_surrounding_whitespace_from_observations():
    payload = LabEquipmentWrite(**_equipment_payload(observations="  No tiene empaque  "))
    assert payload.observations == "No tiene empaque"


def test_observations_defaults_to_none_when_omitted():
    payload = LabEquipmentWrite(**_equipment_payload())
    assert payload.observations is None


def test_report_number_and_observations_remain_independent_fields():
    payload = LabEquipmentWrite(**_equipment_payload(report_number="RPT-9", observations="No tiene empaque"))
    assert payload.report_number == "RPT-9"
    assert payload.observations == "No tiene empaque"
    assert payload.report_number != payload.observations


def test_create_update_round_trip_preserves_observations():
    created = LabEquipmentWrite(**_equipment_payload(observations="No tiene empaque"))
    updated = LabEquipmentWrite(**{**created.model_dump(), "observations": "Empaque reemplazado"})
    assert updated.observations == "Empaque reemplazado"
    assert updated.instrument == created.instrument


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------


def _equipment(position: int, instrument: str, identification: str, observations: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        position=position,
        instrument=instrument,
        brand="MYC",
        identification=identification,
        serial_number=f"SER-{position}",
        model=None,
        report_number=None,
        observations=observations,
        is_good_condition=True,
        certificate_folio=None,
        name=instrument,
        internal_id=identification,
    )


def _work_order(*, notes: str | None, equipment: list, revision_number: int = 1, reopen_ticket_id: int | None = None, signature_preserved: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        signature_session=None,
        client_name="Cliente PDF Observaciones",
        contact_name="Contacto",
        address="Domicilio",
        city="Guadalajara",
        state_name="Jalisco",
        postal_code="44100",
        purchase_order=None,
        notes=notes,
        equipment=equipment,
        active_equipment=equipment,
        reception_date=date(2026, 1, 1),
        departure_date=None,
        folio=6420,
        revision_number=revision_number,
        reopen_ticket_id=reopen_ticket_id,
        signature_preserved=signature_preserved,
    )


def _pdf_text(pdf_bytes: bytes) -> str:
    return "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf_bytes)).pages)


def test_pdf_renders_observation_in_the_expected_format():
    from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf

    work_order = _work_order(
        notes=None,
        equipment=[_equipment(1, "Manómetro", "MAN-02", "No tiene empaque")],
    )
    pdf, _filename = generate_lab_work_order_pdf(work_order)
    text = _pdf_text(pdf)
    assert "MANÓMETRO -> MAN-02 : NO TIENE EMPAQUE" in text


def test_pdf_orders_general_notes_before_per_equipment_observations_before_reopening_note():
    from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf

    work_order = _work_order(
        notes="Cliente solicitó revisión urgente",
        equipment=[_equipment(1, "Manómetro", "MAN-02", "No tiene empaque")],
        revision_number=2,
        reopen_ticket_id=77,
        signature_preserved=True,
    )
    pdf, _filename = generate_lab_work_order_pdf(work_order)
    text = _pdf_text(pdf)

    general_index = text.find("CLIENTE SOLICITÓ REVISIÓN URGENTE")
    observation_index = text.find("MANÓMETRO -> MAN-02")
    reopening_index = text.find("REAPERTURA AUTORIZADA")

    assert general_index != -1
    assert observation_index != -1
    assert reopening_index != -1
    assert general_index < observation_index < reopening_index


def test_pdf_keeps_multiple_equipment_observations_in_position_order():
    from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf

    work_order = _work_order(
        notes=None,
        equipment=[
            _equipment(2, "Termómetro", "TER-01", "Segunda observación"),
            _equipment(1, "Manómetro", "MAN-02", "Primera observación"),
        ],
    )
    pdf, _filename = generate_lab_work_order_pdf(work_order)
    text = _pdf_text(pdf)

    first_index = text.find("MANÓMETRO -> MAN-02 : PRIMERA OBSERVACIÓN")
    second_index = text.find("TERMÓMETRO -> TER-01 : SEGUNDA OBSERVACIÓN")
    assert first_index != -1
    assert second_index != -1
    assert first_index < second_index, "las observaciones deben seguir position, no el orden de la lista"


def test_pdf_omits_observation_line_when_equipment_has_none():
    from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf

    work_order = _work_order(
        notes=None,
        equipment=[_equipment(1, "Manómetro", "MAN-02", None)],
    )
    pdf, _filename = generate_lab_work_order_pdf(work_order)
    text = _pdf_text(pdf)
    assert "MANÓMETRO ->" not in text


def test_pdf_never_uses_report_number_or_certificate_folio_as_observation():
    from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf

    equipment = _equipment(1, "Manómetro", "MAN-02", "No tiene empaque")
    equipment.report_number = "RPT-DISTINTO"
    equipment.certificate_folio = "MYCT-99-99-0001"
    work_order = _work_order(notes=None, equipment=[equipment])
    pdf, _filename = generate_lab_work_order_pdf(work_order)
    text = _pdf_text(pdf)
    assert "NO TIENE EMPAQUE" in text
    assert "RPT-DISTINTO" not in text


# ---------------------------------------------------------------------------
# Snapshot inicial: FieldSheet.observations <- LabWorkOrderEquipment.observations
# ---------------------------------------------------------------------------

PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
).decode()


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
        tech_role = Role(name="Tecnico", description="Técnico")
        admin_role = Role(name="Administrador", description="Administrador")
        db.add_all([tech_role, admin_role])
        db.flush()
        users = {}
        for key, role in (("tech", tech_role), ("admin", admin_role)):
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
            users[key] = user
        db.add_all(users.values())
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
        for key, user in users.items()
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


def signatures_payload() -> dict:
    signed_at = datetime.now(timezone.utc).isoformat()
    return {
        "technician": {
            "signer_name": "Técnico LAB", "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
        "client": {
            "signer_name": "Cliente LAB", "signed_at": signed_at, "version": 1,
            "signature_data_url": PNG_DATA_URL,
        },
    }


def _create_and_sign_ready_order(client, headers, **equipment_extra) -> tuple[int, int]:
    order = client.post(
        "/api/mobile/v1/technician/lab-work-orders", json=create_payload(), headers=headers
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    added = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment",
        json=equipment_payload(1, **equipment_extra),
        headers=headers,
    )
    assert added.status_code == 201, added.text
    equipment_id = added.json()["equipment"][-1]["id"]
    service = client.put(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/service",
        json={"service_type": "traceable", "linked_company_id": None},
        headers=headers,
    )
    assert service.status_code == 200, service.text
    signed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=signatures_payload(),
        headers=headers,
    )
    assert signed.status_code == 200, signed.text
    return order_id, equipment_id


def _patch_equipment(client, headers, order_id, equipment_id, **overrides) -> dict:
    """PATCH /equipment/{id} exige el payload LabEquipmentWrite completo (no
    parcial): se relee el equipo vigente y se reenvían sus mismos campos
    identity, sobreescritos por overrides. update_equipment sólo procede si
    la OT está en draft (_ensure_members_editable) -- callers deben cerrar y
    reabrir primero (ver _close_order/_reopen_order)."""
    current = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()
    equipment = next(item for item in current["equipment"] if item["id"] == equipment_id)
    payload = {
        "instrument": equipment["instrument"],
        "brand": equipment["brand"],
        "identification": equipment["identification"],
        "serial_number": equipment["serial_number"],
        "model": equipment["model"],
        "report_number": equipment["report_number"],
        "is_good_condition": equipment["is_good_condition"],
        "observations": equipment["observations"],
        **overrides,
    }
    response = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def _close_order(client, headers, order_id: int) -> None:
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/complete/individual", headers=headers,
    )
    assert completed.status_code == 200, completed.text


def _reopen_order(client, headers, admin_headers, order_id: int, *, policy: str) -> dict:
    ticket = client.post(
        "/api/mobile/v1/technician/tickets",
        json={
            "work_order_id": order_id,
            "reason": "Corrección" if policy == "preserve" else "Corrección estructural",
            "description": "Ajuste de datos de recepción/equipo." if policy == "preserve"
                else "El equipo requiere corrección de identidad técnica.",
            "requested_signature_policy": policy,
        },
        headers=headers,
    )
    assert ticket.status_code == 201, ticket.text
    approved = client.post(
        f"/api/mobile/v1/technician/tickets/{ticket.json()['id']}/approve",
        json={"signature_policy": policy},
        headers=admin_headers,
    )
    assert approved.status_code == 200, approved.text
    reloaded = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    )
    assert reloaded.status_code == 200, reloaded.text
    return reloaded.json()


def _create_field_sheet(client, headers, order_id, equipment_id, *, template_key="general") -> dict:
    created = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"template_key": template_key},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    return created.json()


def _complete_field_sheet_without_touching_observations(client, headers, order_id, equipment_id) -> int:
    """Como complete_field_sheet_fully de test_lab_phase6_field_sheet_revisions.py,
    pero sin sobreescribir observations en el PATCH -- necesario aquí porque el
    valor bajo prueba es precisamente el snapshot inicial que create_lab_field_sheet
    ya congeló, y una hoja sin observations completa igual (ver
    test_lab_field_sheet_completes_with_observations_and_evidence_notes_both_empty
    en test_lab_field_sheets_capture.py)."""
    sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    rows = [
        {
            "id": row["id"],
            "section_key": row["section_key"],
            "row_number": row["row_number"],
            "row_data": {"result": "1.00"} if index == 0 else row["row_data"],
        }
        for index, row in enumerate(sheet["results_rows"])
    ]
    patched = client.patch(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        json={"final_condition": "BUENA", "results_rows": rows},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    completed = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/complete",
        headers=headers,
    )
    assert completed.status_code == 200, completed.text
    return completed.json()["id"]


def test_new_field_sheet_snapshots_the_equipment_observation(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = _create_and_sign_ready_order(
        client, headers, observations="No tiene empaque"
    )
    sheet = _create_field_sheet(client, headers, order_id, equipment_id)
    assert sheet["observations"] == "No tiene empaque"


def test_new_field_sheet_normalizes_whitespace_only_equipment_observation_to_none(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = _create_and_sign_ready_order(
        client, headers, observations="   \n\t  "
    )
    sheet = _create_field_sheet(client, headers, order_id, equipment_id)
    assert sheet["observations"] is None


def test_field_sheet_pdf_shows_the_snapshotted_observation(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = _create_and_sign_ready_order(
        client, headers, observations="No tiene empaque"
    )
    _create_field_sheet(client, headers, order_id, equipment_id)
    pdf = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet/pdf",
        headers=headers,
    )
    assert pdf.status_code == 200, pdf.text
    text = _pdf_text(pdf.content)
    assert "No tiene empaque" in text


def test_field_sheet_snapshot_never_reads_certificate_folio_or_report_number(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = _create_and_sign_ready_order(
        client,
        headers,
        observations="No tiene empaque",
        report_number="RPT-9",
    )
    detail = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}", headers=headers
    ).json()
    equipment = detail["equipment"][0]
    # "traceable" reserva folio MYCT automáticamente al crear el equipo (ver
    # configure_default_services en otros archivos de este suite) -- ya trae
    # certificate_folio propio, distinto de observations y de report_number.
    assert equipment["certificate_folio"]
    assert equipment["report_number"] == "RPT-9"

    sheet = _create_field_sheet(client, headers, order_id, equipment_id)
    assert sheet["observations"] == "No tiene empaque"
    assert sheet["observations"] != "RPT-9"
    assert sheet["observations"] != equipment["certificate_folio"]


def test_field_sheet_snapshot_ignores_report_number_when_equipment_has_no_observation(lab_context):
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    order_id, equipment_id = _create_and_sign_ready_order(
        client, headers, report_number="RPT-9"
    )
    sheet = _create_field_sheet(client, headers, order_id, equipment_id)
    assert sheet["observations"] is None


def test_editing_equipment_observation_after_creating_the_sheet_does_not_alter_it(lab_context):
    """update_equipment sólo procede con la OT en draft (_ensure_members_editable),
    así que la única forma real de volver a editar el equipo tras firmar es
    cerrar y reabrir (preserve). lab_client_id es None en estos payloads, así
    que _closable_status permite cerrar aunque la hoja siga in_progress (sin
    completar) -- exactamente el caso bajo prueba."""
    client, _factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = _create_and_sign_ready_order(
        client, headers, observations="Observación original"
    )
    sheet = _create_field_sheet(client, headers, order_id, equipment_id)
    assert sheet["observations"] == "Observación original"

    _close_order(client, headers, order_id)
    reopened = _reopen_order(client, headers, admin_headers, order_id, policy="preserve")
    _patch_equipment(
        client, headers, order_id, equipment_id,
        observations="Observación editada tras crear la hoja",
        expected_edit_version=reopened["edit_version"],
    )

    reloaded_sheet = client.get(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/equipment/{equipment_id}/field-sheet",
        headers=headers,
    ).json()
    assert reloaded_sheet["observations"] == "Observación original"


def test_completed_field_sheet_observation_is_immutable_to_later_equipment_edits(lab_context):
    client, factory, tokens = lab_context
    headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = _create_and_sign_ready_order(
        client, headers, observations="Observación al capturar"
    )
    _create_field_sheet(client, headers, order_id, equipment_id)
    sheet_id = _complete_field_sheet_without_touching_observations(client, headers, order_id, equipment_id)

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.status == "completed"
        assert sheet.observations == "Observación al capturar"

    _close_order(client, headers, order_id)
    reopened = _reopen_order(client, headers, admin_headers, order_id, policy="preserve")
    _patch_equipment(
        client, headers, order_id, equipment_id,
        observations="Intento de edición post-cierre",
        expected_edit_version=reopened["edit_version"],
    )

    with factory() as db:
        sheet = db.get(FieldSheet, sheet_id)
        assert sheet.status == "completed"
        assert sheet.observations == "Observación al capturar"


def test_reopened_revision_snapshots_the_current_observation_and_the_previous_revision_keeps_its_own(lab_context):
    """Único camino real para que la MISMA fila de equipo produzca una
    revisión 2 con otra observation: reopen invalidate + editar un campo
    crítico (CRITICAL_EQUIPMENT_FIELDS) en la misma llamada que cambia
    observations -- eso retira la revisión vigente (ver
    test_reopen_invalidate_with_critical_change_retires_old_revision_and_opens_a_new_one
    en test_lab_phase6_field_sheet_revisions.py, mismo patrón). observations
    por sí sola no es un campo crítico y no dispara el retiro."""
    client, factory, tokens = lab_context
    tech_headers = auth(tokens["tech"])
    admin_headers = auth(tokens["admin"])
    order_id, equipment_id = _create_and_sign_ready_order(
        client, tech_headers, observations="Observación de la revisión 1"
    )
    first_sheet = _create_field_sheet(client, tech_headers, order_id, equipment_id)
    assert first_sheet["observations"] == "Observación de la revisión 1"
    first_sheet_id = _complete_field_sheet_without_touching_observations(
        client, tech_headers, order_id, equipment_id
    )

    _close_order(client, tech_headers, order_id)
    reopened = _reopen_order(client, tech_headers, admin_headers, order_id, policy="invalidate")
    _patch_equipment(
        client, tech_headers, order_id, equipment_id,
        serial_number="SER-1-CORREGIDO",
        observations="Observación de la revisión 2",
        expected_edit_version=reopened["edit_version"],
    )

    with factory() as db:
        equipment = db.get(LabWorkOrderEquipment, equipment_id)
        assert equipment.field_sheet is None
        first = db.get(FieldSheet, first_sheet_id)
        assert first.is_current is False
        assert first.observations == "Observación de la revisión 1"

    resigned = client.post(
        f"/api/mobile/v1/technician/lab-work-orders/{order_id}/signatures/individual",
        json=signatures_payload(),
        headers=tech_headers,
    )
    assert resigned.status_code == 200, resigned.text

    second_sheet = _create_field_sheet(client, tech_headers, order_id, equipment_id)
    assert second_sheet["id"] != first_sheet_id
    assert second_sheet["observations"] == "Observación de la revisión 2"

    with factory() as db:
        first = db.get(FieldSheet, first_sheet_id)
        second = db.get(FieldSheet, second_sheet["id"])
        assert first.is_current is False
        assert first.observations == "Observación de la revisión 1"
        assert second.is_current is True
        assert second.observations == "Observación de la revisión 2"
        assert second.supersedes_field_sheet_id == first_sheet_id


def test_ot_pdf_format_for_observations_is_unaffected_by_the_field_sheet_snapshot():
    """El formato "INSTRUMENTO -> IDENTIFICACIÓN : OBSERVACIÓN" del PDF de OT
    (probado exhaustivamente arriba: orden general/equipo/reapertura, position,
    ausencia cuando no hay observation, independencia de report_number/
    certificate_folio) lee LabWorkOrderEquipment.observations directamente --
    el snapshot nuevo en FieldSheet.observations es un campo distinto que
    generate_lab_work_order_pdf ni siquiera consulta. No se duplica esa
    cobertura aquí; este test sólo deja explícito que ambos campos conviven
    sin que uno reemplace al otro."""
    from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf

    equipment = _equipment(1, "Manómetro", "MAN-02", "Observación del equipo")
    work_order = _work_order(notes=None, equipment=[equipment])
    pdf, _filename = generate_lab_work_order_pdf(work_order)
    text = _pdf_text(pdf)
    assert "MANÓMETRO -> MAN-02 : OBSERVACIÓN DEL EQUIPO" in text
