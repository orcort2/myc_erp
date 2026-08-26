from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, WebSocket
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.services.auth import resolve_access_token_user
from app.core.mobile.security import resolve_mobile_token


REALTIME_PROTOCOL = "myc.realtime.v1"
AUTH_PROTOCOL_PREFIX = "auth."


class RealtimeAuthenticationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RealtimeIdentity:
    user_id: int
    expires_at: datetime
    actor_type: str = "internal"
    client_id: int | None = None
    membership_id: int | None = None
    permissions: frozenset[str] = frozenset()


def _token_from_subprotocols(websocket: WebSocket) -> str:
    header = websocket.headers.get("sec-websocket-protocol", "")
    protocols = [item.strip() for item in header.split(",") if item.strip()]
    if REALTIME_PROTOCOL not in protocols:
        raise RealtimeAuthenticationError("Protocolo realtime no soportado")
    encoded = next(
        (item[len(AUTH_PROTOCOL_PREFIX) :] for item in protocols if item.startswith(AUTH_PROTOCOL_PREFIX)),
        "",
    )
    if not encoded:
        raise RealtimeAuthenticationError("Credencial realtime ausente")
    return encoded


def authenticate_websocket(
    db: Session, websocket: WebSocket
) -> RealtimeIdentity:
    token = _token_from_subprotocols(websocket)
    try:
        payload = decode_token(token)
        expires_at = datetime.fromtimestamp(float(payload["exp"]), tz=timezone.utc)
        auth_context = payload.get("auth_context", "internal")
        if auth_context == "internal":
            user = resolve_access_token_user(db, token)
            actor_type = "internal"
            client_id = membership_id = None
            permissions = frozenset()
        elif auth_context in {"mobile_internal", "mobile_client"}:
            context = resolve_mobile_token(db, token)
            user = context.user
            actor_type = context.actor_type
            client_id = context.client_id
            membership_id = context.membership_id
            permissions = context.permissions
        else:
            raise ValueError("Contexto realtime no soportado")
    except (HTTPException, KeyError, TypeError, ValueError, OverflowError) as exc:
        raise RealtimeAuthenticationError("Credencial realtime inválida") from exc
    if expires_at <= datetime.now(timezone.utc):
        raise RealtimeAuthenticationError("Credencial realtime expirada")
    return RealtimeIdentity(
        user_id=user.id,
        expires_at=expires_at,
        actor_type=actor_type,
        client_id=client_id,
        membership_id=membership_id,
        permissions=permissions,
    )
