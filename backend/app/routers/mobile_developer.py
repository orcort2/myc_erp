from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.developer_policy import DEVELOPER_ACCESS, DEVELOPER_SYSTEM_READ
from app.core.mobile.developer import (
    developer_session_status,
    developer_token_header,
    lock_developer_session,
    open_developer_session,
    require_developer_session,
    require_mobile_developer_capability,
)
from app.core.mobile.security import MobileSecurityContext, get_mobile_context
from app.developer_broker.client import BrokerClient
from app.models.developer_session import DeveloperSession
from app.schemas.mobile_developer import (
    DeveloperBrokerHealth,
    DeveloperSessionOpened,
    DeveloperSessionStatus,
    DeveloperUnlockRequest,
)
from app.services.developer_broker import developer_broker_health, get_developer_broker_client


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


@router.get("/broker/health", response_model=DeveloperBrokerHealth)
def read_developer_broker_health(
    record: DeveloperSession = Depends(require_developer_session(DEVELOPER_SYSTEM_READ)),
    client: BrokerClient | None = Depends(get_developer_broker_client),
    db: Session = Depends(get_db),
) -> DeveloperBrokerHealth:
    """DEV-1A diagnostic: live DeveloperSession + explicit
    ``developer.system.read`` (DEV-0 guard), then ``broker.health`` through
    the BrokerClient. Executes nothing; 503 if the Broker is unusable."""
    return DeveloperBrokerHealth(
        **developer_broker_health(db, record, DEVELOPER_SYSTEM_READ, client)
    )
