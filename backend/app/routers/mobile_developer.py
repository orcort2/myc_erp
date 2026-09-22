from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.developer_policy import DEVELOPER_ACCESS
from app.core.mobile.developer import (
    developer_session_status,
    developer_token_header,
    lock_developer_session,
    open_developer_session,
    require_mobile_developer_capability,
)
from app.core.mobile.security import MobileSecurityContext, get_mobile_context
from app.schemas.mobile_developer import (
    DeveloperSessionOpened,
    DeveloperSessionStatus,
    DeveloperUnlockRequest,
)


router = APIRouter(prefix="/mobile/v1/developer", tags=["mobile-developer"])


@router.post("/session", response_model=DeveloperSessionOpened)
def unlock_developer_session(
    payload: DeveloperUnlockRequest,
    context: MobileSecurityContext = Depends(require_mobile_developer_capability(DEVELOPER_ACCESS)),
    db: Session = Depends(get_db),
) -> DeveloperSessionOpened:
    return DeveloperSessionOpened(
        **open_developer_session(db, context, payload.biometric_credential)
    )


@router.get("/session", response_model=DeveloperSessionStatus)
def read_developer_session_status(
    developer_token: str = Depends(developer_token_header),
    context: MobileSecurityContext = Depends(get_mobile_context),
    db: Session = Depends(get_db),
) -> DeveloperSessionStatus:
    return DeveloperSessionStatus(
        **developer_session_status(db, context, developer_token)
    )


@router.delete("/session", status_code=204)
def lock_developer_session_endpoint(
    developer_token: str = Depends(developer_token_header),
    context: MobileSecurityContext = Depends(get_mobile_context),
    db: Session = Depends(get_db),
) -> Response:
    lock_developer_session(db, context, developer_token)
    return Response(status_code=204)
