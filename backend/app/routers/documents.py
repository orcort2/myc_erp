from __future__ import annotations

from fastapi import APIRouter, Depends, Query
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
)


router = APIRouter(prefix="/documents", tags=["documents"])


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
