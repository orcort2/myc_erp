"""observations por equipo LAB: schema, round-trip y su lugar en el PDF final.

Formato esperado en el PDF: "INSTRUMENTO -> IDENTIFICACIÓN : OBSERVACIÓN",
en el orden: 1) notas generales de la OT, 2) observaciones por equipo
(siguiendo position), 3) nota de reapertura -- nunca reutiliza report_number
ni certificate_folio para esto."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from pypdf import PdfReader
import io

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
