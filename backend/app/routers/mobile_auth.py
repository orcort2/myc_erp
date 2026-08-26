from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.mobile.security import (
    MobileSecurityContext,
    authenticate_mobile_user,
    get_mobile_context,
    refresh_mobile_tokens,
)
from app.schemas.mobile_auth import (
    MobileLogin,
    MobileRefreshTokenRequest,
    MobileTokenPair,
    MobileUserRead,
)


router = APIRouter(prefix="/mobile/v1/auth", tags=["mobile-auth"])


@router.post("/login", response_model=MobileTokenPair)
def login(payload: MobileLogin, db: Session = Depends(get_db)) -> MobileTokenPair:
    return authenticate_mobile_user(db, str(payload.email), payload.password)


@router.post("/refresh", response_model=MobileTokenPair)
def refresh(
    payload: MobileRefreshTokenRequest,
    db: Session = Depends(get_db),
) -> MobileTokenPair:
    return refresh_mobile_tokens(db, payload.refresh_token)


@router.get("/me", response_model=MobileUserRead)
def me(context: MobileSecurityContext = Depends(get_mobile_context)) -> MobileUserRead:
    return MobileUserRead(
        id=context.user.id,
        email=context.user.email,
        full_name=context.user.full_name,
        is_active=context.user.is_active,
        permissions=sorted(context.permissions),
        actor_type=context.actor_type,
        client_id=context.client_id,
        membership_id=context.membership_id,
    )
