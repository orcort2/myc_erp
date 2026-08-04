from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.portal.security import PortalSecurityContext, require_portal_permission
from app.schemas.portal.profile import PortalProfileRead, PortalProfileUpdate

router = APIRouter(prefix="/client-portal/profile", tags=["client-portal-profile"])


def _read(context: PortalSecurityContext) -> PortalProfileRead:
    return PortalProfileRead(id=context.user.id, username=context.user.username, email=context.user.email, full_name=context.user.full_name, client_id=context.client.id, client_name=context.client.commercial_name or context.client.legal_name, membership_id=context.membership.id, permissions=sorted(context.permissions), last_login_at=context.user.last_login_at)


@router.get("", response_model=PortalProfileRead)
def profile(context: PortalSecurityContext = Depends(require_portal_permission("profile.view"))):
    return _read(context)


@router.patch("", response_model=PortalProfileRead)
def update_profile(payload: PortalProfileUpdate, context: PortalSecurityContext = Depends(require_portal_permission("profile.update")), db: Session = Depends(get_db)):
    context.user.full_name = " ".join(payload.full_name.split())
    db.commit()
    return _read(context)
