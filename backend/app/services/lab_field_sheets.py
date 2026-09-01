from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.field_sheet import FieldSheet, FieldSheetResult
from app.models.lab_work_order import LabWorkOrderEquipment
from app.models.user import User
from app.schemas.field_sheet import FieldSheetRead, FieldSheetUpdate
from app.schemas.lab_work_order import LabFieldSheetCreate
from app.services.audit_logs import write_audit_log
from app.services.field_sheet_templates import build_default_result_rows, get_template_snapshot
from app.services.field_sheets import (
    EDITABLE_STATUSES,
    _apply_results_updates,
    _default_signature_slots,
    _serialize_field_sheet,
    _validate_ready_to_complete,
)
from app.services.institutional_configurations import (
    get_or_create_institutional_configuration,
    institutional_snapshot,
)


def get_lab_equipment(
    db: Session, work_order_id: int, equipment_id: int, *, lock: bool = False
) -> LabWorkOrderEquipment:
    query = (
        select(LabWorkOrderEquipment)
        .where(
            LabWorkOrderEquipment.id == equipment_id,
            LabWorkOrderEquipment.work_order_id == work_order_id,
        )
        .options(
            selectinload(LabWorkOrderEquipment.work_order),
            selectinload(LabWorkOrderEquipment.field_sheet).selectinload(FieldSheet.results_rows),
            selectinload(LabWorkOrderEquipment.field_sheet).selectinload(FieldSheet.signatures),
        )
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    equipment = db.scalar(query)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipo LAB no encontrado")
    return equipment


def _ensure_capture_allowed(equipment: LabWorkOrderEquipment, *, external: bool) -> None:
    if equipment.work_order.status != "draft":
        raise HTTPException(status_code=409, detail="La OT no admite captura técnica")
    if equipment.service_type is None:
        raise HTTPException(status_code=409, detail="Selecciona el tipo de servicio")
    if equipment.service_type in {"accredited", "traceable"} and equipment.folio_status not in {
        "reserved", "authorized"
    }:
        raise HTTPException(status_code=409, detail="El equipo requiere folio MYCA/MYCT asignado")
    if equipment.service_type == "linked" and not external and equipment.folio_status != "authorized":
        raise HTTPException(status_code=409, detail="Vinculado requiere folio autorizado antes de capturar")


def create_lab_field_sheet(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: LabFieldSheetCreate,
    user: User,
    *,
    external: bool,
) -> FieldSheetRead:
    equipment = get_lab_equipment(db, work_order_id, equipment_id, lock=True)
    _ensure_capture_allowed(equipment, external=external)
    if equipment.field_sheet is not None:
        raise HTTPException(status_code=409, detail="El equipo ya tiene una hoja de campo")
    definition, version = get_template_snapshot(db, payload.template_key)
    order = equipment.work_order
    institution = get_or_create_institutional_configuration(db)
    capture_values = {
        "instrument": equipment.instrument,
        "brand": equipment.brand,
        "serial_number": equipment.serial_number,
        "internal_id": equipment.identification,
    }
    sheet = FieldSheet(
        equipment_id=None,
        lab_equipment_id=equipment.id,
        work_order_id=None,
        work_order_number=order.folio,
        template_key=payload.template_key,
        template_definition_json=definition,
        template_definition_version=version,
        institutional_snapshot_json=institutional_snapshot(institution),
        status="draft",
        company=order.client_name,
        address=order.address,
        attention=order.contact_name,
        reception_date=order.reception_date,
        equipment_general_condition=equipment.is_good_condition,
        purchase_order_or_quotation=order.purchase_order,
        initial_condition="BUENA" if equipment.is_good_condition else "REQUIERE REVISIÓN",
        capture_values=capture_values,
    )
    sheet.results_rows = build_default_result_rows(definition)
    sheet.signatures = _default_signature_slots(definition, sheet)
    db.add(sheet)
    db.flush()
    write_audit_log(
        db,
        action="lab_field_sheet.created",
        entity="field_sheets",
        entity_id=sheet.id,
        user_id=user.id,
        new_values={
            "work_order_id": order.id,
            "lab_equipment_id": equipment.id,
            "template_key": payload.template_key,
            "template_version": version,
        },
    )
    db.commit()
    return read_lab_field_sheet(db, work_order_id, equipment_id)


def read_lab_field_sheet(db: Session, work_order_id: int, equipment_id: int) -> FieldSheetRead:
    equipment = get_lab_equipment(db, work_order_id, equipment_id)
    if equipment.field_sheet is None or not equipment.field_sheet.is_active:
        raise HTTPException(status_code=404, detail="Hoja de campo LAB no encontrada")
    return FieldSheetRead.model_validate(equipment.field_sheet)


def update_lab_field_sheet(
    db: Session,
    work_order_id: int,
    equipment_id: int,
    payload: FieldSheetUpdate,
    user: User,
) -> FieldSheetRead:
    equipment = get_lab_equipment(db, work_order_id, equipment_id, lock=True)
    sheet = equipment.field_sheet
    if sheet is None or not sheet.is_active:
        raise HTTPException(status_code=404, detail="Hoja de campo LAB no encontrada")
    if sheet.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="La hoja no admite edición")
    previous = _serialize_field_sheet(sheet)
    updates = payload.model_dump(
        exclude_unset=True,
        exclude={"results_rows", "reference_standards", "signatures", "work_order_id", "template_key"},
    )
    for key, value in updates.items():
        setattr(sheet, key, value)
    if payload.results_rows is not None:
        before_count = len(sheet.results_rows)
        _apply_results_updates(sheet, payload.results_rows)
        if len(sheet.results_rows) > before_count:
            write_audit_log(
                db,
                action="lab_field_sheet.instance_row_added",
                entity="field_sheets",
                entity_id=sheet.id,
                user_id=user.id,
                new_values={"previous_rows": before_count, "rows": len(sheet.results_rows)},
            )
    if sheet.status == "draft":
        sheet.status = "in_progress"
    write_audit_log(
        db,
        action="lab_field_sheet.updated",
        entity="field_sheets",
        entity_id=sheet.id,
        user_id=user.id,
        previous_values=previous,
        new_values=_serialize_field_sheet(sheet),
    )
    db.commit()
    return read_lab_field_sheet(db, work_order_id, equipment_id)


def complete_lab_field_sheet(
    db: Session, work_order_id: int, equipment_id: int, user: User
) -> FieldSheetRead:
    equipment = get_lab_equipment(db, work_order_id, equipment_id, lock=True)
    sheet = equipment.field_sheet
    if sheet is None or not sheet.is_active:
        raise HTTPException(status_code=404, detail="Hoja de campo LAB no encontrada")
    if sheet.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="La hoja no puede completarse desde este estado")
    _validate_ready_to_complete(sheet)
    previous = sheet.status
    sheet.status = "completed"
    write_audit_log(
        db,
        action="lab_field_sheet.completed",
        entity="field_sheets",
        entity_id=sheet.id,
        user_id=user.id,
        previous_values={"status": previous},
        new_values={"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()},
    )
    db.commit()
    return read_lab_field_sheet(db, work_order_id, equipment_id)
