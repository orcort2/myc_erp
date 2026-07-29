from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity import ActivityMessage
from app.models.notification import Notification
from app.models.user import User


NOTIFICATION_TYPE_ACTIVITY_MENTION = "activity_mention"


def _utc_now() -> datetime:
    """
    Devuelve la fecha y hora actual en UTC.
    """
    return datetime.now(timezone.utc)


def _message_excerpt(
    body: str,
    *,
    max_length: int = 180,
) -> str:
    """
    Genera un fragmento limpio y compacto para mostrar
    dentro de una notificación.
    """
    normalized = " ".join((body or "").split())

    if len(normalized) <= max_length:
        return normalized

    return f"{normalized[: max_length - 1].rstrip()}…"


def create_activity_mention_notification(
    db: Session,
    *,
    message: ActivityMessage,
    recipient_user_id: int,
    actor: User,
) -> Notification | None:
    """
    Crea, actualiza o reactiva una notificación por mención.

    No crea una notificación cuando el autor se menciona a sí mismo.

    Esta función no ejecuta commit. La transacción debe ser
    confirmada por el servicio público que crea o edita el mensaje.
    """
    if recipient_user_id == actor.id:
        return None

    existing = db.scalar(
        select(Notification).where(
            Notification.recipient_user_id == recipient_user_id,
            Notification.notification_type
            == NOTIFICATION_TYPE_ACTIVITY_MENTION,
            Notification.activity_message_id == message.id,
        )
    )

    thread = message.thread
    title = f"{actor.full_name} te mencionó"
    body = _message_excerpt(message.body)

    if existing is not None:
        was_revoked = existing.revoked_at is not None

        existing.actor_user_id = actor.id
        existing.title = title
        existing.body = body
        existing.entity_type = thread.entity_type
        existing.entity_id = thread.entity_id
        existing.priority = "normal"
        existing.metadata_json = existing.metadata_json or {}
        existing.revoked_at = None
        existing.updated_at = _utc_now()

        if was_revoked:
            existing.read_at = None
            existing.dismissed_at = None

        return existing

    now = _utc_now()

    notification = Notification(
        recipient_user_id=recipient_user_id,
        actor_user_id=actor.id,
        notification_type=NOTIFICATION_TYPE_ACTIVITY_MENTION,
        title=title,
        body=body,
        entity_type=thread.entity_type,
        entity_id=thread.entity_id,
        activity_message_id=message.id,
        priority="normal",
        metadata_json={},
        created_at=now,
        updated_at=now,
    )

    db.add(notification)

    return notification

def revoke_activity_mention_notification(
    db: Session,
    *,
    message_id: int,
    recipient_user_id: int,
) -> Notification | None:
    """
    Revoca la notificación asociada con una mención eliminada.

    La notificación no se borra físicamente para conservar
    trazabilidad y permitir una futura reactivación.

    Esta función no ejecuta commit.
    """
    notification = db.scalar(
        select(Notification).where(
            Notification.recipient_user_id == recipient_user_id,
            Notification.notification_type
            == NOTIFICATION_TYPE_ACTIVITY_MENTION,
            Notification.activity_message_id == message_id,
        )
    )

    if notification is None:
        return None

    if notification.revoked_at is None:
        notification.revoked_at = _utc_now()

    return notification


def revoke_activity_mention_notifications(
    db: Session,
    *,
    message_id: int,
    recipient_user_ids: set[int] | list[int] | tuple[int, ...],
) -> list[Notification]:
    """
    Revoca las notificaciones de varios usuarios que dejaron
    de estar mencionados en un mensaje.

    Esta función no ejecuta commit.
    """
    normalized_user_ids = {
        int(user_id)
        for user_id in recipient_user_ids
    }

    if not normalized_user_ids:
        return []

    notifications = list(
        db.scalars(
            select(Notification).where(
                Notification.recipient_user_id.in_(normalized_user_ids),
                Notification.notification_type
                == NOTIFICATION_TYPE_ACTIVITY_MENTION,
                Notification.activity_message_id == message_id,
                Notification.revoked_at.is_(None),
            )
        ).all()
    )

    revoked_at = _utc_now()

    for notification in notifications:
        notification.revoked_at = revoked_at

    return notifications


def get_unread_notification_count(
    db: Session,
    *,
    user_id: int,
) -> int:
    """
    Devuelve el total de notificaciones activas y no leídas
    pertenecientes al usuario.
    """
    count = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.recipient_user_id == user_id,
            Notification.read_at.is_(None),
            Notification.dismissed_at.is_(None),
            Notification.revoked_at.is_(None),
        )
    )

    return int(count or 0)

def get_notification(
    db: Session,
    *,
    notification_id: int,
    user_id: int,
) -> Notification | None:
    """
    Obtiene una notificación activa perteneciente al usuario.

    No devuelve notificaciones revocadas ni pertenecientes
    a otro usuario.
    """
    return db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_user_id == user_id,
            Notification.revoked_at.is_(None),
        )
    )


def list_notifications(
    db: Session,
    *,
    user_id: int,
    unread_only: bool = False,
    notification_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Notification], int]:
    """
    Lista las notificaciones activas del usuario y devuelve:

    - elementos de la página;
    - total de resultados antes de aplicar offset y limit.

    Las notificaciones revocadas y descartadas no aparecen.
    """
    filters = [
        Notification.recipient_user_id == user_id,
        Notification.dismissed_at.is_(None),
        Notification.revoked_at.is_(None),
    ]

    if unread_only:
        filters.append(Notification.read_at.is_(None))

    if notification_type:
        filters.append(
            Notification.notification_type == notification_type
        )

    total = db.scalar(
        select(func.count(Notification.id)).where(*filters)
    )

    notifications = list(
        db.scalars(
            select(Notification)
            .where(*filters)
            .order_by(
                Notification.created_at.desc(),
                Notification.id.desc(),
            )
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 100))
        ).all()
    )

    return notifications, int(total or 0)


def mark_notification_read(
    db: Session,
    *,
    notification_id: int,
    user_id: int,
) -> Notification | None:
    """
    Marca una notificación como leída.

    Sólo permite modificar notificaciones pertenecientes al usuario.
    La operación es idempotente: si ya estaba leída, no modifica
    nuevamente la fecha.

    Esta función no ejecuta commit.
    """
    notification = get_notification(
        db,
        notification_id=notification_id,
        user_id=user_id,
    )

    if notification is None:
        return None

    if notification.dismissed_at is not None:
        return None

    if notification.read_at is None:
        notification.read_at = _utc_now()

    return notification


def mark_all_notifications_read(
    db: Session,
    *,
    user_id: int,
) -> int:
    """
    Marca como leídas todas las notificaciones activas y no leídas
    pertenecientes al usuario.

    Devuelve el número de notificaciones modificadas.

    Esta función no ejecuta commit.
    """
    notifications = list(
        db.scalars(
            select(Notification).where(
                Notification.recipient_user_id == user_id,
                Notification.read_at.is_(None),
                Notification.dismissed_at.is_(None),
                Notification.revoked_at.is_(None),
            )
        ).all()
    )

    if not notifications:
        return 0

    read_at = _utc_now()

    for notification in notifications:
        notification.read_at = read_at

    return len(notifications)