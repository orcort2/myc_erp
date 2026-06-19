from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.audit_log import AuditLogRead
from app.services.audit_logs import list_audit_logs


router = APIRouter(prefix="/audit-logs", tags=["audit_logs"])


@router.get("", response_model=list[AuditLogRead])
def get_audit_logs(
    entity: str | None = Query(default=None),
    entity_id: int | None = Query(default=None),
    user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AuditLogRead]:
    return list_audit_logs(
        db,
        entity=entity,
        entity_id=entity_id,
        user_id=user_id,
        limit=limit,
    )
