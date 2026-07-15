"""Administrative integration status endpoints."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.core.config import get_settings
from app.models.user import User
from app.services.auth import require_permission
from app.services.facturama.client import FacturamaClient
from app.services.facturama.health import FacturamaHealthService


router = APIRouter(prefix="/integrations", tags=["integrations"])


class FacturamaStatusResponse(BaseModel):
    enabled: bool
    environment: str
    connected: bool
    response_time_ms: float | None = None
    status: str


@router.get("/facturama/status", response_model=FacturamaStatusResponse)
async def get_facturama_status(
    request: Request,
    current_user: User = Depends(require_permission("integrations.facturama.status")),
) -> FacturamaStatusResponse:
    """Safely report configuration and a live, read-only credential verification."""
    del current_user
    settings = get_settings()
    if not settings.facturama_enabled:
        return FacturamaStatusResponse(
            enabled=False,
            environment=settings.facturama_environment,
            connected=False,
            status="disabled",
        )

    facturama_client: FacturamaClient = request.app.state.facturama_client
    result = await FacturamaHealthService(facturama_client, settings).check()
    return FacturamaStatusResponse(
        enabled=True,
        environment=settings.facturama_environment,
        connected=result.status == "connected",
        response_time_ms=result.response_time_ms,
        status=result.status,
    )
