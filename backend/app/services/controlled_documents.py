from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile, status
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
from app.services.storage_service import build_storage_path


MAX_MASTER_FILE_BYTES = 20 * 1024 * 1024


def _validate_master_xlsx(upload: UploadFile, raw: bytes) -> None:
    filename = upload.filename or ""
    if Path(filename).suffix.lower() != ".xlsx":
        raise HTTPException(status_code=422, detail="La Plantilla Maestra debe ser un archivo .xlsx")
    if len(raw) > MAX_MASTER_FILE_BYTES:
        raise HTTPException(status_code=422, detail="El archivo XLSX excede el máximo de 20 MB")
    try:
        with ZipFile(BytesIO(raw)) as archive:
            if "[Content_Types].xml" not in archive.namelist() or "xl/workbook.xml" not in archive.namelist():
                raise ValueError("estructura XLSX incompleta")
    except (BadZipFile, ValueError) as exc:
        raise HTTPException(status_code=422, detail="El archivo no es un XLSX válido") from exc


def create_certificate_master(
    db: Session, *, code: str, name: str, description: str | None, revision: str,
    effective_date, expires_on, upload: UploadFile, user_id: int | None,
) -> ControlledDocument:
    raw = upload.file.read()
    _validate_master_xlsx(upload, raw)
    if expires_on and effective_date and expires_on <= effective_date:
        raise HTTPException(status_code=422, detail="La fecha de caducidad debe ser posterior a la vigencia")
    document = ControlledDocument(code=code.strip(), name=name.strip(), document_type="certificate_master",
        description=description, status="draft", effective_date=effective_date, created_by_id=user_id)
    db.add(document)
    db.flush()
    original = upload.filename or f"{code}.xlsx"
    stored_name = f"{document.id}-{sha256(raw).hexdigest()[:12]}.xlsx"
    target = build_storage_path(directory=f"certificate-masters/{document.id}", filename=stored_name)
    target.write_bytes(raw)
    version = ControlledDocumentVersion(document_id=document.id, revision=revision.strip(),
        file_path=f"certificate-masters/{document.id}/{target.name}", original_filename=original,
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", checksum=sha256(raw).hexdigest(),
        file_size_bytes=len(raw), effective_date=effective_date, expires_on=expires_on, status="draft", uploaded_by_id=user_id)
    document.versions.append(version)
    db.flush()
    write_audit_log(db, action="certificate_master.created", entity="controlled_documents", entity_id=document.id, user_id=user_id,
        new_values={"code": document.code, "revision": revision, "filename": original, "checksum": version.checksum})
    db.commit()
    return get_document(db, document.id)


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
    if document.document_type == "certificate_master":
        if not version.file_path or Path(version.file_path).suffix.lower() != ".xlsx":
            raise HTTPException(status_code=422, detail="Una Plantilla Maestra activa requiere archivo .xlsx")
        if version.expires_on and version.expires_on < datetime.now(timezone.utc).date():
            raise HTTPException(status_code=422, detail="No se puede activar una Plantilla Maestra caducada")
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
