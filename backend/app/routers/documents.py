from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.controlled_document import (
    ControlledDocumentArchive,
    ControlledDocumentCreate,
    ControlledDocumentRead,
    ControlledDocumentUpdate,
    ControlledDocumentVersionCreate,
)
from app.services.auth import require_permission
from app.services.controlled_documents import (
    activate_document_version,
    archive_document,
    create_document,
    create_document_version,
    get_document,
    list_documents,
    update_document,
    create_certificate_master,
)
from app.services.storage_service import resolve_storage_path


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/certificate-masters", response_model=ControlledDocumentRead)
def post_certificate_master(
    code: str = Form(...), name: str = Form(...), revision: str = Form(...),
    effective_date: str = Form(...), expires_on: str | None = Form(None),
    description: str | None = Form(None), file: UploadFile = File(...),
    db: Session = Depends(get_db), current_user: User = Depends(require_permission("documents.create")),
) -> ControlledDocumentRead:
    from datetime import date
    try:
        starts = date.fromisoformat(effective_date)
        ends = date.fromisoformat(expires_on) if expires_on else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Fecha de vigencia inválida") from exc
    return create_certificate_master(db, code=code, name=name, description=description, revision=revision,
        effective_date=starts, expires_on=ends, upload=file, user_id=current_user.id)


@router.get("/{document_id}/versions/{version_id}/download")
def download_document_version(
    document_id: int, version_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents.read")),
) -> FileResponse:
    document = get_document(db, document_id)
    version = next((item for item in document.versions if item.id == version_id), None)
    path = resolve_storage_path(version.file_path if version else None)
    if version is None or path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Archivo documental no disponible")
    return FileResponse(path, media_type=version.mime_type or "application/octet-stream", filename=version.original_filename or path.name)


@router.get("", response_model=list[ControlledDocumentRead])
def get_documents(
    q: str | None = Query(default=None),
    code: str | None = Query(default=None),
    document_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    quality_level: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents.read")),
) -> list[ControlledDocumentRead]:
    return list_documents(
        db,
        q=q,
        code=code,
        document_type=document_type,
        status=status,
        quality_level=quality_level,
    )


@router.post("", response_model=ControlledDocumentRead)
def post_document(
    payload: ControlledDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents.create")),
) -> ControlledDocumentRead:
    return create_document(db, payload, user_id=current_user.id)


@router.get("/{document_id}", response_model=ControlledDocumentRead)
def get_document_by_id(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents.read")),
) -> ControlledDocumentRead:
    return get_document(db, document_id)


@router.patch("/{document_id}", response_model=ControlledDocumentRead)
def patch_document(
    document_id: int,
    payload: ControlledDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents.update")),
) -> ControlledDocumentRead:
    return update_document(db, document_id, payload, user_id=current_user.id)


@router.post("/{document_id}/versions", response_model=ControlledDocumentRead)
def post_document_version(
    document_id: int,
    payload: ControlledDocumentVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents.update")),
) -> ControlledDocumentRead:
    return create_document_version(db, document_id, payload, user_id=current_user.id)


@router.post("/{document_id}/versions/{version_id}/activate", response_model=ControlledDocumentRead)
def post_activate_document_version(
    document_id: int,
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents.approve")),
) -> ControlledDocumentRead:
    return activate_document_version(db, document_id, version_id, user_id=current_user.id)


@router.patch("/{document_id}/archive", response_model=ControlledDocumentRead)
def patch_archive_document(
    document_id: int,
    payload: ControlledDocumentArchive,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("documents.archive")),
) -> ControlledDocumentRead:
    return archive_document(db, document_id, payload, user_id=current_user.id)
