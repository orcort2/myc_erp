from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.document_template import DocumentTemplateOut, DocumentTemplateUpdate
from app.services.document_templates import (
    get_or_create_quotation_template,
    restore_quotation_template_defaults,
    update_quotation_template,
)


router = APIRouter(prefix="/document-templates", tags=["document-templates"])


@router.get("/quotation", response_model=DocumentTemplateOut)
def get_quotation_template(db: Session = Depends(get_db)) -> DocumentTemplateOut:
    return get_or_create_quotation_template(db)


@router.patch("/quotation", response_model=DocumentTemplateOut)
def patch_quotation_template(
    payload: DocumentTemplateUpdate,
    db: Session = Depends(get_db),
) -> DocumentTemplateOut:
    return update_quotation_template(db, payload)


@router.post("/quotation/restore-defaults", response_model=DocumentTemplateOut)
def restore_quotation_template(db: Session = Depends(get_db)) -> DocumentTemplateOut:
    return restore_quotation_template_defaults(db)
