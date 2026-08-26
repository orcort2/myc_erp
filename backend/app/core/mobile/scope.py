from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.mobile.security import MobileSecurityContext
from app.models.lab_work_order import LabWorkOrder


def ensure_lab_work_order_scope(
    db: Session,
    work_order_id: int,
    context: MobileSecurityContext,
) -> None:
    if context.actor_type == "internal":
        return
    owned = db.scalar(
        select(LabWorkOrder.id).where(
            LabWorkOrder.id == work_order_id,
            LabWorkOrder.operator_client_id == context.client_id,
        )
    )
    if owned is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso no encontrado",
        )
