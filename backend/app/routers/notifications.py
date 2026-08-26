from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.core.mobile.security import MobileSecurityContext, get_mobile_context
from app.schemas.notification import (
    NotificationListRead,
    NotificationMarkRead,
    NotificationRead,
    NotificationUnreadCountRead,
    PushDeviceCreate,
    PushDeviceRead,
)
from app.services.auth import get_current_user
from app.services.notifications import (
    get_unread_notification_count,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.services.push_notifications import deactivate_push_device, register_push_device

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)

mobile_router = APIRouter(
    prefix="/mobile/v1/notifications",
    tags=["mobile-notifications"],
)


@mobile_router.post("/devices", response_model=PushDeviceRead, status_code=201)
def post_push_device(
    payload: PushDeviceCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(get_mobile_context),
):
    return register_push_device(db, payload, context.user)


@mobile_router.delete("/devices/{device_id}", response_model=PushDeviceRead)
def delete_push_device(
    device_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(get_mobile_context),
):
    return deactivate_push_device(db, device_id, context.user)


@mobile_router.get("", response_model=NotificationListRead)
def get_mobile_notifications(
    unread_only: bool = Query(default=False),
    notification_type: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(get_mobile_context),
):
    notifications, total = list_notifications(
        db,
        user_id=context.user.id,
        unread_only=unread_only,
        notification_type=notification_type,
        offset=offset,
        limit=limit,
    )
    return NotificationListRead(items=notifications, total=total)


@mobile_router.get("/unread-count", response_model=NotificationUnreadCountRead)
def get_mobile_notifications_unread_count(
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(get_mobile_context),
):
    return NotificationUnreadCountRead(
        count=get_unread_notification_count(db, user_id=context.user.id)
    )


@mobile_router.post("/{notification_id}/read", response_model=NotificationRead)
def post_mobile_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(get_mobile_context),
):
    notification = mark_notification_read(
        db,
        notification_id=notification_id,
        user_id=context.user.id,
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    db.commit()
    db.refresh(notification)
    return notification


@mobile_router.post("/read-all", response_model=NotificationMarkRead)
def post_mobile_notifications_read_all(
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(get_mobile_context),
):
    mark_all_notifications_read(db, user_id=context.user.id)
    db.commit()
    return NotificationMarkRead(success=True)


@router.get(
    "",
    response_model=NotificationListRead,
)
def get_notifications(
    unread_only: bool = Query(default=False),
    notification_type: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifications, total = list_notifications(
        db,
        user_id=current_user.id,
        unread_only=unread_only,
        notification_type=notification_type,
        offset=offset,
        limit=limit,
    )

    return NotificationListRead(
        items=notifications,
        total=total,
    )


@router.get(
    "/unread-count",
    response_model=NotificationUnreadCountRead,
)
def get_notifications_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = get_unread_notification_count(
        db,
        user_id=current_user.id,
    )

    return NotificationUnreadCountRead(
        count=count,
    )


@router.post(
    "/{notification_id}/read",
    response_model=NotificationRead,
)
def post_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = mark_notification_read(
        db,
        notification_id=notification_id,
        user_id=current_user.id,
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada",
        )

    db.commit()
    db.refresh(notification)

    return notification


@router.post(
    "/read-all",
    response_model=NotificationMarkRead,
)
def post_notifications_read_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mark_all_notifications_read(
        db,
        user_id=current_user.id,
    )

    db.commit()

    return NotificationMarkRead(
        success=True,
    )
