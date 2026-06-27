from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.controlled_document import (
    ControlledDocument,
    ControlledDocumentVersion,
    DocumentInterpretation,
)
from app.schemas.controlled_document import DocumentInterpretationCreate, DocumentInterpretationUpdate
from app.services.audit_logs import write_audit_log


def _ensure_document_links(
    db: Session,
    *,
    document_id: int,
    document_version_id: int | None,
) -> None:
    if db.get(ControlledDocument, document_id) is None:
        raise HTTPException(status_code=404, detail="Documento controlado no encontrado")
    if document_version_id is not None:
        version = db.get(ControlledDocumentVersion, document_version_id)
        if version is None or version.document_id != document_id:
            raise HTTPException(status_code=422, detail="La version no pertenece al documento")


def list_interpretations(
    db: Session,
    *,
    document_id: int | None = None,
    magnitude: str | None = None,
    equipment_type: str | None = None,
    interpretation_type: str | None = None,
    status: str | None = None,
) -> list[DocumentInterpretation]:
    query = select(DocumentInterpretation).order_by(DocumentInterpretation.created_at.desc())
    if document_id is not None:
        query = query.where(DocumentInterpretation.document_id == document_id)
    if magnitude:
        query = query.where(DocumentInterpretation.magnitude == magnitude)
    if equipment_type:
        query = query.where(DocumentInterpretation.equipment_type == equipment_type)
    if interpretation_type:
        query = query.where(DocumentInterpretation.interpretation_type == interpretation_type)
    if status:
        query = query.where(DocumentInterpretation.status == status)
    return list(db.scalars(query).all())


def get_interpretation(db: Session, interpretation_id: int) -> DocumentInterpretation:
    interpretation = db.get(DocumentInterpretation, interpretation_id)
    if interpretation is None:
        raise HTTPException(status_code=404, detail="Interpretacion documental no encontrada")
    return interpretation


def create_interpretation(
    db: Session,
    payload: DocumentInterpretationCreate,
    *,
    user_id: int | None = None,
) -> DocumentInterpretation:
    _ensure_document_links(
        db,
        document_id=payload.document_id,
        document_version_id=payload.document_version_id,
    )
    interpretation = DocumentInterpretation(
        **payload.model_dump(),
        created_by_id=user_id,
    )
    db.add(interpretation)
    db.flush()
    write_audit_log(
        db,
        action="document_interpretation.created",
        entity="document_interpretations",
        entity_id=interpretation.id,
        user_id=user_id,
        new_values=payload.model_dump(mode="json"),
    )
    db.commit()
    return get_interpretation(db, interpretation.id)


def update_interpretation(
    db: Session,
    interpretation_id: int,
    payload: DocumentInterpretationUpdate,
    *,
    user_id: int | None = None,
) -> DocumentInterpretation:
    interpretation = get_interpretation(db, interpretation_id)
    if interpretation.status in {"approved", "obsolete"}:
        raise HTTPException(
            status_code=409,
            detail="Crea una nueva version para modificar una interpretacion aprobada u obsoleta",
        )
    updates = payload.model_dump(exclude_unset=True)
    if "document_version_id" in updates:
        _ensure_document_links(
            db,
            document_id=interpretation.document_id,
            document_version_id=updates["document_version_id"],
        )
    previous = {key: getattr(interpretation, key) for key in updates}
    for key, value in updates.items():
        setattr(interpretation, key, value)
    write_audit_log(
        db,
        action="document_interpretation.updated",
        entity="document_interpretations",
        entity_id=interpretation.id,
        user_id=user_id,
        previous_values=previous,
        new_values=payload.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    return get_interpretation(db, interpretation.id)


def approve_interpretation(
    db: Session,
    interpretation_id: int,
    *,
    user_id: int | None = None,
) -> DocumentInterpretation:
    interpretation = get_interpretation(db, interpretation_id)
    previous_status = interpretation.status
    interpretation.status = "approved"
    interpretation.approved_by_id = user_id
    interpretation.approved_at = datetime.now(timezone.utc)
    write_audit_log(
        db,
        action="document_interpretation.approved",
        entity="document_interpretations",
        entity_id=interpretation.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": "approved"},
    )
    db.commit()
    return get_interpretation(db, interpretation.id)


def create_interpretation_new_version(
    db: Session,
    interpretation_id: int,
    *,
    user_id: int | None = None,
) -> DocumentInterpretation:
    source = get_interpretation(db, interpretation_id)
    source.status = "obsolete"
    clone = DocumentInterpretation(
        document_id=source.document_id,
        document_version_id=source.document_version_id,
        name=source.name,
        interpretation_type=source.interpretation_type,
        magnitude=source.magnitude,
        equipment_type=source.equipment_type,
        service_type=source.service_type,
        calibration_scope=source.calibration_scope,
        data=source.data,
        status="draft",
        version=source.version + 1,
        created_by_id=user_id,
    )
    db.add(clone)
    db.flush()
    write_audit_log(
        db,
        action="document_interpretation.new_version",
        entity="document_interpretations",
        entity_id=clone.id,
        user_id=user_id,
        previous_values={"source_id": source.id, "source_version": source.version},
        new_values={"version": clone.version, "status": clone.status},
    )
    db.commit()
    return get_interpretation(db, clone.id)
