"""Central email administration: templates, delivery history and transport status.

No generic preview endpoint on purpose: previews are served by the owning
domain (quotations, invoices) from entities the caller is authorized to read.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models.email import EmailDelivery
from app.models.user import User
from app.schemas.email import (
    EmailDeliveryRead,
    EmailDeliverySummary,
    EmailRetryResult,
    EmailTemplateRead,
    EmailTemplateUpdate,
    EmailTransportStatus,
)
from app.services.auth import require_permission
from app.services.email.access import can_read_delivery, scope_deliveries
from app.services.email.catalog import TEMPLATE_DEFINITIONS
from app.services.email.errors import EmailError
from app.services.email.service import RetryNotAllowed, retry_delivery
from app.services.email.templates import get_template, list_templates, update_template

router = APIRouter(prefix="/email", tags=["email"])


def _template_read(template) -> EmailTemplateRead:
    payload = EmailTemplateRead.model_validate(template)
    payload.allowed_variables = sorted(TEMPLATE_DEFINITIONS[template.template_key].variable_names)
    return payload


def _http_error(exc: EmailError) -> HTTPException:
    status = 409 if isinstance(exc, RetryNotAllowed) else 422
    return HTTPException(status_code=status, detail={"code": exc.code, "detail": exc.message})


@router.get("/templates", response_model=list[EmailTemplateRead])
def read_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("email.templates.read")),
):
    return [_template_read(item) for item in list_templates(db)]


@router.get("/templates/{template_key}", response_model=EmailTemplateRead)
def read_template(
    template_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("email.templates.read")),
):
    if template_key not in TEMPLATE_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return _template_read(get_template(db, template_key))


@router.patch("/templates/{template_key}", response_model=EmailTemplateRead)
def patch_template(
    template_key: str,
    payload: EmailTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("email.templates.manage")),
):
    if template_key not in TEMPLATE_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    try:
        template = update_template(db, template_key, actor_id=current_user.id, **payload.model_dump(exclude_unset=True))
    except EmailError as exc:
        db.rollback()
        raise _http_error(exc) from exc
    return _template_read(template)


@router.get("/deliveries", response_model=list[EmailDeliverySummary])
def read_deliveries(
    status: str | None = Query(default=None, pattern="^(pending|sending|sent|failed)$"),
    template_key: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("email.deliveries.read")),
):
    query = select(EmailDelivery).order_by(EmailDelivery.id.desc()).limit(limit).offset(offset)
    if status:
        query = query.where(EmailDelivery.status == status)
    if template_key:
        query = query.where(EmailDelivery.template_key == template_key)
    return list(db.scalars(scope_deliveries(query, current_user)).all())


@router.get("/deliveries/{delivery_id}", response_model=EmailDeliveryRead)
def read_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("email.deliveries.read")),
):
    delivery = db.get(EmailDelivery, delivery_id)
    # 404 for both missing and out-of-scope rows: no existence oracle.
    if delivery is None or not can_read_delivery(current_user, delivery):
        raise HTTPException(status_code=404, detail="Envío de correo no encontrado")
    return delivery


@router.post("/deliveries/{delivery_id}/retry", response_model=EmailRetryResult)
def retry_email_delivery(
    delivery_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("email.deliveries.retry")),
):
    delivery = db.get(EmailDelivery, delivery_id)
    if delivery is None or not can_read_delivery(current_user, delivery):
        raise HTTPException(status_code=404, detail="Envío de correo no encontrado")
    try:
        result = retry_delivery(db, delivery_id, actor_id=current_user.id)
    except EmailError as exc:
        db.rollback()
        raise _http_error(exc) from exc
    return EmailRetryResult(delivery_id=result.delivery_id, status=result.status, sent=result.sent, reason=result.reason)


@router.get("/transport/status", response_model=EmailTransportStatus)
def read_transport_status(
    current_user: User = Depends(require_permission("email.transport.status")),
):
    """Never opens a connection and never returns credentials."""
    settings = get_settings()
    has_auth = bool(settings.smtp_username and settings.smtp_password.get_secret_value())
    return EmailTransportStatus(
        enabled=settings.email_enabled,
        configured=bool(settings.smtp_host and settings.email_from_address),
        host=settings.smtp_host or None,
        port=settings.smtp_port,
        starttls=settings.smtp_use_starttls,
        authentication_mode="smtp_auth" if has_auth else "none_ip_allowlist",
        from_address=settings.email_from_address or None,
    )
