from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.calibration_procedure import CalibrationProcedure
from app.schemas.calibration_procedure import CalibrationProcedureCreate, CalibrationProcedureUpdate
from app.services.audit_logs import write_audit_log


def _serialize_procedure(item: CalibrationProcedure) -> dict:
    return {
        "code": item.code,
        "name": item.name,
        "magnitude": item.magnitude,
        "profile_key": item.profile_key,
        "version": item.version,
        "issuer_company": item.issuer_company,
        "certificate_type": item.certificate_type,
        "status": item.status,
        "required_readings": item.required_readings,
    }


def _assert_unique_code_version(
    db: Session,
    code: str,
    version: str,
    procedure_id: int | None = None,
) -> None:
    existing = db.scalar(
        select(CalibrationProcedure.id).where(
            CalibrationProcedure.code == code,
            CalibrationProcedure.version == version,
            CalibrationProcedure.is_active.is_(True),
            CalibrationProcedure.id != (procedure_id or 0),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un procedimiento activo con el mismo codigo y version.",
        )


def list_calibration_procedures(
    db: Session,
    *,
    include_inactive: bool = False,
    magnitude: str | None = None,
    profile_key: str | None = None,
    status_value: str | None = None,
    search: str | None = None,
) -> list[CalibrationProcedure]:
    query = select(CalibrationProcedure).order_by(
        CalibrationProcedure.updated_at.desc(), CalibrationProcedure.id.desc()
    )
    if not include_inactive:
        query = query.where(CalibrationProcedure.is_active.is_(True))
    if magnitude:
        query = query.where(CalibrationProcedure.magnitude == magnitude)
    if profile_key:
        query = query.where(CalibrationProcedure.profile_key == profile_key)
    if status_value:
        query = query.where(CalibrationProcedure.status == status_value)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                CalibrationProcedure.code.ilike(pattern),
                CalibrationProcedure.name.ilike(pattern),
                CalibrationProcedure.description.ilike(pattern),
                CalibrationProcedure.magnitude.ilike(pattern),
            )
        )
    return list(db.scalars(query).all())


def get_calibration_procedure(db: Session, procedure_id: int) -> CalibrationProcedure:
    procedure = db.scalar(select(CalibrationProcedure).where(CalibrationProcedure.id == procedure_id))
    if procedure is None or not procedure.is_active:
        raise HTTPException(status_code=404, detail="Procedimiento no encontrado")
    return procedure


def create_calibration_procedure(
    db: Session,
    payload: CalibrationProcedureCreate,
    *,
    user_id: int | None = None,
) -> CalibrationProcedure:
    _assert_unique_code_version(db, payload.code, payload.version)
    procedure = CalibrationProcedure(**payload.model_dump())
    db.add(procedure)
    db.flush()
    write_audit_log(
        db,
        action="calibration_procedure.created",
        entity="calibration_procedures",
        entity_id=procedure.id,
        user_id=user_id,
        new_values=_serialize_procedure(procedure),
    )
    db.commit()
    return get_calibration_procedure(db, procedure.id)


def update_calibration_procedure(
    db: Session,
    procedure_id: int,
    payload: CalibrationProcedureUpdate,
    *,
    user_id: int | None = None,
) -> CalibrationProcedure:
    procedure = get_calibration_procedure(db, procedure_id)
    previous = _serialize_procedure(procedure)
    updates = payload.model_dump(exclude_unset=True)
    code = updates.get("code", procedure.code)
    version = updates.get("version", procedure.version)
    _assert_unique_code_version(db, code, version, procedure_id)
    for key, value in updates.items():
        setattr(procedure, key, value)
    write_audit_log(
        db,
        action="calibration_procedure.updated",
        entity="calibration_procedures",
        entity_id=procedure.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_procedure(procedure),
    )
    db.commit()
    return get_calibration_procedure(db, procedure.id)


def deactivate_calibration_procedure(
    db: Session,
    procedure_id: int,
    *,
    user_id: int | None = None,
) -> CalibrationProcedure:
    procedure = get_calibration_procedure(db, procedure_id)
    previous = _serialize_procedure(procedure)
    procedure.is_active = False
    procedure.status = "inactive"
    procedure.deleted_at = datetime.now(timezone.utc)
    procedure.deleted_by = user_id
    write_audit_log(
        db,
        action="calibration_procedure.deactivated",
        entity="calibration_procedures",
        entity_id=procedure.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_procedure(procedure),
    )
    db.commit()
    return procedure
