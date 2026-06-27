from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models.controlled_document import ControlledDocument, ControlledDocumentVersion
from app.schemas.controlled_document import (
    ControlledDocumentArchive,
    ControlledDocumentCreate,
    ControlledDocumentUpdate,
    ControlledDocumentVersionCreate,
)
from app.services.audit_logs import write_audit_log


def _json_safe(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _get_document_query() -> Select:
    return select(ControlledDocument).options(selectinload(ControlledDocument.versions))


def list_documents(
    db: Session,
    *,
    q: str | None = None,
    code: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    quality_level: str | None = None,
) -> list[ControlledDocument]:
    query = _get_document_query().order_by(ControlledDocument.code.asc())
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            ControlledDocument.code.ilike(like) | ControlledDocument.name.ilike(like)
        )
    if code:
        query = query.where(ControlledDocument.code.ilike(f"%{code.strip()}%"))
    if document_type:
        query = query.where(ControlledDocument.document_type == document_type)
    if status:
        query = query.where(ControlledDocument.status == status)
    if quality_level:
        query = query.where(ControlledDocument.quality_level == quality_level)
    return list(db.scalars(query).all())


def get_document(db: Session, document_id: int) -> ControlledDocument:
    document = db.scalar(_get_document_query().where(ControlledDocument.id == document_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Documento controlado no encontrado")
    return document


def create_document(
    db: Session,
    payload: ControlledDocumentCreate,
    *,
    user_id: int | None = None,
) -> ControlledDocument:
    document = ControlledDocument(**payload.model_dump(), created_by_id=user_id)
    db.add(document)
    db.flush()
    write_audit_log(
        db,
        action="controlled_document.created",
        entity="controlled_documents",
        entity_id=document.id,
        user_id=user_id,
        new_values=payload.model_dump(mode="json"),
    )
    db.commit()
    return get_document(db, document.id)


def update_document(
    db: Session,
    document_id: int,
    payload: ControlledDocumentUpdate,
    *,
    user_id: int | None = None,
) -> ControlledDocument:
    document = get_document(db, document_id)
    updates = payload.model_dump(exclude_unset=True)
    previous = {key: _json_safe(getattr(document, key)) for key in updates}
    for key, value in updates.items():
        setattr(document, key, value)
    write_audit_log(
        db,
        action="controlled_document.updated",
        entity="controlled_documents",
        entity_id=document.id,
        user_id=user_id,
        previous_values=previous,
        new_values=payload.model_dump(exclude_unset=True, mode="json"),
    )
    db.commit()
    return get_document(db, document.id)


def create_document_version(
    db: Session,
    document_id: int,
    payload: ControlledDocumentVersionCreate,
    *,
    user_id: int | None = None,
) -> ControlledDocument:
    document = get_document(db, document_id)
    version = ControlledDocumentVersion(
        **payload.model_dump(exclude={"status"}),
        status="draft",
        uploaded_by_id=user_id,
    )
    document.versions.append(version)
    db.flush()
    write_audit_log(
        db,
        action="controlled_document.version_created",
        entity="controlled_documents",
        entity_id=document.id,
        user_id=user_id,
        new_values={"version_id": version.id, **payload.model_dump(mode="json")},
    )
    if payload.status == "active":
        _activate_document_version(db, document, version, user_id=user_id)
    db.commit()
    return get_document(db, document.id)


def _activate_document_version(
    db: Session,
    document: ControlledDocument,
    version: ControlledDocumentVersion,
    *,
    user_id: int | None = None,
) -> None:
    for item in document.versions:
        if item.id != version.id and item.status == "active":
            item.status = "obsolete"
    version.status = "active"
    version.approved_by_id = user_id
    version.approved_at = datetime.now(timezone.utc)
    document.status = "active"
    document.current_revision = version.revision
    document.effective_date = version.effective_date or document.effective_date
    write_audit_log(
        db,
        action="controlled_document.version_activated",
        entity="controlled_documents",
        entity_id=document.id,
        user_id=user_id,
        new_values={"version_id": version.id, "revision": version.revision},
    )


def activate_document_version(
    db: Session,
    document_id: int,
    version_id: int,
    *,
    user_id: int | None = None,
) -> ControlledDocument:
    document = get_document(db, document_id)
    version = next((item for item in document.versions if item.id == version_id), None)
    if version is None:
        raise HTTPException(status_code=404, detail="Version documental no encontrada")
    _activate_document_version(db, document, version, user_id=user_id)
    db.commit()
    return get_document(db, document.id)


def archive_document(
    db: Session,
    document_id: int,
    payload: ControlledDocumentArchive,
    *,
    user_id: int | None = None,
) -> ControlledDocument:
    document = get_document(db, document_id)
    previous_status = document.status
    document.status = payload.status
    write_audit_log(
        db,
        action="controlled_document.archived",
        entity="controlled_documents",
        entity_id=document.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": payload.status},
        comment=payload.comment,
    )
    db.commit()
    return get_document(db, document.id)
