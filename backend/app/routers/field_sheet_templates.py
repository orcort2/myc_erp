from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.field_sheet_template import (
    FieldSheetTemplateCatalogRead,
    FieldSheetTemplateCreate,
    FieldSheetTemplateImport,
    FieldSheetTemplateRead,
    FieldSheetTemplateUpdate,
)
from app.services.auth import require_permission
from app.services.field_sheet_templates import (
    activate_field_sheet_template,
    create_field_sheet_template,
    delete_field_sheet_template,
    duplicate_field_sheet_template,
    export_field_sheet_template,
    get_field_sheet_template,
    get_field_sheet_template_catalog,
    import_field_sheet_template,
    list_field_sheet_templates,
    update_field_sheet_template,
)


router = APIRouter(prefix="/field-sheet-templates", tags=["Field Sheet Templates"])


@router.get("/catalog", response_model=FieldSheetTemplateCatalogRead)
def get_template_catalog(
    current_user: User = Depends(require_permission("field_sheet_templates.read")),
):
    return get_field_sheet_template_catalog()


@router.get("", response_model=list[FieldSheetTemplateRead])
def list_templates(
    include_all: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.read")),
):
    return list_field_sheet_templates(db, include_all=include_all)


@router.get("/{template_key}", response_model=FieldSheetTemplateRead)
def get_template(
    template_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.read")),
):
    return get_field_sheet_template(db, template_key)


@router.post("", response_model=FieldSheetTemplateRead, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: FieldSheetTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.create")),
):
    return create_field_sheet_template(db, payload, user_id=current_user.id)


@router.post("/import", response_model=FieldSheetTemplateRead, status_code=status.HTTP_201_CREATED)
def import_template(
    payload: FieldSheetTemplateImport,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.import")),
):
    return import_field_sheet_template(db, payload, user_id=current_user.id)


@router.patch("/{template_id}", response_model=FieldSheetTemplateRead)
def patch_template(
    template_id: int,
    payload: FieldSheetTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.update")),
):
    return update_field_sheet_template(db, template_id, payload, user_id=current_user.id)


@router.post("/{template_id}/duplicate", response_model=FieldSheetTemplateRead)
def duplicate_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.create")),
):
    return duplicate_field_sheet_template(db, template_id, user_id=current_user.id)


@router.post("/{template_id}/activate", response_model=FieldSheetTemplateRead)
def activate_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.approve")),
):
    return activate_field_sheet_template(db, template_id, user_id=current_user.id)


@router.get("/{template_id}/export")
def export_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.export")),
):
    return export_field_sheet_template(db, template_id, user_id=current_user.id)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.archive")),
) -> Response:
    delete_field_sheet_template(db, template_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
