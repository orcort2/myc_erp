from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogRead


def write_audit_log(
    db: Session,
    *,
    action: str,
    entity: str,
    entity_id: int | None,
    user_id: int | None = None,
    previous_values: dict | None = None,
    new_values: dict | None = None,
    comment: str | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        previous_values=previous_values,
        new_values=new_values,
        comment=comment,
    )
    db.add(log)
    return log


def list_audit_logs(
    db: Session,
    *,
    action: str | None = None,
    entity: str | None = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    limit: int = 100,
) -> list[AuditLogRead]:
    query: Select = (
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    if action is not None:
        query = query.where(AuditLog.action == action)
    if entity is not None:
        query = query.where(AuditLog.entity == entity)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)

    rows = db.execute(query).all()
    return [
        AuditLogRead(
            id=audit_log.id,
            user_id=audit_log.user_id,
            user_name=user_name,
            action=audit_log.action,
            entity=audit_log.entity,
            entity_id=audit_log.entity_id,
            previous_values=audit_log.previous_values,
            new_values=audit_log.new_values,
            comment=audit_log.comment,
            created_at=audit_log.created_at,
        )
        for audit_log, user_name in rows
    ]
