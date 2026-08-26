from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.portal.constants import ClientPortalMembershipStatus
from app.models.client_portal_membership import ClientPortalMembership
from app.models.user import User


ACTIVE_MEMBERSHIP_CONFLICT = "Este usuario ya pertenece a otra organización activa."


def ensure_single_active_membership(
    db: Session,
    *,
    user_id: int,
    exclude_membership_id: int | None = None,
) -> None:
    """Serialize membership activation by user and reject another active client."""
    if db.scalar(select(User.id).where(User.id == user_id).with_for_update()) is None:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    query = select(ClientPortalMembership.id).where(
        ClientPortalMembership.user_id == user_id,
        ClientPortalMembership.status == ClientPortalMembershipStatus.ACTIVE.value,
    )
    if exclude_membership_id is not None:
        query = query.where(ClientPortalMembership.id != exclude_membership_id)
    if db.scalar(query.limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ACTIVE_MEMBERSHIP_CONFLICT,
        )
