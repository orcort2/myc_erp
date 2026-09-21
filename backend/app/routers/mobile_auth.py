from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.auth import user_can_resolve_own_lab_folios
from app.core.mobile.security import (
    MobileSecurityContext,
    authenticate_mobile_user,
    get_mobile_context,
    refresh_mobile_tokens,
    logout_mobile_session,
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
    return authenticate_mobile_user(db, str(payload.email), payload.password, payload.device)


@router.post("/refresh", response_model=MobileTokenPair)
def refresh(
    payload: MobileRefreshTokenRequest,
    db: Session = Depends(get_db),
) -> MobileTokenPair:
    if payload.device is None and "device" in payload.model_fields_set:
        raise HTTPException(status_code=422, detail="Omite device; null no identifica una instalación")
    return refresh_mobile_tokens(db, payload.refresh_token, payload.device)


@router.get("/me", response_model=MobileUserRead)
def me(context: MobileSecurityContext = Depends(get_mobile_context)) -> MobileUserRead:
    return MobileUserRead(
        id=context.user.id,
        email=context.user.email,
        full_name=context.user.full_name,
        is_active=context.user.is_active,
        permissions=sorted(context.permissions),
        can_resolve_own_lab_folios=context.actor_type == "internal" and user_can_resolve_own_lab_folios(context.user),
        actor_type=context.actor_type,
        client_id=context.client_id,
        membership_id=context.membership_id,
    )


@router.post("/logout", status_code=204)
def logout(
    context: MobileSecurityContext = Depends(get_mobile_context),
    db: Session = Depends(get_db),
) -> Response:
    logout_mobile_session(db, context)
    return Response(status_code=204)
