from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification, PushDevice
from app.models.user import User
from app.schemas.notification import PushDeviceCreate


logger = logging.getLogger("app.push_notifications")
EXPO_TOKEN_PREFIXES = ("ExponentPushToken[", "ExpoPushToken[")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _valid_expo_token(token: str) -> bool:
    return token.startswith(EXPO_TOKEN_PREFIXES) and token.endswith("]")


def register_push_device(
    db: Session, payload: PushDeviceCreate, user: User
) -> PushDevice:
    token = payload.expo_push_token.strip()
    if not _valid_expo_token(token):
        raise HTTPException(status_code=422, detail="Expo push token inválido")
    device = db.scalar(select(PushDevice).where(PushDevice.expo_push_token == token))
    now = _now()
    if device is None:
        device = PushDevice(
            user_id=user.id,
            expo_push_token=token,
            platform=payload.platform,
            device_name=payload.device_name,
            app_version=payload.app_version,
            is_active=True,
            last_seen_at=now,
        )
        db.add(device)
    else:
        device.user_id = user.id
        device.platform = payload.platform
        device.device_name = payload.device_name
        device.app_version = payload.app_version
        device.is_active = True
        device.last_seen_at = now
    db.commit()
    db.refresh(device)
    return device


def deactivate_push_device(db: Session, device_id: int, user: User) -> PushDevice:
    device = db.scalar(
        select(PushDevice).where(
            PushDevice.id == device_id,
            PushDevice.user_id == user.id,
        )
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Dispositivo push no encontrado")
    device.is_active = False
    device.last_seen_at = _now()
    db.commit()
    return device


class ExpoPushNotificationService:
    def send(self, messages: list[dict]) -> list[dict]:
        response = httpx.post(
            settings.expo_push_url,
            json=messages,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=settings.expo_push_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data")
        if not isinstance(data, list) or len(data) != len(messages):
            raise ValueError("Respuesta Expo Push inválida")
        return data


expo_push_service = ExpoPushNotificationService()


def queue_notification_for_delivery(db: Session, notification: Notification) -> None:
    db.flush()
    queued = db.info.setdefault("push_notification_ids", [])
    if notification.id not in queued:
        queued.append(notification.id)


def deliver_notification_ids(db: Session, notification_ids: list[int]) -> None:
    if not notification_ids:
        return
    notifications = list(
        db.scalars(select(Notification).where(Notification.id.in_(notification_ids))).all()
    )
    recipient_ids = {item.recipient_user_id for item in notifications}
    devices = list(
        db.scalars(
            select(PushDevice).where(
                PushDevice.user_id.in_(recipient_ids), PushDevice.is_active.is_(True)
            )
        ).all()
    )
    devices_by_user: dict[int, list[PushDevice]] = {}
    for device in devices:
        devices_by_user.setdefault(device.user_id, []).append(device)

    now = _now()
    messages: list[dict] = []
    message_context: list[tuple[Notification, PushDevice]] = []
    for notification in notifications:
        active_devices = devices_by_user.get(notification.recipient_user_id, [])
        notification.push_attempted_at = now
        if not active_devices:
            notification.delivery_status = "no_devices"
            continue
        for device in active_devices:
            messages.append(
                {
                    "to": device.expo_push_token,
                    "title": notification.title,
                    "body": notification.body or "",
                    "sound": "default",
                    "channelId": "operational",
                    "data": {
                        "event_type": notification.notification_type,
                        "entity_type": notification.entity_type,
                        "entity_id": notification.entity_id,
                        **(notification.metadata_json or {}),
                    },
                }
            )
            message_context.append((notification, device))

    if messages:
        try:
            results = expo_push_service.send(messages)
        except (httpx.HTTPError, ValueError) as exc:
            for notification in notifications:
                if devices_by_user.get(notification.recipient_user_id):
                    notification.delivery_status = "failed"
                    notification.error_code = "provider_unavailable"
            logger.warning(
                "Expo Push falló notification_ids=%s category=%s",
                notification_ids,
                type(exc).__name__,
            )
        else:
            successes: dict[int, int] = {}
            failures: dict[int, int] = {}
            for result, (notification, device) in zip(results, message_context, strict=True):
                if result.get("status") == "ok":
                    successes[notification.id] = successes.get(notification.id, 0) + 1
                    continue
                failures[notification.id] = failures.get(notification.id, 0) + 1
                details = result.get("details") or {}
                error = details.get("error") or result.get("message") or "provider_error"
                if error == "DeviceNotRegistered":
                    device.is_active = False
                logger.info(
                    "Expo Push rechazó notification_id=%s user_id=%s category=%s",
                    notification.id,
                    notification.recipient_user_id,
                    error,
                )
            for notification in notifications:
                if successes.get(notification.id):
                    notification.delivery_status = "sent"
                    notification.push_delivered_at = now
                    notification.error_code = (
                        "partial_failure" if failures.get(notification.id) else None
                    )
                elif devices_by_user.get(notification.recipient_user_id):
                    notification.delivery_status = "failed"
                    notification.error_code = "device_not_registered"
    db.commit()


def commit_and_dispatch_notifications(db: Session) -> None:
    notification_ids = list(db.info.pop("push_notification_ids", []))
    db.commit()
    if not notification_ids:
        return
    try:
        deliver_notification_ids(db, notification_ids)
    except Exception:
        db.rollback()
        logger.exception("Entrega push inesperadamente fallida notification_ids=%s", notification_ids)
