from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.controlled_document import (
    DocumentInterpretationCreate,
    DocumentInterpretationRead,
    DocumentInterpretationUpdate,
)
from app.services.auth import require_permission
from app.services.document_interpretations import (
    approve_interpretation,
    create_interpretation,
    create_interpretation_new_version,
    get_interpretation,
    list_interpretations,
    update_interpretation,
)


router = APIRouter(prefix="/document-interpretations", tags=["document-interpretations"])


@router.get("", response_model=list[DocumentInterpretationRead])
def get_document_interpretations(
    document_id: int | None = Query(default=None),
    magnitude: str | None = Query(default=None),
    equipment_type: str | None = Query(default=None),
    interpretation_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_interpretations.read")),
) -> list[DocumentInterpretationRead]:
    return list_interpretations(
        db,
        document_id=document_id,
        magnitude=magnitude,
        equipment_type=equipment_type,
        interpretation_type=interpretation_type,
        status=status,
    )


@router.post("", response_model=DocumentInterpretationRead)
def post_document_interpretation(
    payload: DocumentInterpretationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_interpretations.create")),
) -> DocumentInterpretationRead:
    return create_interpretation(db, payload, user_id=current_user.id)


@router.get("/{interpretation_id}", response_model=DocumentInterpretationRead)
def get_document_interpretation_by_id(
    interpretation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_interpretations.read")),
) -> DocumentInterpretationRead:
    return get_interpretation(db, interpretation_id)


@router.patch("/{interpretation_id}", response_model=DocumentInterpretationRead)
def patch_document_interpretation(
    interpretation_id: int,
    payload: DocumentInterpretationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_interpretations.update")),
) -> DocumentInterpretationRead:
    return update_interpretation(db, interpretation_id, payload, user_id=current_user.id)


@router.post("/{interpretation_id}/approve", response_model=DocumentInterpretationRead)
def post_approve_document_interpretation(
    interpretation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_interpretations.approve")),
) -> DocumentInterpretationRead:
    return approve_interpretation(db, interpretation_id, user_id=current_user.id)


@router.post("/{interpretation_id}/new-version", response_model=DocumentInterpretationRead)
def post_document_interpretation_new_version(
    interpretation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_interpretations.create")),
) -> DocumentInterpretationRead:
    return create_interpretation_new_version(db, interpretation_id, user_id=current_user.id)
