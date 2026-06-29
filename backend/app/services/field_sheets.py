from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.models.reference_standard import FieldSheetReferenceStandard, ReferenceStandard
from app.models.reference_standard_certificate import ReferenceStandardCertificate
from app.models.service_order import ServiceOrder
from app.models.calibration_procedure import CalibrationProcedure
from app.schemas.field_sheet import (
    FieldSheetCreate,
    FieldSheetResultUpdate,
    FieldSheetStatusChange,
    FieldSheetTemplateKey,
    FieldSheetUpdate,
)
from app.services.audit_logs import write_audit_log
from app.services.equipment import sync_service_order_equipment_counts


TERMINAL_STATUSES = {"approved", "cancelled"}
EDITABLE_STATUSES = {"draft", "in_progress", "rejected"}
FIELD_SHEET_TEMPLATE_ROWS: dict[str, list[tuple[str, int]]] = {
    "general": [("main", 10)],
    "electrica": [
        ("main", 5),
        ("page2_a", 5),
        ("page2_b", 5),
        ("page2_c", 5),
        ("page2_d", 5),
        ("page2_e", 5),
    ],
}

FIELD_SHEET_REFERENCE_USAGE_ROLES = {
    "primary",
    "secondary",
    "auxiliary",
    "environmental",
    "other",
}


def _default_result_rows(template_key: FieldSheetTemplateKey) -> list[FieldSheetResult]:
    rows: list[FieldSheetResult] = []
    for section_key, total_rows in FIELD_SHEET_TEMPLATE_ROWS[template_key]:
        for row_number in range(1, total_rows + 1):
            rows.append(FieldSheetResult(section_key=section_key, row_number=row_number))
    return rows


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
        }
        for row in rows
    ]


def _serialize_field_sheet(field_sheet: FieldSheet) -> dict:
    return {
        "equipment_id": field_sheet.equipment_id,
        "calibration_procedure_id": field_sheet.calibration_procedure_id,
        "template_key": field_sheet.template_key,
        "work_order_number": field_sheet.work_order_number,
        "status": field_sheet.status,
        "calibration_place": field_sheet.calibration_place,
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
        "results_rows": _serialize_result_rows(field_sheet.results_rows),
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
        .options(selectinload(Equipment.service_order))
    )
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipo no encontrado",
        )
    if equipment.status in {"labeled", "not_done", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede modificar hoja de campo de un equipo terminal",
        )
    return equipment


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
        any(
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


def _validate_ready_to_complete(field_sheet: FieldSheet) -> None:
    missing_fields = []
    required_fields = {
        "initial_condition": field_sheet.initial_condition,
        "final_condition": field_sheet.final_condition,
    }
    for field_name, value in required_fields.items():
        if not value or not value.strip():
            missing_fields.append(field_name)

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
    new_rows: list[FieldSheetResult] = []
    for row_payload in results_rows:
        row_data = row_payload.model_dump(exclude={"id"})
        if row_payload.id is not None and row_payload.id in existing_by_id:
            row = existing_by_id[row_payload.id]
            for key, value in row_data.items():
                setattr(row, key, value)
            new_rows.append(row)
        else:
            new_rows.append(FieldSheetResult(**row_data))
    field_sheet.results_rows = new_rows


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
    include_inactive: bool = False,
) -> list[FieldSheet]:
    query = (
        select(FieldSheet)
        .options(
            selectinload(FieldSheet.results_rows),
            selectinload(FieldSheet.calibration_procedure),
            selectinload(FieldSheet.reference_standard_links).selectinload(
                FieldSheetReferenceStandard.reference_standard
            ).selectinload(ReferenceStandard.uncertainties),
        )
        .order_by(FieldSheet.created_at.desc())
    )
    if equipment_id is not None:
        query = query.where(FieldSheet.equipment_id == equipment_id)
    if not include_inactive:
        query = query.where(FieldSheet.is_active.is_(True))
    return list(db.scalars(query).all())


def get_field_sheet(db: Session, field_sheet_id: int) -> FieldSheet:
    field_sheet = db.scalar(
        select(FieldSheet)
        .where(FieldSheet.id == field_sheet_id)
        .options(
            selectinload(FieldSheet.results_rows),
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

    field_sheet = FieldSheet(
        **payload.model_dump(
            exclude={
                "results_rows",
                "reference_standards",
                "template_key",
                "reception_date",
                "calibration_date",
                "purchase_order_or_quotation",
            }
        ),
        template_key=payload.template_key,
        status="draft",
        work_order_number=service_order.work_order_number,
        reception_date=payload.reception_date or service_order.agenda_date or service_order.created_at.date(),
        calibration_date=payload.calibration_date or service_order.service_date,
        purchase_order_or_quotation=payload.purchase_order_or_quotation
        or (service_order.quotation.folio if service_order.quotation else None),
    )
    field_sheet.results_rows = (
        [FieldSheetResult(**row.model_dump()) for row in payload.results_rows]
        if payload.results_rows
        else _default_result_rows(payload.template_key)
    )
    resolved_standards = _resolve_reference_standards(db, payload.reference_standards)
    _apply_reference_standard_updates(field_sheet, payload.reference_standards, resolved_standards)
    db.add(field_sheet)
    db.flush()
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
    updates = payload.model_dump(exclude_unset=True, exclude={"results_rows", "reference_standards"})
    if "calibration_procedure_id" in updates:
        _ensure_calibration_procedure(db, updates["calibration_procedure_id"])
    template_changed = False
    new_template = updates.get("template_key")
    if new_template is not None and new_template != field_sheet.template_key:
        if field_sheet.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Solo una hoja en borrador puede cambiar de plantilla",
            )
        template_changed = True

    for key, value in updates.items():
        setattr(field_sheet, key, value)

    if template_changed and new_template is not None:
        field_sheet.results_rows = _default_result_rows(new_template)

    if payload.results_rows is not None:
        _apply_results_updates(field_sheet, payload.results_rows)
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

    if field_sheet.work_order_number is None:
        field_sheet.work_order_number = equipment.service_order.work_order_number

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
    if field_sheet.status not in {"draft", "in_progress", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La hoja de campo no puede completarse desde este estado",
        )
    _validate_ready_to_complete(field_sheet)
    previous_status = field_sheet.status
    previous_equipment_status = equipment.status
    field_sheet.status = "completed"
    equipment.status = "calibrated"
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
        },
        comment=payload.comment if payload else None,
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
    write_audit_log(
        db,
        action="field_sheet.reviewed",
        entity="field_sheets",
        entity_id=field_sheet.id,
        user_id=user_id,
        previous_values={"status": "completed"},
        new_values={"status": "under_review"},
        comment=payload.comment if payload else None,
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
