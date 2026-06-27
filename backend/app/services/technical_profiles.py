from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.controlled_document import (
    ControlledDocument,
    DocumentInterpretation,
    TechnicalProfile,
    TechnicalProfileAllowedPattern,
)
from app.schemas.controlled_document import TechnicalProfileCreate, TechnicalProfileUpdate
from app.services.audit_logs import write_audit_log


DOCUMENT_LINK_FIELDS = [
    "procedure_document_id",
    "field_sheet_template_document_id",
    "certificate_template_document_id",
    "uncertainty_source_document_id",
]


def _profile_query():
    return select(TechnicalProfile).options(selectinload(TechnicalProfile.allowed_patterns))


def _ensure_links(db: Session, payload: dict) -> None:
    for field in DOCUMENT_LINK_FIELDS:
        document_id = payload.get(field)
        if document_id is not None and db.get(ControlledDocument, document_id) is None:
            raise HTTPException(status_code=422, detail=f"Documento no encontrado: {field}")
    interpretation_id = payload.get("procedure_interpretation_id")
    if interpretation_id is not None:
        interpretation = db.get(DocumentInterpretation, interpretation_id)
        if interpretation is None:
            raise HTTPException(status_code=422, detail="Interpretacion de procedimiento no encontrada")
        if interpretation.status != "approved":
            raise HTTPException(status_code=422, detail="Solo se puede usar interpretacion aprobada")


def _apply_patterns(profile: TechnicalProfile, items: list) -> None:
    profile.allowed_patterns = [
        TechnicalProfileAllowedPattern(**item.model_dump())
        for item in items
    ]


def list_technical_profiles(
    db: Session,
    *,
    magnitude: str | None = None,
    equipment_type: str | None = None,
    service_type: str | None = None,
    calibration_scope: str | None = None,
    status: str | None = None,
) -> list[TechnicalProfile]:
    query = _profile_query().order_by(TechnicalProfile.created_at.desc())
    if magnitude:
        query = query.where(TechnicalProfile.magnitude == magnitude)
    if equipment_type:
        query = query.where(TechnicalProfile.equipment_type == equipment_type)
    if service_type:
        query = query.where(TechnicalProfile.service_type == service_type)
    if calibration_scope:
        query = query.where(TechnicalProfile.calibration_scope == calibration_scope)
    if status:
        query = query.where(TechnicalProfile.status == status)
    return list(db.scalars(query).all())


def get_technical_profile(db: Session, profile_id: int) -> TechnicalProfile:
    profile = db.scalar(_profile_query().where(TechnicalProfile.id == profile_id))
    if profile is None:
        raise HTTPException(status_code=404, detail="Perfil tecnico no encontrado")
    return profile


def create_technical_profile(
    db: Session,
    payload: TechnicalProfileCreate,
    *,
    user_id: int | None = None,
) -> TechnicalProfile:
    data = payload.model_dump(exclude={"allowed_patterns"})
    _ensure_links(db, data)
    profile = TechnicalProfile(**data, created_by_id=user_id)
    _apply_patterns(profile, payload.allowed_patterns)
    db.add(profile)
    db.flush()
    write_audit_log(
        db,
        action="technical_profile.created",
        entity="technical_profiles",
        entity_id=profile.id,
        user_id=user_id,
        new_values=payload.model_dump(mode="json"),
    )
    db.commit()
    return get_technical_profile(db, profile.id)


def update_technical_profile(
    db: Session,
    profile_id: int,
    payload: TechnicalProfileUpdate,
    *,
    user_id: int | None = None,
) -> TechnicalProfile:
    profile = get_technical_profile(db, profile_id)
    if profile.status in {"active", "obsolete"}:
        raise HTTPException(
            status_code=409,
            detail="Crea una nueva version para modificar un perfil activo u obsoleto",
        )
    updates = payload.model_dump(exclude_unset=True, exclude={"allowed_patterns"})
    _ensure_links(db, updates)
    previous = {key: getattr(profile, key) for key in updates}
    for key, value in updates.items():
        setattr(profile, key, value)
    if payload.allowed_patterns is not None:
        _apply_patterns(profile, payload.allowed_patterns)
    write_audit_log(
        db,
        action="technical_profile.updated",
        entity="technical_profiles",
        entity_id=profile.id,
        user_id=user_id,
        previous_values=previous,
        new_values=payload.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    return get_technical_profile(db, profile.id)


def approve_technical_profile(
    db: Session,
    profile_id: int,
    *,
    user_id: int | None = None,
) -> TechnicalProfile:
    profile = get_technical_profile(db, profile_id)
    previous_status = profile.status
    profile.status = "active"
    profile.approved_by_id = user_id
    profile.approved_at = datetime.now(timezone.utc)
    write_audit_log(
        db,
        action="technical_profile.approved",
        entity="technical_profiles",
        entity_id=profile.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": "active"},
    )
    db.commit()
    return get_technical_profile(db, profile.id)


def create_technical_profile_new_version(
    db: Session,
    profile_id: int,
    *,
    user_id: int | None = None,
) -> TechnicalProfile:
    source = get_technical_profile(db, profile_id)
    source.status = "obsolete"
    clone = TechnicalProfile(
        code=f"{source.code}-V{source.version + 1}",
        name=source.name,
        magnitude=source.magnitude,
        equipment_type=source.equipment_type,
        service_type=source.service_type,
        calibration_scope=source.calibration_scope,
        procedure_document_id=source.procedure_document_id,
        procedure_interpretation_id=source.procedure_interpretation_id,
        field_sheet_template_document_id=source.field_sheet_template_document_id,
        certificate_template_document_id=source.certificate_template_document_id,
        uncertainty_source_document_id=source.uncertainty_source_document_id,
        status="draft",
        version=source.version + 1,
        rules=source.rules,
        notes=source.notes,
        created_by_id=user_id,
    )
    clone.allowed_patterns = [
        TechnicalProfileAllowedPattern(
            pattern_id=item.pattern_id,
            pattern_code=item.pattern_code,
            min_range=item.min_range,
            max_range=item.max_range,
            unit=item.unit,
            priority=item.priority,
            is_preferred=item.is_preferred,
            notes=item.notes,
        )
        for item in source.allowed_patterns
    ]
    db.add(clone)
    db.flush()
    write_audit_log(
        db,
        action="technical_profile.new_version",
        entity="technical_profiles",
        entity_id=clone.id,
        user_id=user_id,
        previous_values={"source_id": source.id, "source_version": source.version},
        new_values={"version": clone.version, "status": clone.status},
    )
    db.commit()
    return get_technical_profile(db, clone.id)


def resolve_technical_profiles(
    db: Session,
    *,
    magnitude: str,
    equipment_type: str,
    service_type: str,
    calibration_scope: str,
    range_min: float | None = None,
    range_max: float | None = None,
    unit: str | None = None,
) -> list[TechnicalProfile]:
    query = _profile_query().where(
        TechnicalProfile.magnitude == magnitude,
        TechnicalProfile.equipment_type == equipment_type,
        TechnicalProfile.service_type == service_type,
        TechnicalProfile.calibration_scope == calibration_scope,
        TechnicalProfile.status == "active",
    )
    return list(db.scalars(query).all())
