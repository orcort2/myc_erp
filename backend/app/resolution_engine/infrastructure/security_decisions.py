"""Verificación única de decisiones persistidas en límites críticos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.security import (
    INTEGRAL_SECURITY_POLICY_KEY,
    INTEGRAL_SECURITY_POLICY_VERSION,
    ActorContext,
    SecurityDecisionUseMode,
    security_operation_hash,
)
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionSecurityDecision,
    ResolutionSecurityDecisionUse,
)


@dataclass(frozen=True, slots=True)
class SecurityDecisionExpectation:
    decision_id: int
    action: str
    resource_type: str
    resource_id: str
    actor: ActorContext
    required_permissions: tuple[ComponentKey, ...]
    occurred_at: datetime
    use_mode: SecurityDecisionUseMode
    operation_id: str
    operation_payload: Mapping[str, Any]
    resolution_id: int | None = None
    plan_id: int | None = None
    plan_version: int | None = None
    plan_hash: str | None = None
    revalidation_id: int | None = None
    revalidation_hash: str | None = None
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SecurityDecisionUseClaim:
    """Resultado de reservar una concesión single-operation."""

    replayed: bool
    operation_context: Mapping[str, Any] = field(default_factory=dict)


class SqlAlchemySecurityDecisionVerifier:
    """Revalida alcance, actor, permisos y hash sin reevaluar políticas."""

    def verify(
        self,
        session: Session,
        expectation: SecurityDecisionExpectation,
        /,
    ) -> tuple[str, ...]:
        decision = session.get(
            ResolutionSecurityDecision,
            expectation.decision_id,
        )
        if decision is None:
            return ("security_decision_missing",)

        actor = expectation.actor
        identity = actor.identity
        authentication = actor.authentication
        reasons = list(actor.validate_at(expectation.occurred_at))
        if decision.outcome != "allowed":
            reasons.append("security_decision_denied")
        if decision.action != expectation.action:
            reasons.append("security_action_mismatch")
        if decision.resource_type != expectation.resource_type:
            reasons.append("security_resource_type_mismatch")
        if decision.resource_id != expectation.resource_id:
            reasons.append("security_resource_id_mismatch")
        if decision.resolution_id != expectation.resolution_id:
            reasons.append("security_resolution_mismatch")
        if decision.actor_id != identity.actor_id:
            reasons.append("security_actor_mismatch")
        if decision.organization_id != identity.organization_id:
            reasons.append("security_organization_mismatch")
        if decision.correlation_id != authentication.correlation_id:
            reasons.append("security_correlation_mismatch")
        if decision.actor_snapshot != identity.snapshot():
            reasons.append("security_actor_snapshot_mismatch")
        if decision.authentication_snapshot != authentication.snapshot():
            reasons.append("security_authentication_snapshot_mismatch")
        evaluated_at = decision.evaluated_at
        if evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)
        if evaluated_at > expectation.occurred_at:
            reasons.append("security_decision_from_future")

        required = [
            str(permission)
            for permission in expectation.required_permissions
        ]
        if decision.required_permissions != required:
            reasons.append("security_required_permissions_mismatch")
        if decision.use_mode != expectation.use_mode.value:
            reasons.append("security_use_mode_mismatch")
        if decision.operation_id != expectation.operation_id:
            reasons.append("security_operation_id_mismatch")
        expected_operation_hash = security_operation_hash(
            action=expectation.action,
            operation_id=expectation.operation_id,
            payload=expectation.operation_payload,
        )
        if decision.operation_hash != expected_operation_hash:
            reasons.append("security_operation_hash_mismatch")
        if decision.operation_payload != dict(expectation.operation_payload):
            reasons.append("security_operation_payload_mismatch")
        for permission in expectation.required_permissions:
            if not any(
                grant.applies_to(
                    permission=permission,
                    resource_type=expectation.resource_type,
                    resource_id=expectation.resource_id,
                    instant=expectation.occurred_at,
                    context=expectation.context,
                )
                for grant in actor.permissions
            ):
                reasons.append("security_permission_not_current")
                break

        if decision.plan_id != expectation.plan_id:
            reasons.append("security_plan_mismatch")
        if decision.plan_version != expectation.plan_version:
            reasons.append("security_plan_version_mismatch")
        if decision.plan_hash != expectation.plan_hash:
            reasons.append("security_plan_hash_mismatch")
        if decision.revalidation_id != expectation.revalidation_id:
            reasons.append("security_revalidation_mismatch")
        if decision.revalidation_hash != expectation.revalidation_hash:
            reasons.append("security_revalidation_hash_mismatch")
        evidence_context = decision.context_snapshot.get("context")
        if evidence_context != dict(expectation.context):
            reasons.append("security_context_mismatch")

        if expectation.resolution_id is not None:
            root = session.get(Resolution, expectation.resolution_id)
            if root is None:
                reasons.append("security_resolution_missing")
            elif root.organization_id != identity.organization_id:
                reasons.append("security_root_organization_mismatch")

        policy = next(
            (
                item
                for item in decision.policy_results
                if item.get("policy_key") == INTEGRAL_SECURITY_POLICY_KEY
            ),
            None,
        )
        if (
            policy is None
            or policy.get("policy_version")
            != INTEGRAL_SECURITY_POLICY_VERSION
            or policy.get("outcome") != "allowed"
        ):
            reasons.append("integral_security_policy_missing")
        for required_policy_key in (
            "security.require_permissions",
            "security.same_organization",
        ):
            baseline_policy = next(
                (
                    item
                    for item in decision.policy_results
                    if item.get("policy_key") == required_policy_key
                ),
                None,
            )
            if (
                baseline_policy is None
                or baseline_policy.get("policy_version") != "1.0"
                or baseline_policy.get("outcome") != "allowed"
            ):
                reasons.append(
                    f"{required_policy_key.replace('.', '_')}_missing"
                )

        payload = decision.context_snapshot.get("evidence_payload")
        if not isinstance(payload, dict):
            reasons.append("security_evidence_payload_missing")
        elif canonical_sha256(payload) != decision.evidence_hash:
            reasons.append("security_evidence_hash_mismatch")
        return tuple(dict.fromkeys(reasons))

    def claim(
        self,
        session: Session,
        expectation: SecurityDecisionExpectation,
        /,
        *,
        operation_context: Mapping[str, Any] | None = None,
    ) -> tuple[SecurityDecisionUseClaim | None, tuple[str, ...]]:
        """Reserva una concesión en la misma transacción de su efecto."""

        decision = session.scalar(
            select(ResolutionSecurityDecision)
            .where(
                ResolutionSecurityDecision.id == expectation.decision_id
            )
            .with_for_update()
        )
        if decision is None:
            return None, ("security_decision_missing",)
        reasons = self.verify(session, expectation)
        if reasons:
            return None, reasons
        if expectation.use_mode is not SecurityDecisionUseMode.SINGLE_OPERATION:
            return None, ("security_use_mode_not_consumable",)

        existing = session.scalar(
            select(ResolutionSecurityDecisionUse).where(
                ResolutionSecurityDecisionUse.security_decision_id
                == expectation.decision_id
            )
        )
        if existing is not None:
            if (
                existing.organization_id
                != expectation.actor.identity.organization_id
                or existing.action != expectation.action
                or existing.operation_id != expectation.operation_id
                or existing.operation_hash != decision.operation_hash
            ):
                return None, ("security_decision_replay_different_operation",)
            return (
                SecurityDecisionUseClaim(
                    replayed=True,
                    operation_context=dict(existing.operation_context),
                ),
                (),
            )

        operation_collision = session.scalar(
            select(ResolutionSecurityDecisionUse).where(
                ResolutionSecurityDecisionUse.organization_id
                == expectation.actor.identity.organization_id,
                ResolutionSecurityDecisionUse.action == expectation.action,
                ResolutionSecurityDecisionUse.operation_id
                == expectation.operation_id,
            )
        )
        if operation_collision is not None:
            return None, ("security_operation_already_authorized",)

        use = ResolutionSecurityDecisionUse(
            security_decision_id=expectation.decision_id,
            resolution_id=expectation.resolution_id,
            organization_id=expectation.actor.identity.organization_id,
            action=expectation.action,
            operation_id=expectation.operation_id,
            operation_hash=decision.operation_hash,
            operation_context=dict(operation_context or {}),
        )
        session.add(use)
        session.flush()
        return (
            SecurityDecisionUseClaim(
                replayed=False,
                operation_context=dict(use.operation_context),
            ),
            (),
        )
