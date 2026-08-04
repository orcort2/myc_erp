from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.client_portal import ClientPortalConfigurationRead, ClientPortalConfigurationUpdate
from app.services.auth import require_permission
from app.services.client_portal_configuration_service import get_configuration, save_configuration

router = APIRouter(prefix="/client-portal/configuration", tags=["client-portal-configuration"])


@router.get("/{client_id}", response_model=ClientPortalConfigurationRead)
def get_client_portal_configuration(client_id: int, db: Session = Depends(get_db), _actor: User = Depends(require_permission("users.manage"))):
    item = get_configuration(db, client_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Configuración del portal no encontrada")
    return item


@router.put("/{client_id}", response_model=ClientPortalConfigurationRead)
def put_client_portal_configuration(client_id: int, payload: ClientPortalConfigurationUpdate, db: Session = Depends(get_db), actor: User = Depends(require_permission("users.manage"))):
    return save_configuration(db, client_id, payload.model_dump(), actor.id)
