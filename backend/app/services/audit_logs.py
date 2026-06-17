from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


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

