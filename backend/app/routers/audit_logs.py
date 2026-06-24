from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.services.auth import require_permission
from app.services.audit_logs import list_audit_logs


router = APIRouter(prefix="/audit-logs", tags=["audit_logs"])


@router.get("", response_model=list[AuditLogRead])
def get_audit_logs(
    action: str | None = Query(default=None),
    entity: str | None = Query(default=None),
    entity_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit_logs.read")),
) -> list[AuditLogRead]:
    return list_audit_logs(
        db,
        action=action,
        entity=entity,
        entity_id=entity_id,
        user_id=user_id,
        limit=limit,
    )
