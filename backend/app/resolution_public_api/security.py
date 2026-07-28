"""Autenticación de consumidor y traducción al ActorContext canónico."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.resolution_api_consumer import ResolutionApiConsumer
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorType,
    AuthenticationContext,
    PermissionGrant,
)
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_public_api.errors import PublicApiError


@dataclass(frozen=True, slots=True)
class PublicApiConsumerContext:
    consumer: ResolutionApiConsumer
    actor: ActorContext
    correlation_id: str


def hash_consumer_secret(secret: str) -> str:
    return hmac.new(
        settings.secret_key.encode(),
        secret.encode(),
        hashlib.sha256,
    ).hexdigest()


def provision_consumer(
    session: Session,
    *,
    consumer_key: str,
    name: str,
    organization_id: str,
    permissions: tuple[str, ...],
) -> tuple[ResolutionApiConsumer, str]:
    """Provisiona localmente; el secreto sólo se devuelve una vez."""

    secret = secrets.token_urlsafe(32)
    consumer = ResolutionApiConsumer(
        consumer_key=consumer_key,
        name=name,
        organization_id=organization_id,
        secret_hash=hash_consumer_secret(secret),
        permissions=list(permissions),
    )
    session.add(consumer)
    session.flush()
    return consumer, f"{consumer_key}.{secret}"


def authenticate_consumer(
    session: Session,
    *,
    authorization: str | None,
    organization_id: str | None,
    correlation_id: str,
) -> PublicApiConsumerContext:
    unauthorized = PublicApiError(
        status_code=401,
        code="consumer_authentication_failed",
        message="Consumer credentials are invalid.",
        correlation_id=correlation_id,
    )
    if not authorization or not authorization.startswith("Bearer "):
        raise unauthorized
    token = authorization.removeprefix("Bearer ").strip()
    try:
        consumer_key, secret = token.split(".", 1)
    except ValueError:
        raise unauthorized from None
    consumer = session.scalar(
        select(ResolutionApiConsumer).where(
            ResolutionApiConsumer.consumer_key == consumer_key
        )
    )
    now = datetime.now(timezone.utc)
    if (
        consumer is None
        or not consumer.is_active
        or (
            consumer.expires_at is not None
            and _as_utc(consumer.expires_at) <= now
        )
        or not hmac.compare_digest(
            consumer.secret_hash,
            hash_consumer_secret(secret),
        )
    ):
        raise unauthorized
    if not organization_id or organization_id != consumer.organization_id:
        raise PublicApiError(
            status_code=403,
            code="organization_scope_mismatch",
            message="The requested organization is outside the consumer scope.",
            correlation_id=correlation_id,
        )
    actor = ActorContext(
        identity=ActorIdentity(
            actor_id=f"api-consumer:{consumer.consumer_key}",
            actor_type=ActorType.SERVICE,
            principal=consumer.name,
            organization_id=consumer.organization_id,
            attributes={"consumer_key": consumer.consumer_key},
        ),
        authentication=AuthenticationContext(
            authenticated_at=now,
            method="api_consumer_secret",
            session_id=f"{consumer.consumer_key}:{correlation_id}",
            assurance_level="institutional",
            source="resolution_public_api_v1",
            correlation_id=correlation_id,
            metadata={"contract_version": "1.0"},
        ),
        permissions=tuple(
            PermissionGrant(permission=ComponentKey.parse(permission))
            for permission in consumer.permissions
        ),
    )
    return PublicApiConsumerContext(
        consumer=consumer,
        actor=actor,
        correlation_id=correlation_id,
    )


def _as_utc(value: datetime) -> datetime:
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )
