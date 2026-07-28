"""Adaptación explícita de usuarios ERP a actores canónicos del Motor."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.user import User
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorType,
    AuthenticationContext,
    PermissionGrant,
)
from app.resolution_engine.domain.value_objects import ComponentKey
from app.services.auth import user_has_permission


DOMAIN_PERMISSIONS_BY_CENTER_PERMISSION = {
    "resolution_center.create": ("resolution.create",),
    "resolution_center.prepare": ("resolution.context.build",),
    "resolution_center.analyze": ("resolution.analyze",),
    "resolution_center.plan": (
        "resolution.strategy.select",
        "resolution.plan.build",
    ),
    "resolution_center.simulate": ("resolution.simulate",),
    "resolution_center.authorize": ("resolution.plan.authorize",),
    "resolution_center.execute": (
        "resolution.revalidate",
        "resolution.execute",
    ),
    "resolution_center.audit": ("resolution.audit.inspect",),
}


def actor_for_user(
    user: User,
    *,
    organization_id: str,
    correlation_id: str | None = None,
) -> ActorContext:
    now = datetime.now(timezone.utc)
    permissions = {
        domain_permission
        for center_permission, domain_permissions
        in DOMAIN_PERMISSIONS_BY_CENTER_PERMISSION.items()
        if user_has_permission(user, center_permission)
        for domain_permission in domain_permissions
    }
    if any(
        user_has_permission(user, permission)
        for permission in (
            "resolution_center.prepare",
            "resolution_center.analyze",
            "resolution_center.plan",
            "resolution_center.simulate",
            "resolution_center.authorize",
            "resolution_center.execute",
        )
    ):
        permissions.add("resolution.lifecycle.transition")
    return ActorContext(
        identity=ActorIdentity(
            actor_id=f"user:{user.id}",
            actor_type=ActorType.HUMAN,
            principal=user.email,
            organization_id=organization_id,
            attributes={
                "full_name": user.full_name,
                "roles": sorted(role.name for role in user.roles if role.is_active),
            },
        ),
        authentication=AuthenticationContext(
            authenticated_at=now,
            # La decisión por operación y su consumo único son la autoridad
            # durable. No se arrastra la caducidad del token HTTP al worker.
            expires_at=None,
            method="erp_access_token",
            session_id=f"resolution-center:{user.id}:{uuid4()}",
            assurance_level="authenticated",
            source="resolution_center",
            correlation_id=correlation_id or str(uuid4()),
        ),
        permissions=tuple(
            PermissionGrant(permission=ComponentKey(permission))
            for permission in sorted(permissions)
        ),
    )
