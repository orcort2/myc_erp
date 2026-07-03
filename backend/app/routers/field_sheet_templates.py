from fastapi import APIRouter

from app.schemas.field_sheet_template import FieldSheetTemplateRead
from app.services.field_sheet_templates import (
    get_field_sheet_template,
    list_field_sheet_templates,
)

router = APIRouter(prefix="/field-sheet-templates", tags=["Field Sheet Templates"])


@router.get("", response_model=list[FieldSheetTemplateRead])
def list_templates():
    return list_field_sheet_templates()


@router.get("/{template_key}", response_model=FieldSheetTemplateRead)
def get_template(template_key: str):
    return get_field_sheet_template(template_key)