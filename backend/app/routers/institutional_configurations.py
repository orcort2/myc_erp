from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.institutional_configuration import (
    InstitutionalConfigurationRead,
    InstitutionalConfigurationUpdate,
)
from app.services.auth import require_permission
from app.services.institutional_configurations import (
    get_or_create_institutional_configuration,
    update_institutional_configuration,
)


router = APIRouter(prefix="/institutional-configuration", tags=["institutional-configuration"])


@router.get("", response_model=InstitutionalConfigurationRead)
def get_configuration(
    db: Session = Depends(get_db),
):
    return get_or_create_institutional_configuration(db)


@router.patch("", response_model=InstitutionalConfigurationRead)
def patch_configuration(
    payload: InstitutionalConfigurationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("field_sheet_templates.update")),
):
    return update_institutional_configuration(db, payload, user_id=current_user.id)
