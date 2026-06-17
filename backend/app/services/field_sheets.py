from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet
from app.schemas.field_sheet import (
    FieldSheetCreate,
    FieldSheetStatusChange,
    FieldSheetUpdate,
)
from app.services.audit_logs import write_audit_log
from app.services.equipment import sync_service_order_equipment_counts


TERMINAL_STATUSES = {"approved", "cancelled"}
EDITABLE_STATUSES = {"draft", "in_progress", "rejected"}


def _ensure_active_equipment(db: Session, equipment_id: int) -> Equipment:
    equipment = db.scalar(
        select(Equipment).where(
            Equipment.id == equipment_id,
            Equipment.is_active.is_(True),
        )
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


def _validate_ready_to_complete(field_sheet: FieldSheet) -> None:
    missing_fields = []
    required_fields = {
        "initial_condition": field_sheet.initial_condition,
        "final_condition": field_sheet.final_condition,
        "pattern_used": field_sheet.pattern_used,
        "results": field_sheet.results,
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


def list_field_sheets(
    db: Session,
    *,
    equipment_id: int | None = None,
    include_inactive: bool = False,
) -> list[FieldSheet]:
    query = select(FieldSheet).order_by(FieldSheet.created_at.desc())
    if equipment_id is not None:
        query = query.where(FieldSheet.equipment_id == equipment_id)
    if not include_inactive:
        query = query.where(FieldSheet.is_active.is_(True))
    return list(db.scalars(query).all())


def get_field_sheet(db: Session, field_sheet_id: int) -> FieldSheet:
    field_sheet = db.scalar(select(FieldSheet).where(FieldSheet.id == field_sheet_id))
    if field_sheet is None or not field_sheet.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hoja de campo no encontrada",
        )
    return field_sheet


def create_field_sheet(
    db: Session, payload: FieldSheetCreate, *, user_id: int | None = None
) -> FieldSheet:
    _ensure_active_equipment(db, payload.equipment_id)
    _ensure_no_active_field_sheet(db, payload.equipment_id)
    field_sheet = FieldSheet(**payload.model_dump(), status="draft")
    db.add(field_sheet)
    db.flush()
    write_audit_log(
        db,
        action="field_sheet.created",
        entity="field_sheets",
        entity_id=field_sheet.id,
        user_id=user_id,
        new_values={
            "equipment_id": field_sheet.equipment_id,
            "status": field_sheet.status,
        },
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
    _ensure_active_equipment(db, field_sheet.equipment_id)
    if field_sheet.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede editar una hoja de campo en este estado",
        )
    updates = payload.model_dump(exclude_unset=True)
    previous_values = {key: getattr(field_sheet, key) for key in updates}
    for key, value in updates.items():
        setattr(field_sheet, key, value)
    if field_sheet.status == "draft" and updates:
        previous_values["status"] = "draft"
        field_sheet.status = "in_progress"
        updates["status"] = "in_progress"
    write_audit_log(
        db,
        action="field_sheet.updated",
        entity="field_sheets",
        entity_id=field_sheet.id,
        user_id=user_id,
        previous_values=previous_values,
        new_values=updates,
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
        action="field_sheet.under_review",
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
