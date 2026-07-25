"""Valores inmutables del núcleo de seguridad del Motor."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.exceptions import InvalidResolutionValueError
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
)


class ActorType(StrEnum):
    HUMAN = "human"
    SERVICE = "service"
    WORKER = "worker"
    INTEGRATION = "integration"
    MOBILE_APP = "mobile_app"
    SYSTEM = "system"


class ActorStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"
    REVOKED = "revoked"
    EXPIRED = "expired"


class SecurityDecisionOutcome(StrEnum):
    ALLOWED = "allowed"
    DENIED = "denied"


def _non_empty(value: str, field_name: str, *, maximum: int = 200) -> str:
    normalized = value.strip() if isinstance(value, str) else ""
    if not normalized or len(normalized) > maximum:
        raise InvalidResolutionValueError(
            f"{field_name} must be a non-empty string up to {maximum} characters"
        )
    return normalized


@dataclass(frozen=True, slots=True)
class ActorIdentity:
    """Identidad institucional estable, independiente del ERP anfitrión."""

    actor_id: str
    actor_type: ActorType
    principal: str
    organization_id: str
    status: ActorStatus = ActorStatus.ACTIVE
    branch_id: str | None = None
    department_id: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "actor_type", ActorType(self.actor_type))
            object.__setattr__(self, "status", ActorStatus(self.status))
        except ValueError as exc:
            raise InvalidResolutionValueError(
                "actor_type and status must use controlled values"
            ) from exc
        object.__setattr__(self, "actor_id", _non_empty(self.actor_id, "actor_id"))
        object.__setattr__(
            self,
            "principal",
            _non_empty(self.principal, "principal", maximum=320),
        )
        object.__setattr__(
            self,
            "organization_id",
            _non_empty(self.organization_id, "organization_id"),
        )
        object.__setattr__(
            self,
            "attributes",
            MappingProxyType(dict(self.attributes)),
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type.value,
            "principal": self.principal,
            "organization_id": self.organization_id,
            "branch_id": self.branch_id,
            "department_id": self.department_id,
            "status": self.status.value,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True)
class AuthenticationContext:
    """Evidencia de la autenticación ya verificada por un adaptador."""

    authenticated_at: datetime
    method: str
    session_id: str
    assurance_level: str
    source: str
    correlation_id: str
    expires_at: datetime | None = None
    delegated_by_actor_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.authenticated_at.tzinfo is None:
            raise InvalidResolutionValueError(
                "authenticated_at must include timezone"
            )
        for name in (
            "method",
            "session_id",
            "assurance_level",
            "source",
            "correlation_id",
        ):
            object.__setattr__(self, name, _non_empty(getattr(self, name), name))
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None:
                raise InvalidResolutionValueError(
                    "expires_at must include timezone"
                )
            if self.expires_at <= self.authenticated_at:
                raise InvalidResolutionValueError(
                    "expires_at must be after authenticated_at"
                )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def is_valid_at(self, instant: datetime) -> bool:
        return self.expires_at is None or instant < self.expires_at

    def snapshot(self) -> dict[str, Any]:
        return {
            "authenticated_at": self.authenticated_at.isoformat(),
            "method": self.method,
            "session_id": self.session_id,
            "assurance_level": self.assurance_level,
            "source": self.source,
            "correlation_id": self.correlation_id,
            "expires_at": (
                self.expires_at.isoformat() if self.expires_at else None
            ),
            "delegated_by_actor_id": self.delegated_by_actor_id,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class PermissionGrant:
    """Capacidad atómica concedida por un proveedor externo de autoridad."""

    permission: ComponentKey
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    constraints: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "permission",
            ComponentKey.parse(self.permission),
        )
        if self.valid_from and self.valid_from.tzinfo is None:
            raise InvalidResolutionValueError("valid_from must include timezone")
        if self.valid_until and self.valid_until.tzinfo is None:
            raise InvalidResolutionValueError("valid_until must include timezone")
        if (
            self.valid_from
            and self.valid_until
            and self.valid_until <= self.valid_from
        ):
            raise InvalidResolutionValueError(
                "valid_until must be after valid_from"
            )
        if (self.resource_type is None) != (self.resource_id is None):
            raise InvalidResolutionValueError(
                "resource_type and resource_id must be provided together"
            )
        object.__setattr__(
            self,
            "constraints",
            MappingProxyType(dict(self.constraints)),
        )

    def applies_to(
        self,
        *,
        permission: ComponentKey,
        resource_type: str,
        resource_id: str,
        instant: datetime,
    ) -> bool:
        return (
            self.permission == permission
            and (self.valid_from is None or self.valid_from <= instant)
            and (self.valid_until is None or instant < self.valid_until)
            and (
                self.resource_type is None
                or (
                    self.resource_type == resource_type
                    and self.resource_id == resource_id
                )
            )
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "permission": str(self.permission),
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": (
                self.valid_until.isoformat() if self.valid_until else None
            ),
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "constraints": dict(self.constraints),
        }


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Contexto completo entregado al núcleo tras autenticar al actor."""

    identity: ActorIdentity
    authentication: AuthenticationContext
    permissions: tuple[PermissionGrant, ...] = ()

    def validate_at(self, instant: datetime) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.identity.status is not ActorStatus.ACTIVE:
            reasons.append("actor_not_active")
        if not self.authentication.is_valid_at(instant):
            reasons.append("authentication_expired")
        return tuple(reasons)

    def snapshot(self) -> dict[str, Any]:
        return {
            "identity": self.identity.snapshot(),
            "authentication": self.authentication.snapshot(),
            "permissions": [grant.snapshot() for grant in self.permissions],
        }


@dataclass(frozen=True, slots=True)
class SecurityResource:
    resource_type: str
    resource_id: str
    organization_id: str
    resolution_id: int | None = None
    resolution_public_id: str | None = None
    plan_id: int | None = None
    plan_version: int | None = None
    plan_hash: str | None = None
    simulation_id: int | None = None
    simulation_hash: str | None = None
    authorization_request_id: int | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("resource_type", "resource_id", "organization_id"):
            object.__setattr__(self, name, _non_empty(getattr(self, name), name))
        if self.plan_id is not None:
            if self.plan_version is None or self.plan_hash is None:
                raise InvalidResolutionValueError(
                    "plan_id requires plan_version and plan_hash"
                )
            if len(self.plan_hash) != 64:
                raise InvalidResolutionValueError("plan_hash must be SHA-256")
        if self.simulation_id is not None:
            if self.plan_id is None or self.simulation_hash is None:
                raise InvalidResolutionValueError(
                    "simulation_id requires plan and simulation_hash"
                )
            if len(self.simulation_hash) != 64:
                raise InvalidResolutionValueError(
                    "simulation_hash must be SHA-256"
                )
        object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))

    def snapshot(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "organization_id": self.organization_id,
            "resolution_id": self.resolution_id,
            "resolution_public_id": self.resolution_public_id,
            "plan_id": self.plan_id,
            "plan_version": self.plan_version,
            "plan_hash": self.plan_hash,
            "simulation_id": self.simulation_id,
            "simulation_hash": self.simulation_hash,
            "authorization_request_id": self.authorization_request_id,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True)
class SecurityRequest:
    actor: ActorContext
    action: ComponentKey
    resource: SecurityResource
    required_permissions: tuple[ComponentKey, ...]
    occurred_functions: Mapping[str, tuple[str, ...]] = field(
        default_factory=dict
    )
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", ComponentKey.parse(self.action))
        object.__setattr__(
            self,
            "required_permissions",
            tuple(
                ComponentKey.parse(permission)
                for permission in self.required_permissions
            ),
        )
        object.__setattr__(
            self,
            "occurred_functions",
            MappingProxyType(
                {
                    key: tuple(actor_ids)
                    for key, actor_ids in self.occurred_functions.items()
                }
            ),
        )
        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))


@dataclass(frozen=True, slots=True)
class PolicyResult:
    policy_key: ComponentKey
    policy_version: DefinitionVersion
    outcome: SecurityDecisionOutcome
    reason_codes: tuple[str, ...]
    conditions: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_key",
            ComponentKey.parse(self.policy_key),
        )
        object.__setattr__(
            self,
            "policy_version",
            DefinitionVersion.parse(self.policy_version),
        )
        if not self.reason_codes:
            raise InvalidResolutionValueError(
                "policy result requires at least one reason code"
            )
        object.__setattr__(
            self,
            "conditions",
            MappingProxyType(dict(self.conditions)),
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "policy_key": str(self.policy_key),
            "policy_version": str(self.policy_version),
            "outcome": self.outcome.value,
            "reason_codes": list(self.reason_codes),
            "conditions": dict(self.conditions),
        }


@dataclass(frozen=True, slots=True)
class SecurityDecision:
    outcome: SecurityDecisionOutcome
    actor: ActorContext
    action: ComponentKey
    resource: SecurityResource
    evaluated_at: datetime
    policy_results: tuple[PolicyResult, ...]
    reason_codes: tuple[str, ...]
    required_permissions: tuple[ComponentKey, ...]
    evidence_hash: str

    @classmethod
    def build(
        cls,
        *,
        outcome: SecurityDecisionOutcome,
        request: SecurityRequest,
        evaluated_at: datetime,
        policy_results: tuple[PolicyResult, ...],
        reason_codes: tuple[str, ...],
    ) -> SecurityDecision:
        evidence = {
            "outcome": outcome.value,
            "actor": request.actor.snapshot(),
            "action": str(request.action),
            "resource": request.resource.snapshot(),
            "evaluated_at": evaluated_at.astimezone(timezone.utc).isoformat(),
            "policy_results": [result.snapshot() for result in policy_results],
            "reason_codes": list(reason_codes),
            "required_permissions": [
                str(permission) for permission in request.required_permissions
            ],
            "occurred_functions": dict(request.occurred_functions),
            "context": dict(request.context),
        }
        return cls(
            outcome=outcome,
            actor=request.actor,
            action=request.action,
            resource=request.resource,
            evaluated_at=evaluated_at,
            policy_results=policy_results,
            reason_codes=reason_codes,
            required_permissions=request.required_permissions,
            evidence_hash=canonical_sha256(evidence),
        )
