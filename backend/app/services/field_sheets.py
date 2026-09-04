from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.certificate import Certificate
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet, FieldSheetResult, FieldSheetSignature
from app.models.reference_standard import FieldSheetReferenceStandard, ReferenceStandard
from app.models.reference_standard_certificate import ReferenceStandardCertificate
from app.models.service_order import ServiceOrder
from app.models.calibration_procedure import CalibrationProcedure
from app.schemas.field_sheet import (
    FieldSheetCreate,
    FieldSheetResultUpdate,
    FieldSheetSignatureUpdate,
    FieldSheetStatusChange,
    FieldSheetUpdate,
)
from app.services.audit_logs import write_audit_log
from app.services.activity import publish_event
from app.services.equipment import sync_service_order_equipment_counts
from app.services.field_sheet_templates import (
    CANONICAL_PDF_RENDERER_KEY,
    CANONICAL_PDF_RENDERER_VERSION,
    build_default_result_rows,
    canonicalize_new_field_sheet_snapshot,
    get_field_sheet_template,
    get_template_snapshot,
)
from app.services.institutional_configurations import (
    get_or_create_institutional_configuration,
    institutional_snapshot,
)
FIELD_SHEET_REFERENCE_USAGE_ROLES = {
    "primary",
    "secondary",
    "auxiliary",
    "environmental",
    "other",
}
EDITABLE_STATUSES = {"draft", "in_progress", "rejected", "returned_to_technician"}
TERMINAL_STATUSES = {"approved", "cancelled"}

# Cierre de contrato canonico LAB (2026-09): estas claves son la experiencia
# de captura comun a TODAS las hojas de campo LAB Mobile -- ninguna
# plantilla (ni una FieldSheetTemplateDefinition editada por Admin) puede
# redefinir su label/orden/tipo/obligatoriedad. Ver
# myc-mobile/src/services/field-sheet-canonical-contract.ts para el mismo
# contrato del lado Mobile (duplicado deliberado: no hay codegen compartido
# en este repo, mismo patron ya usado para otros contratos LAB/Mobile).
# Los bloques de plantilla (HeaderBlock/ClientBlock/EquipmentBlock/...)
# siguen existiendo para layout/PDF; sencillamente esta clave ya no
# participa en la resolucion de campos de captura comun ni en su
# obligatoriedad -- ver _validate_specialized_template_fields.
CANONICAL_FIELD_SHEET_KEYS = frozenset(
    {
        # Identidad documental (readonly, snapshot de la OT)
        "work_order_number",
        "reserved_certificate_folio",
        # Cliente (readonly, snapshot del cliente documental por equipo)
        "attention",
        "company",
        "address",
        # Equipo (readonly, snapshot de LabWorkOrderEquipment)
        "instrument",
        "brand",
        "model",
        "serial_number",
        "internal_id",
        # Equipo (captura tecnica)
        "scope",
        "minimum_division",
        "location",
        # Calibracion (reception_date es readonly; el resto es captura tecnica)
        "reception_date",
        "calibration_place",
        "calibration_date",
        "next_calibration_date",
        # Ambientales (captura tecnica)
        "environment_humidity_start",
        "environment_humidity_end",
        "environment_temperature_start",
        "environment_temperature_end",
        # Condicion / observaciones (captura tecnica)
        "equipment_general_condition",
        "consider_equipment_deviations",
        "observations",
    }
)


def _json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _serialize_result_rows(rows: list[FieldSheetResult]) -> list[dict]:
    return [
        {
            "id": row.id,
            "section_key": row.section_key,
            "row_number": row.row_number,
            "pattern_value": row.pattern_value,
            "ibc_value_1": row.ibc_value_1,
            "ibc_value_2": row.ibc_value_2,
            "ibc_value_3": row.ibc_value_3,
            "unit": row.unit,
            "notes": row.notes,
            "row_data": row.row_data or {},
        }
        for row in rows
    ]


def _serialize_field_sheet(field_sheet: FieldSheet) -> dict:
    return {
        "equipment_id": field_sheet.equipment_id,
        "lab_equipment_id": field_sheet.lab_equipment_id,
        "lab_signature_session_id": field_sheet.lab_signature_session_id,
        "work_order_id": field_sheet.work_order_id,
        "calibration_procedure_id": field_sheet.calibration_procedure_id,
        "template_key": field_sheet.template_key,
        "work_order_number": field_sheet.work_order_number,
        "status": field_sheet.status,
        "calibration_place": field_sheet.calibration_place,
        "minimum_division": field_sheet.minimum_division,
        "location": field_sheet.location,
        "attention": field_sheet.attention,
        "company": field_sheet.company,
        "address": field_sheet.address,
        "reception_date": field_sheet.reception_date.isoformat() if field_sheet.reception_date else None,
        "calibration_date": field_sheet.calibration_date.isoformat() if field_sheet.calibration_date else None,
        "next_calibration_date": field_sheet.next_calibration_date.isoformat() if field_sheet.next_calibration_date else None,
        "environment_humidity_start": field_sheet.environment_humidity_start,
        "environment_humidity_end": field_sheet.environment_humidity_end,
        "environment_temperature_start": field_sheet.environment_temperature_start,
        "environment_temperature_end": field_sheet.environment_temperature_end,
        "equipment_general_condition": field_sheet.equipment_general_condition,
        "consider_equipment_deviations": field_sheet.consider_equipment_deviations,
        "units": field_sheet.units,
        "calibrated_by": field_sheet.calibrated_by,
        "reviewed_by": field_sheet.reviewed_by,
        "report_made_by": field_sheet.report_made_by,
        "purchase_order_or_quotation": field_sheet.purchase_order_or_quotation,
        "initial_condition": field_sheet.initial_condition,
        "final_condition": field_sheet.final_condition,
        "pattern_used": field_sheet.pattern_used,
        "results": field_sheet.results,
        "observations": field_sheet.observations,
        "evidence_notes": field_sheet.evidence_notes,
        "method": field_sheet.method,
        "environmental_conditions": field_sheet.environmental_conditions,
        "technician_notes": field_sheet.technician_notes,
        "template_definition": field_sheet.template_definition,
        "template_definition_version": field_sheet.template_definition_version,
        "pdf_renderer_key": field_sheet.pdf_renderer_key,
        "pdf_renderer_version": field_sheet.pdf_renderer_version,
        "final_pdf_path": field_sheet.final_pdf_path,
        "final_pdf_sha256": field_sheet.final_pdf_sha256,
        "final_pdf_template_definition_version": field_sheet.final_pdf_template_definition_version,
        "final_pdf_generated_at": field_sheet.final_pdf_generated_at.isoformat()
        if field_sheet.final_pdf_generated_at
        else None,
        "institutional_snapshot": field_sheet.institutional_snapshot_json,
        "certificate_client_mode": field_sheet.certificate_client_mode,
        "certificate_client_company": field_sheet.certificate_client_company,
        "certificate_client_attention": field_sheet.certificate_client_attention,
        "certificate_client_address": field_sheet.certificate_client_address,
        "apply_certificate_client_to_order": field_sheet.apply_certificate_client_to_order,
        "capture_values": field_sheet.capture_values or {},
        "reserved_certificate_folio": field_sheet.reserved_certificate_folio,
        "results_rows": _serialize_result_rows(field_sheet.results_rows),
        "signatures": [
            {
                "id": signature.id,
                "role": signature.role,
                "display_label": signature.display_label,
                "name": signature.name,
                "signature_data": signature.signature_data,
                "signed_at": signature.signed_at.isoformat() if signature.signed_at else None,
                "user_id": signature.user_id,
                "position": signature.position,
            }
            for signature in field_sheet.signatures
        ],
        "reference_standards": [
            {
                "reference_standard_id": link.reference_standard_id,
                "usage_role": link.usage_role,
                "measurement_section": link.measurement_section,
                "notes": link.notes,
            }
            for link in field_sheet.reference_standard_links
        ],
    }


def _ensure_active_equipment(db: Session, equipment_id: int) -> Equipment:
    equipment = db.scalar(
        select(Equipment)
        .where(Equipment.id == equipment_id, Equipment.is_active.is_(True))
        .options(
            selectinload(Equipment.service_order).selectinload(ServiceOrder.client),
            selectinload(Equipment.service_order).selectinload(ServiceOrder.quotation),
            selectinload(Equipment.work_order),
        )
            
    )
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado",
        )
    if equipment.status in {"not_done", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede modificar hoja de campo de un equipo terminal",
        )
    return equipment


def _inherit_certificate_client_from_order(
    db: Session,
    *,
    service_order_id: int,
) -> dict[str, str | bool | None]:
    previous_sheet = db.scalar(
        select(FieldSheet)
        .join(Equipment, Equipment.id == FieldSheet.equipment_id)
        .where(
            Equipment.service_order_id == service_order_id,
            FieldSheet.is_active.is_(True),
            FieldSheet.apply_certificate_client_to_order.is_(True),
            FieldSheet.certificate_client_mode == "different",
        )
        .order_by(FieldSheet.created_at.desc())
    )
    if previous_sheet is None:
        return {}
    return {
        "certificate_client_mode": "different",
        "certificate_client_company": previous_sheet.certificate_client_company,
        "certificate_client_attention": previous_sheet.certificate_client_attention,
        "certificate_client_address": previous_sheet.certificate_client_address,
        "apply_certificate_client_to_order": True,
    }


def _client_address(client) -> str | None:
    parts = [
        client.street,
        client.exterior_number,
        client.interior_number,
        client.neighborhood,
        client.locality,
        client.municipality,
        client.city,
        client.state,
        client.postal_code,
        client.country,
    ]
    value = ", ".join(str(part).strip() for part in parts if part and str(part).strip())
    return value or None


def _ensure_no_active_field_sheet(db: Session, equipment_id: int) -> None:
    exists = db.scalar(
        select(FieldSheet.id).where(
            FieldSheet.equipment_id == equipment_id,
            FieldSheet.is_active.is_(True),
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El equipo ya tiene una hoja de campo activa",
        )

def _ensure_calibration_procedure(
    db: Session, calibration_procedure_id: int | None
) -> CalibrationProcedure | None:
    if calibration_procedure_id is None:
        return None
    procedure = db.scalar(
        select(CalibrationProcedure).where(
            CalibrationProcedure.id == calibration_procedure_id,
            CalibrationProcedure.is_active.is_(True),
        )
    )
    if procedure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedimiento de calibracion no encontrado",
        )
    return procedure


def _resolve_reference_standards(
    db: Session,
    items: list,
) -> list[tuple[FieldSheetReferenceStandard, ReferenceStandard]]:
    if not items:
        return []
    standard_ids = [item.reference_standard_id for item in items]
    standards = list(
        db.scalars(
            select(ReferenceStandard)
            .options(selectinload(ReferenceStandard.certificates).selectinload(ReferenceStandardCertificate.uncertainties))
            .where(ReferenceStandard.id.in_(standard_ids))
            .where(ReferenceStandard.is_active.is_(True))
        ).all()
    )
    standards_by_id = {standard.id: standard for standard in standards}
    missing_ids = sorted(set(standard_ids) - set(standards_by_id))
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Patrones no encontrados", "reference_standard_ids": missing_ids},
        )

    resolved: list[tuple[FieldSheetReferenceStandard, ReferenceStandard]] = []
    seen: set[tuple[int, str, str | None]] = set()
    for item in items:
        if item.usage_role not in FIELD_SHEET_REFERENCE_USAGE_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"usage_role invalido: {item.usage_role}",
            )
        dedupe_key = (item.reference_standard_id, item.usage_role, item.measurement_section)
        if dedupe_key in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="No repitas el mismo patron con el mismo rol y seccion.",
            )
        seen.add(dedupe_key)
        resolved.append(
            (
                FieldSheetReferenceStandard(
                    reference_standard_id=item.reference_standard_id,
                    usage_role=item.usage_role,
                    measurement_section=item.measurement_section,
                    notes=item.notes,
                ),
                standards_by_id[item.reference_standard_id],
            )
        )
    return resolved


def _validate_results_rows(field_sheet: FieldSheet) -> None:
    has_measurement = any(
        any([str(value).strip() for value in (row.row_data or {}).values() if value not in (None, "")])
        or any(
            [
                row.pattern_value and row.pattern_value.strip(),
                row.ibc_value_1 and row.ibc_value_1.strip(),
                row.ibc_value_2 and row.ibc_value_2.strip(),
                row.ibc_value_3 and row.ibc_value_3.strip(),
            ]
        )
        for row in field_sheet.results_rows
    )
    if not has_measurement:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Faltan resultados estructurados de calibracion",
                "missing_fields": ["results_rows"],
            },
        )


_FIELD_SHEET_KEY_ALIASES = {
    "humidity_start": "environment_humidity_start",
    "humidity_end": "environment_humidity_end",
    "temperature_start": "environment_temperature_start",
    "temperature_end": "environment_temperature_end",
}


def _validate_canonical_common_fields(field_sheet: FieldSheet) -> list[str]:
    """Autoridad FIJA de obligatoriedad para el contrato canonico comun
    (ver CANONICAL_FIELD_SHEET_KEYS) -- ninguna plantilla participa aqui.

    Hoy no agrega requisitos propios mas alla de los ya fijos que existian
    antes de esta separacion (initial_condition/final_condition/
    observations_or_evidence_notes, ver _validate_ready_to_complete): esos
    quedan como estaban porque no son parte del contrato canonico nuevo.
    Este es el punto unico donde una futura obligatoriedad canonica fija
    (independiente de plantilla) se agregaria."""
    return []


def _validate_specialized_template_fields(field_sheet: FieldSheet) -> list[str]:
    """Autoridad de plantilla: SOLO para claves fuera del contrato canonico
    comun. Una plantilla (o una FieldSheetTemplateDefinition editada desde
    Admin) puede declarar un campo especializado required=True y este lazo
    lo exige -- pero si esa clave (o su alias) pertenece al contrato
    canonico, se ignora por completo: la plantilla no tiene autoridad sobre
    la obligatoriedad de un campo canonico."""
    missing_fields: list[str] = []
    capture_values = field_sheet.capture_values or {}
    for block in (field_sheet.template_definition_json or {}).get("blocks") or []:
        for field in block.get("fields") or []:
            key = field.get("key")
            model_key = _FIELD_SHEET_KEY_ALIASES.get(key, key)
            if model_key in CANONICAL_FIELD_SHEET_KEYS or key in CANONICAL_FIELD_SHEET_KEYS:
                continue
            if not field.get("required"):
                continue
            value = getattr(field_sheet, model_key, None)
            if value in (None, ""):
                value = capture_values.get(key)
            if value in (None, "") and key not in missing_fields:
                missing_fields.append(key)
    return missing_fields


def _validate_ready_to_complete(field_sheet: FieldSheet) -> None:
    missing_fields = []
    # Fase 1 del contrato canonico LAB (2026-09, item 1.3): initial_condition/
    # final_condition dejan de ser requisito UNIVERSAL para hojas LAB -- no
    # pertenecen al contrato comun (ver CANONICAL_FIELD_SHEET_KEYS) y sólo
    # deben bloquear completitud si una plantilla especifica los declara
    # explicitamente como campo especializado required (ya cubierto por
    # _validate_specialized_template_fields, sin cambios). El FieldSheet
    # productivo (equipment_id, no lab_equipment_id) no participa de este
    # contrato canonico LAB y conserva exactamente su comportamiento actual.
    if field_sheet.lab_equipment_id is None:
        required_fields = {
            "initial_condition": field_sheet.initial_condition,
            "final_condition": field_sheet.final_condition,
        }
        for field_name, value in required_fields.items():
            if not value or not value.strip():
                missing_fields.append(field_name)

    missing_fields.extend(_validate_canonical_common_fields(field_sheet))
    for key in _validate_specialized_template_fields(field_sheet):
        if key not in missing_fields:
            missing_fields.append(key)

    # Micro-cierre Fases 1/2 (hallazgo 1): observations_or_evidence_notes era
    # el ultimo requisito legado UNIVERSAL para LAB, contradiciendo el
    # contrato canonico (observations pertenece al contrato comun pero
    # required=false; evidence_notes ni siquiera pertenece a el). Igual que
    # initial_condition/final_condition arriba, este chequeo queda
    # exclusivamente para el FieldSheet productivo (equipment_id, no
    # lab_equipment_id), que conserva su comportamiento actual sin cambios.
    # Para LAB, evidence_notes sigue disponible como campo especializado: si
    # una plantilla futura lo declara required=True,
    # _validate_specialized_template_fields ya lo exige (sin cambios aqui).
    if field_sheet.lab_equipment_id is None:
        has_observations = bool(field_sheet.observations and field_sheet.observations.strip())
        has_evidence = bool(field_sheet.evidence_notes and field_sheet.evidence_notes.strip())
        if not has_observations and not has_evidence:
            missing_fields.append("observations_or_evidence_notes")

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Faltan datos tecnicos para completar la hoja de campo",
                "missing_fields": missing_fields,
            },
        )

    _validate_results_rows(field_sheet)


def _apply_results_updates(field_sheet: FieldSheet, results_rows: list[FieldSheetResultUpdate]) -> None:
    existing_by_id = {row.id: row for row in field_sheet.results_rows}
    existing_by_key = {(row.section_key, row.row_number): row for row in field_sheet.results_rows}
    new_rows: list[FieldSheetResult] = []
    for row_payload in results_rows:
        row_data = row_payload.model_dump(exclude={"id"})
        raw_data = dict(row_data.get("row_data") or {})
        for key in ("pattern_value", "ibc_value_1", "ibc_value_2", "ibc_value_3", "unit", "notes"):
            if row_data.get(key) not in (None, ""):
                raw_data.setdefault(key, row_data.get(key))
        row_data["row_data"] = raw_data
        existing_row = (
            existing_by_id.get(row_payload.id)
            if row_payload.id is not None
            else existing_by_key.get((row_payload.section_key, row_payload.row_number))
        )
        if existing_row is not None:
            row = existing_row
            for key, value in row_data.items():
                setattr(row, key, value)
            new_rows.append(row)
        else:
            new_rows.append(FieldSheetResult(**row_data))
    field_sheet.results_rows = new_rows


def _default_signature_slots(template_definition: dict, field_sheet: FieldSheet) -> list[FieldSheetSignature]:
    slots = template_definition.get("signature_layout", {}).get("slots") or [
        {"role": "calibrated_by", "display_label": "Calibró"},
        {"role": "reviewed_by", "display_label": "Revisó"},
        {"role": "report_made_by", "display_label": "Elaboró informe"},
    ]
    legacy_names = {
        "calibrated_by": field_sheet.calibrated_by,
        "reviewed_by": field_sheet.reviewed_by,
        "report_made_by": field_sheet.report_made_by,
    }
    return [
        FieldSheetSignature(
            role=slot["role"],
            display_label=slot.get("display_label") or slot["role"],
            name=legacy_names.get(slot["role"]),
            position=index,
        )
        for index, slot in enumerate(slots)
    ]


def _apply_signature_updates(
    field_sheet: FieldSheet,
    signatures: list[FieldSheetSignatureUpdate],
) -> None:
    existing_by_id = {signature.id: signature for signature in field_sheet.signatures}
    existing_by_role = {signature.role: signature for signature in field_sheet.signatures}
    next_signatures: list[FieldSheetSignature] = []
    for index, payload in enumerate(signatures):
        signature = existing_by_id.get(payload.id) if payload.id is not None else None
        signature = signature or existing_by_role.get(payload.role)
        values = payload.model_dump(exclude={"id"})
        values["position"] = values.get("position", index)
        if signature is None:
            signature = FieldSheetSignature(**values)
        else:
            for key, value in values.items():
                setattr(signature, key, value)
        next_signatures.append(signature)
    field_sheet.signatures = next_signatures

    names_by_role = {signature.role: signature.name for signature in next_signatures}
    field_sheet.calibrated_by = names_by_role.get("calibrated_by", field_sheet.calibrated_by)
    field_sheet.reviewed_by = names_by_role.get("reviewed_by", field_sheet.reviewed_by)
    field_sheet.report_made_by = names_by_role.get("report_made_by", field_sheet.report_made_by)


def _first_current_certificate(standard: ReferenceStandard) -> ReferenceStandardCertificate | None:
    current = [
        certificate
        for certificate in standard.certificates
        if certificate.is_current and certificate.status == "active"
    ]
    return current[0] if current else None


def _apply_reference_standard_updates(
    field_sheet: FieldSheet,
    items: list,
    resolved: list[tuple[FieldSheetReferenceStandard, ReferenceStandard]] | None = None,
) -> None:
    standards_by_id = {standard.id: standard for _, standard in (resolved or [])}
    existing_by_key = {
        (link.reference_standard_id, link.usage_role, link.measurement_section): link
        for link in field_sheet.reference_standard_links
    }
    new_links: list[FieldSheetReferenceStandard] = []
    for item in items:
        key = (item.reference_standard_id, item.usage_role, item.measurement_section)
        existing = existing_by_key.get(key)
        standard = standards_by_id.get(item.reference_standard_id)
        certificate = _first_current_certificate(standard) if standard is not None else None
        uncertainty = (
            next((row for row in certificate.uncertainties if row.is_active), None)
            if certificate is not None
            else None
        )
        if existing is not None:
            existing.notes = item.notes
            if certificate is not None:
                existing.reference_standard_certificate_id = certificate.id
                existing.selected_uncertainty_id = uncertainty.id if uncertainty is not None else None
                existing.selection_status = "auto_selected"
                existing.validation_snapshot = {
                    "certificate_number": certificate.certificate_number,
                    "certificate_expiration_date": certificate.expiration_date.isoformat()
                    if certificate.expiration_date
                    else None,
                    "uncertainty_id": uncertainty.id if uncertainty is not None else None,
                }
            new_links.append(existing)
        else:
            new_links.append(
                FieldSheetReferenceStandard(
                    reference_standard_id=item.reference_standard_id,
                    reference_standard_certificate_id=certificate.id if certificate is not None else None,
                    selected_uncertainty_id=uncertainty.id if uncertainty is not None else None,
                    usage_role=item.usage_role,
                    measurement_section=item.measurement_section,
                    selection_status="auto_selected" if certificate is not None else None,
                    validation_snapshot={
                        "certificate_number": certificate.certificate_number,
                        "certificate_expiration_date": certificate.expiration_date.isoformat()
                        if certificate.expiration_date
                        else None,
                        "uncertainty_id": uncertainty.id if uncertainty is not None else None,
                    }
                    if certificate is not None
                    else None,
                    notes=item.notes,
                )
            )
    field_sheet.reference_standard_links = new_links


def list_field_sheets(
    db: Session,
    *,
    equipment_id: int | None = None,
    work_order_id: int | None = None,
    include_inactive: bool = False,
) -> list[FieldSheet]:
    query = (
        select(FieldSheet)
        .options(
            selectinload(FieldSheet.certificates),
            selectinload(FieldSheet.results_rows),
            selectinload(FieldSheet.signatures),
            selectinload(FieldSheet.equipment).selectinload(Equipment.certificates),
            selectinload(FieldSheet.lab_equipment),
            selectinload(FieldSheet.equipment).selectinload(Equipment.service_order).selectinload(ServiceOrder.client),
            selectinload(FieldSheet.equipment).selectinload(Equipment.service_order).selectinload(ServiceOrder.quotation),
            selectinload(FieldSheet.calibration_procedure),
            selectinload(FieldSheet.reference_standard_links).selectinload(
                FieldSheetReferenceStandard.reference_standard
            ).selectinload(ReferenceStandard.uncertainties),
        )
        .order_by(FieldSheet.created_at.desc())
    )
    if equipment_id is not None:
        query = query.where(FieldSheet.equipment_id == equipment_id)
    if work_order_id is not None:
        query = query.where(FieldSheet.work_order_id == work_order_id)
        
    if not include_inactive:
        query = query.where(FieldSheet.is_active.is_(True))
    return list(db.scalars(query).all())


def get_field_sheet(db: Session, field_sheet_id: int) -> FieldSheet:
    field_sheet = db.scalar(
        select(FieldSheet)
        .where(FieldSheet.id == field_sheet_id)
        .options(
            selectinload(FieldSheet.certificates),
            selectinload(FieldSheet.results_rows),
            selectinload(FieldSheet.signatures),
            selectinload(FieldSheet.equipment).selectinload(Equipment.certificates),
            selectinload(FieldSheet.lab_equipment),
            selectinload(FieldSheet.equipment).selectinload(Equipment.service_order).selectinload(ServiceOrder.client),
            selectinload(FieldSheet.equipment).selectinload(Equipment.service_order).selectinload(ServiceOrder.quotation),
            selectinload(FieldSheet.calibration_procedure),
            selectinload(FieldSheet.reference_standard_links).selectinload(
                FieldSheetReferenceStandard.reference_standard
            ).selectinload(ReferenceStandard.uncertainties),
        )
    )
    if field_sheet is None or not field_sheet.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hoja de campo no encontrada",
        )
    return field_sheet


def create_field_sheet(
    db: Session, payload: FieldSheetCreate, *, user_id: int | None = None
) -> FieldSheet:
    equipment = _ensure_active_equipment(db, payload.equipment_id)
    _ensure_no_active_field_sheet(db, payload.equipment_id)
    service_order: ServiceOrder = equipment.service_order
    _ensure_calibration_procedure(db, payload.calibration_procedure_id)
    if payload.template_snapshot is not None:
        template_definition = deepcopy(payload.template_snapshot)
        snapshot_key = template_definition.get("template_key") or template_definition.get("key")
        if snapshot_key != payload.template_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La clave de la plantilla no coincide con su snapshot",
            )
        template_version = int(payload.template_version or template_definition.get("version") or 1)
        template_definition["template_key"] = payload.template_key
        template_definition["version"] = template_version
    else:
        template_definition, template_version = get_template_snapshot(db, payload.template_key)
    template_definition = canonicalize_new_field_sheet_snapshot(template_definition)
    institution = get_or_create_institutional_configuration(db)

    field_sheet = FieldSheet(
        **payload.model_dump(
            exclude={
                "results_rows",
                "reference_standards",
                "signatures",
                "template_key",
                "template_version",
                "template_snapshot",
                "work_order_id",
                "reception_date",
                "calibration_date",
                "purchase_order_or_quotation",
                "capture_values",
            }
        ),
        template_key=payload.template_key,
        template_definition_json=template_definition,
        template_definition_version=template_version,
        pdf_renderer_key=template_definition.get("pdf_renderer_key", CANONICAL_PDF_RENDERER_KEY),
        pdf_renderer_version=int(template_definition.get("pdf_renderer_version") or CANONICAL_PDF_RENDERER_VERSION),
        institutional_snapshot_json=institutional_snapshot(institution),
        status="draft",
        work_order_id=payload.work_order_id or equipment.work_order_id,
        work_order_number=(
            equipment.work_order.work_order_number
            if equipment.work_order is not None
            else service_order.work_order_number
        ),    


        reception_date=payload.reception_date or service_order.agenda_date or service_order.created_at.date(),
        calibration_date=payload.calibration_date or service_order.service_date,
        purchase_order_or_quotation=payload.purchase_order_or_quotation
        or (service_order.quotation.folio if service_order.quotation else None),
        capture_values={
            "instrument": equipment.name or "",
            "scope": equipment.range_or_capacity or "",
            "brand": equipment.brand or "",
            "model": equipment.model or "",
            "serial_number": equipment.serial_number or "",
            "internal_id": equipment.internal_id or "",
            **(payload.capture_values or {}),
        },
    )
    if payload.certificate_client_mode == "billing":
        client = service_order.client
        if field_sheet.company is None:
            field_sheet.company = client.commercial_name or client.legal_name
        if field_sheet.address is None:
            field_sheet.address = _client_address(client)
    else:
        if field_sheet.company is None:
            field_sheet.company = payload.certificate_client_company
        if field_sheet.address is None:
            field_sheet.address = payload.certificate_client_address
    if field_sheet.initial_condition is None:
        field_sheet.initial_condition = equipment.initial_condition
    field_sheet.results_rows = (
        [FieldSheetResult(**row.model_dump()) for row in payload.results_rows]
        if payload.results_rows
        else build_default_result_rows(template_definition)
    )
    field_sheet.signatures = (
        [FieldSheetSignature(**signature.model_dump()) for signature in payload.signatures]
        if payload.signatures
        else _default_signature_slots(template_definition, field_sheet)
    )
    resolved_standards = _resolve_reference_standards(db, payload.reference_standards)
    _apply_reference_standard_updates(field_sheet, payload.reference_standards, resolved_standards)
    db.add(field_sheet)
    db.flush()
    if equipment.status == "registered":
        equipment.status = "realizing"
    if field_sheet.calibration_procedure_id is not None:
        write_audit_log(
            db,
            action="field_sheet.procedure_assigned",
            entity="field_sheets",
            entity_id=field_sheet.id,
            user_id=user_id,
            new_values={"calibration_procedure_id": field_sheet.calibration_procedure_id},
        )
    for link in field_sheet.reference_standard_links:
        write_audit_log(
            db,
            action="field_sheet.reference_standard_added",
            entity="field_sheets",
            entity_id=field_sheet.id,
            user_id=user_id,
            new_values={
                "reference_standard_id": link.reference_standard_id,
                "usage_role": link.usage_role,
                "measurement_section": link.measurement_section,
            },
        )
    write_audit_log(
        db,
        action="field_sheet.created",
        entity="field_sheets",
        entity_id=field_sheet.id,
        user_id=user_id,
        new_values=_serialize_field_sheet(field_sheet),
    )
    db.commit()
    db.refresh(field_sheet)
    return get_field_sheet(db, field_sheet.id)


def update_field_sheet(
    db: Session,
    field_sheet_id: int,
    payload: FieldSheetUpdate,
    *,
    user_id: int | None = None,
) -> FieldSheet:
    field_sheet = get_field_sheet(db, field_sheet_id)
    equipment = _ensure_active_equipment(db, field_sheet.equipment_id)
    if field_sheet.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede editar una hoja de campo en este estado",
        )

    previous_values = _serialize_field_sheet(field_sheet)
    updates = payload.model_dump(
        exclude_unset=True,
        exclude={"results_rows", "reference_standards", "signatures"},
    )
    if "calibration_procedure_id" in updates:
        _ensure_calibration_procedure(db, updates["calibration_procedure_id"])
    template_changed = False
    new_template = updates.get("template_key")
    if new_template is not None and new_template != field_sheet.template_key:
        template_definition, template_version = get_template_snapshot(db, new_template)
        if field_sheet.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo una hoja en borrador puede cambiar de plantilla",
            )
        template_changed = True

    for key, value in updates.items():
        setattr(field_sheet, key, value)

    if template_changed and new_template is not None:
        template_definition = canonicalize_new_field_sheet_snapshot(template_definition)
        field_sheet.template_definition_json = template_definition
        field_sheet.template_definition_version = template_version
        field_sheet.pdf_renderer_key = template_definition.get("pdf_renderer_key", CANONICAL_PDF_RENDERER_KEY)
        field_sheet.pdf_renderer_version = int(template_definition.get("pdf_renderer_version") or CANONICAL_PDF_RENDERER_VERSION)
        field_sheet.results_rows = build_default_result_rows(template_definition)

    if payload.results_rows is not None:
        _apply_results_updates(field_sheet, payload.results_rows)
    if payload.signatures is not None:
        _apply_signature_updates(field_sheet, payload.signatures)
    if payload.reference_standards is not None:
        previous_links = _serialize_field_sheet(field_sheet)["reference_standards"]
        resolved_standards = _resolve_reference_standards(db, payload.reference_standards)
        _apply_reference_standard_updates(field_sheet, payload.reference_standards, resolved_standards)
        previous_ids = {item["reference_standard_id"] for item in previous_links}
        new_ids = {item.reference_standard_id for item in payload.reference_standards}
        for added_id in sorted(new_ids - previous_ids):
            write_audit_log(
                db,
                action="field_sheet.reference_standard_added",
                entity="field_sheets",
                entity_id=field_sheet.id,
                user_id=user_id,
                new_values={"reference_standard_id": added_id},
            )
        for removed_id in sorted(previous_ids - new_ids):
            write_audit_log(
                db,
                action="field_sheet.reference_standard_removed",
                entity="field_sheets",
                entity_id=field_sheet.id,
                user_id=user_id,
                previous_values={"reference_standard_id": removed_id},
            )
    if "calibration_procedure_id" in updates:
        write_audit_log(
            db,
            action="field_sheet.procedure_assigned",
            entity="field_sheets",
            entity_id=field_sheet.id,
            user_id=user_id,
            previous_values={"calibration_procedure_id": previous_values.get("calibration_procedure_id")},
            new_values={"calibration_procedure_id": field_sheet.calibration_procedure_id},
        )

    if field_sheet.work_order_id is None:
        field_sheet.work_order_id = equipment.work_order_id

    if field_sheet.work_order_number is None:
        field_sheet.work_order_number = (
            equipment.work_order.work_order_number
            if equipment.work_order is not None
            else equipment.service_order.work_order_number
        )

    if field_sheet.status == "draft" and (updates or payload.results_rows is not None):
        field_sheet.status = "in_progress"

    write_audit_log(
        db,
        action="field_sheet.updated",
        entity="field_sheets",
        entity_id=field_sheet.id,
        user_id=user_id,
        previous_values=_json_safe(previous_values),
        new_values=_json_safe(_serialize_field_sheet(field_sheet)),
    )
    db.commit()
    return get_field_sheet(db, field_sheet.id)


def complete_field_sheet(
    db: Session,
    field_sheet_id: int,
    payload: FieldSheetStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> FieldSheet:
    field_sheet = get_field_sheet(db, field_sheet_id)
    equipment = _ensure_active_equipment(db, field_sheet.equipment_id)

    if field_sheet.status not in {"draft", "in_progress", "rejected", "returned_to_technician"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La hoja de campo no puede completarse desde este estado",
        )

    _validate_ready_to_complete(field_sheet)

    previous_status = field_sheet.status
    previous_equipment_status = equipment.status

    field_sheet.status = "completed"
    equipment.status = "calibrated"

    # Completing is the documentary freeze boundary. The renderer writes the
    # immutable artifact through the shared storage abstraction and persists
    # its identity in this same transaction. guard_final_pdf_write spans the
    # write through this function's own commit so a failure anywhere in that
    # span (certificate updates, audit log, publish_event, sync, commit
    # itself) deletes the orphaned artifact and rolls back instead of leaving
    # a frozen PDF that no committed row points to.
    from app.services.field_sheet_pdfs import freeze_final_field_sheet_pdf, guard_final_pdf_write

    with guard_final_pdf_write(db, field_sheet):
        freeze_final_field_sheet_pdf(db, field_sheet)

        certificate = db.scalar(
            select(Certificate).where(
                Certificate.equipment_id == equipment.id,
                Certificate.is_active.is_(True),
            )
        )

        if certificate is not None and certificate.status in {
            "expected",
            "field_sheet_ready",
            "capture_pending",
            "capture_in_progress",
            "quality_rejected",
            "returned_to_technician",
        }:
            certificate.field_sheet_id = field_sheet.id
            certificate.status = "field_sheet_ready"

        sync_service_order_equipment_counts(db, equipment.service_order_id)

        write_audit_log(
            db,
            action="field_sheet.completed",
            entity="field_sheets",
            entity_id=field_sheet.id,
            user_id=user_id,
            previous_values={
                "status": previous_status,
                "equipment_status": previous_equipment_status,
            },
            new_values={
                "status": "completed",
                "equipment_status": "calibrated",
                "certificate_ready": True,
                "external_certificate_flow": True,
                "certificate_id": certificate.id if certificate else None,
                "certificate_status": certificate.status if certificate else None,
            },
            comment=payload.comment if payload else None,
        )
        publish_event(
            db,
            entity_type="field_sheet",
            entity_id=field_sheet.id,
            event_code="field_sheet.completed",
            idempotency_key=f"field_sheet:{field_sheet.id}:completed",
            body="Hoja de Campo completada y equipo marcado como calibrado.",
            actor_id=user_id,
            metadata={
                "previous_status": previous_status,
                "status": "completed",
                "equipment_status": "calibrated",
            },
            related_entity_type="equipment",
            related_entity_id=equipment.id,
        )

        db.commit()
    return get_field_sheet(db, field_sheet.id)


def review_field_sheet(
    db: Session,
    field_sheet_id: int,
    payload: FieldSheetStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> FieldSheet:
    field_sheet = get_field_sheet(db, field_sheet_id)
    _ensure_active_equipment(db, field_sheet.equipment_id)
    if field_sheet.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo una hoja completada puede pasar a revision",
        )
    field_sheet.status = "under_review"
    certificate = next((item for item in field_sheet.certificates if item.is_active), None)
    if certificate is None:
        certificate = db.scalar(
            select(Certificate).where(
                Certificate.equipment_id == field_sheet.equipment_id,
                Certificate.is_active.is_(True),
            )
        )
    if certificate is not None and certificate.status in {"expected", "field_sheet_ready", "returned_to_technician"}:
        certificate.field_sheet_id = field_sheet.id
        certificate.status = "capture_pending"
    write_audit_log(
        db,
        action="field_sheet.reviewed",
        entity="field_sheets",
        entity_id=field_sheet.id,
        user_id=user_id,
        previous_values={"status": "completed"},
        new_values={
            "status": "under_review",
            "certificate_id": certificate.id if certificate else None,
            "certificate_status": certificate.status if certificate else None,
        },
        comment=payload.comment if payload else None,
    )
    publish_event(
        db,
        entity_type="field_sheet",
        entity_id=field_sheet.id,
        event_code="field_sheet.reviewed",
        idempotency_key=f"field_sheet:{field_sheet.id}:reviewed",
        body="Hoja de Campo enviada a revisión.",
        actor_id=user_id,
        metadata={"previous_status": "completed", "status": "under_review"},
        related_entity_type="certificate" if certificate else None,
        related_entity_id=certificate.id if certificate else None,
    )
    db.commit()
    return get_field_sheet(db, field_sheet.id)


def deactivate_field_sheet(
    db: Session, field_sheet_id: int, *, user_id: int | None = None
) -> FieldSheet:
    field_sheet = get_field_sheet(db, field_sheet_id)
    if field_sheet.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede cancelar una hoja de campo en estado terminal",
        )
    field_sheet.is_active = False
    field_sheet.status = "cancelled"
    field_sheet.deleted_at = datetime.now(timezone.utc)
    field_sheet.deleted_by = user_id
    write_audit_log(
        db,
        action="field_sheet.deactivated",
        entity="field_sheets",
        entity_id=field_sheet.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False, "status": "cancelled"},
    )
    db.commit()
    return field_sheet
