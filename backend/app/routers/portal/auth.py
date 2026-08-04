from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.portal.security import PortalSecurityContext, authenticate_portal_user, get_portal_context, refresh_portal_tokens
from app.schemas.portal.auth import PortalLogin, PortalRefresh, PortalTokenPair
from app.services.audit_logs import write_audit_log

router = APIRouter(prefix="/portal/auth", tags=["portal-auth"])


@router.post("/login", response_model=PortalTokenPair)
def login(payload: PortalLogin, db: Session = Depends(get_db)):
    return authenticate_portal_user(db, payload.identifier, payload.password)


@router.post("/refresh", response_model=PortalTokenPair)
def refresh(payload: PortalRefresh, db: Session = Depends(get_db)):
    return refresh_portal_tokens(db, payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, context: PortalSecurityContext = Depends(get_portal_context), db: Session = Depends(get_db)):
    write_audit_log(db, action="portal.session.logout", entity="users", entity_id=context.user.id, user_id=context.user.id)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
