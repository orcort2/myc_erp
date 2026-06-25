from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.reference_standard import ReferenceStandard, ReferenceStandardUncertainty
from app.schemas.reference_standard import (
    ReferenceStandardCreate,
    ReferenceStandardUncertaintyCreate,
    ReferenceStandardUncertaintyUpdate,
    ReferenceStandardUpdate,
)
from app.services.audit_logs import write_audit_log


def _with_relations():
    return (
        selectinload(ReferenceStandard.uncertainties),
        selectinload(ReferenceStandard.field_sheet_links),
    )


def _serialize_uncertainty(item: ReferenceStandardUncertainty) -> dict:
    return {
        "id": item.id,
        "range_min": float(item.range_min) if item.range_min is not None else None,
        "range_max": float(item.range_max) if item.range_max is not None else None,
        "unit": item.unit,
        "uncertainty_value": float(item.uncertainty_value),
        "coverage_factor_k": float(item.coverage_factor_k) if item.coverage_factor_k is not None else None,
        "distribution": item.distribution,
        "notes": item.notes,
        "is_active": item.is_active,
    }


def _serialize_standard(item: ReferenceStandard) -> dict:
    return {
        "internal_code": item.internal_code,
        "name": item.name,
        "owner_company": item.owner_company,
        "magnitude": item.magnitude,
        "status": item.status,
        "effective_status": item.effective_status,
        "next_calibration_on": item.next_calibration_on.isoformat() if item.next_calibration_on else None,
        "uncertainties": [_serialize_uncertainty(row) for row in item.uncertainties if row.is_active],
    }


def _assert_unique_internal_code(db: Session, internal_code: str, standard_id: int | None = None) -> None:
    existing = db.scalar(
        select(ReferenceStandard.id).where(
            ReferenceStandard.internal_code == internal_code,
            ReferenceStandard.is_active.is_(True),
            ReferenceStandard.id != (standard_id or 0),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un patron activo con esa clave interna.",
        )


def list_reference_standards(
    db: Session,
    *,
    include_inactive: bool = False,
    owner_company: str | None = None,
    magnitude: str | None = None,
    status_value: str | None = None,
    search: str | None = None,
) -> list[ReferenceStandard]:
    query = select(ReferenceStandard).options(*_with_relations()).order_by(
        ReferenceStandard.updated_at.desc(), ReferenceStandard.id.desc()
    )
    if not include_inactive:
        query = query.where(ReferenceStandard.is_active.is_(True))
    if owner_company:
        query = query.where(ReferenceStandard.owner_company == owner_company)
    if magnitude:
        query = query.where(ReferenceStandard.magnitude == magnitude)
    if status_value:
        query = query.where(ReferenceStandard.status == status_value)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                ReferenceStandard.internal_code.ilike(pattern),
                ReferenceStandard.name.ilike(pattern),
                ReferenceStandard.description.ilike(pattern),
                ReferenceStandard.magnitude.ilike(pattern),
                ReferenceStandard.serial_number.ilike(pattern),
            )
        )
    return list(db.scalars(query).all())


def get_reference_standard(db: Session, standard_id: int) -> ReferenceStandard:
    standard = db.scalar(
        select(ReferenceStandard)
        .where(ReferenceStandard.id == standard_id)
        .options(*_with_relations())
    )
    if standard is None or not standard.is_active:
        raise HTTPException(status_code=404, detail="Patron no encontrado")
    return standard


def create_reference_standard(
    db: Session,
    payload: ReferenceStandardCreate,
    *,
    user_id: int | None = None,
) -> ReferenceStandard:
    _assert_unique_internal_code(db, payload.internal_code)
    standard = ReferenceStandard(**payload.model_dump(exclude={"uncertainties"}))
    standard.uncertainties = [
        ReferenceStandardUncertainty(**item.model_dump()) for item in payload.uncertainties
    ]
    db.add(standard)
    db.flush()
    write_audit_log(
        db,
        action="reference_standard.created",
        entity="reference_standards",
        entity_id=standard.id,
        user_id=user_id,
        new_values=_serialize_standard(standard),
    )
    db.commit()
    return get_reference_standard(db, standard.id)


def update_reference_standard(
    db: Session,
    standard_id: int,
    payload: ReferenceStandardUpdate,
    *,
    user_id: int | None = None,
) -> ReferenceStandard:
    standard = get_reference_standard(db, standard_id)
    previous = _serialize_standard(standard)
    updates = payload.model_dump(exclude_unset=True)
    if "internal_code" in updates:
        _assert_unique_internal_code(db, updates["internal_code"], standard_id)
    for key, value in updates.items():
        setattr(standard, key, value)
    write_audit_log(
        db,
        action="reference_standard.updated",
        entity="reference_standards",
        entity_id=standard.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_standard(standard),
    )
    db.commit()
    return get_reference_standard(db, standard.id)


def deactivate_reference_standard(
    db: Session, standard_id: int, *, user_id: int | None = None
) -> ReferenceStandard:
    standard = get_reference_standard(db, standard_id)
    previous = _serialize_standard(standard)
    standard.is_active = False
    standard.status = "inactive"
    standard.deleted_at = datetime.now(timezone.utc)
    standard.deleted_by = user_id
    write_audit_log(
        db,
        action="reference_standard.deactivated",
        entity="reference_standards",
        entity_id=standard.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_standard(standard),
    )
    db.commit()
    return standard


def create_reference_standard_uncertainty(
    db: Session,
    standard_id: int,
    payload: ReferenceStandardUncertaintyCreate,
    *,
    user_id: int | None = None,
) -> ReferenceStandard:
    standard = get_reference_standard(db, standard_id)
    row = ReferenceStandardUncertainty(reference_standard_id=standard.id, **payload.model_dump())
    db.add(row)
    db.flush()
    db.refresh(standard)
    write_audit_log(
        db,
        action="reference_standard.uncertainty.created",
        entity="reference_standard_uncertainties",
        entity_id=row.id,
        user_id=user_id,
        new_values=_serialize_uncertainty(row),
    )
    db.commit()
    return get_reference_standard(db, standard.id)


def update_reference_standard_uncertainty(
    db: Session,
    standard_id: int,
    uncertainty_id: int,
    payload: ReferenceStandardUncertaintyUpdate,
    *,
    user_id: int | None = None,
) -> ReferenceStandard:
    standard = get_reference_standard(db, standard_id)
    row = next((item for item in standard.uncertainties if item.id == uncertainty_id and item.is_active), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Incertidumbre no encontrada")
    previous = _serialize_uncertainty(row)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    write_audit_log(
        db,
        action="reference_standard.uncertainty.updated",
        entity="reference_standard_uncertainties",
        entity_id=row.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_uncertainty(row),
    )
    db.commit()
    return get_reference_standard(db, standard.id)


def deactivate_reference_standard_uncertainty(
    db: Session,
    standard_id: int,
    uncertainty_id: int,
    *,
    user_id: int | None = None,
) -> ReferenceStandard:
    standard = get_reference_standard(db, standard_id)
    row = next((item for item in standard.uncertainties if item.id == uncertainty_id and item.is_active), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Incertidumbre no encontrada")
    previous = _serialize_uncertainty(row)
    row.is_active = False
    write_audit_log(
        db,
        action="reference_standard.uncertainty.deactivated",
        entity="reference_standard_uncertainties",
        entity_id=row.id,
        user_id=user_id,
        previous_values=previous,
        new_values=_serialize_uncertainty(row),
    )
    db.commit()
    return get_reference_standard(db, standard.id)
