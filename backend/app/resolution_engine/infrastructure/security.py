"""Adaptador SQLAlchemy para evidencia de seguridad append-only."""

from __future__ import annotations

from datetime import timezone
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.resolution_engine.domain.security import SecurityDecision
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionExecution,
    ResolutionRevalidation,
    ResolutionSecurityDecision,
)
from app.resolution_engine.infrastructure.persistence.governance import (
    ResolutionAuthorizationRequest,
)
from app.resolution_engine.infrastructure.persistence.planning import (
    ResolutionPlan,
    ResolutionSimulation,
)


class SqlAlchemySecurityEvidenceStore:
    """Agrega evidencia sin confirmar ni controlar la transacción."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        decision: SecurityDecision,
        /,
        *,
        context_snapshot: Mapping[str, Any],
    ) -> None:
        resource = decision.resource
        invalid_scope = "evidence_scope_invalid" in decision.reason_codes
        evidence_payload = {
            "outcome": decision.outcome.value,
            "actor": decision.actor.snapshot(),
            "action": str(decision.action),
            "resource": resource.snapshot(),
            "evaluated_at": (
                decision.evaluated_at.astimezone(timezone.utc).isoformat()
            ),
            "policy_results": [
                result.snapshot() for result in decision.policy_results
            ],
            "reason_codes": list(decision.reason_codes),
            "required_permissions": [
                str(permission)
                for permission in decision.required_permissions
            ],
            "use_mode": decision.use_mode.value,
            "operation_id": decision.operation_id,
            "operation_payload": dict(
                context_snapshot.get("operation_payload", {})
            ),
            "operation_hash": decision.operation_hash,
            "occurred_functions": dict(
                context_snapshot.get("occurred_functions", {})
            ),
            "context": dict(context_snapshot.get("context", {})),
        }
        self._session.add(
            ResolutionSecurityDecision(
                resolution_id=resource.resolution_id,
                authorization_request_id=(
                    None
                    if invalid_scope
                    else resource.authorization_request_id
                ),
                plan_id=None if invalid_scope else resource.plan_id,
                plan_version=None if invalid_scope else resource.plan_version,
                plan_hash=None if invalid_scope else resource.plan_hash,
                simulation_id=None if invalid_scope else resource.simulation_id,
                simulation_hash=(
                    None if invalid_scope else resource.simulation_hash
                ),
                revalidation_id=(
                    None if invalid_scope else resource.revalidation_id
                ),
                revalidation_hash=(
                    None if invalid_scope else resource.revalidation_hash
                ),
                actor_id=decision.actor.identity.actor_id,
                actor_type=decision.actor.identity.actor_type.value,
                organization_id=decision.actor.identity.organization_id,
                action=str(decision.action),
                resource_type=resource.resource_type,
                resource_id=resource.resource_id,
                outcome=decision.outcome.value,
                policy_results=[
                    result.snapshot() for result in decision.policy_results
                ],
                required_permissions=[
                    str(permission)
                    for permission in decision.required_permissions
                ],
                use_mode=decision.use_mode.value,
                operation_id=decision.operation_id,
                operation_hash=decision.operation_hash,
                operation_payload=dict(
                    context_snapshot.get("operation_payload", {})
                ),
                reason_codes=list(decision.reason_codes),
                actor_snapshot=decision.actor.identity.snapshot(),
                authentication_snapshot=(
                    decision.actor.authentication.snapshot()
                ),
                context_snapshot={
                    **dict(context_snapshot),
                    "attempted_resource": resource.snapshot(),
                    "evidence_payload": evidence_payload,
                },
                evaluated_at=decision.evaluated_at,
                correlation_id=(
                    decision.actor.authentication.correlation_id
                ),
                evidence_hash=decision.evidence_hash,
            )
        )


class SqlAlchemySecurityResourceVerifier:
    """Valida por claves exactas sin consultar módulos propietarios."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def verify(self, resource, /) -> tuple[str, ...]:
        reasons: list[str] = []
        if resource.resolution_id is not None:
            resolution = self._session.get(
                Resolution,
                resource.resolution_id,
            )
            if resolution is None:
                reasons.append("resolution_missing")
            else:
                if resolution.organization_id != resource.organization_id:
                    reasons.append("resolution_organization_mismatch")
                if (
                    resource.resolution_public_id is not None
                    and resolution.public_id
                    != resource.resolution_public_id
                ):
                    reasons.append("resolution_public_id_mismatch")
                if (
                    resource.resource_type == "resolution"
                    and resource.resource_id
                    not in {
                        str(resolution.id),
                        resolution.public_id,
                    }
                ):
                    reasons.append("resolution_resource_id_mismatch")
        if resource.plan_id is not None:
            plan = self._session.scalar(
                select(ResolutionPlan).where(
                    ResolutionPlan.id == resource.plan_id,
                    ResolutionPlan.resolution_id == resource.resolution_id,
                    ResolutionPlan.version == resource.plan_version,
                    ResolutionPlan.plan_hash == resource.plan_hash,
                )
            )
            if plan is None:
                reasons.append("plan_resolution_version_hash_mismatch")
            elif (
                resource.resource_type == "resolution_plan"
                and resource.resource_id != str(plan.id)
            ):
                reasons.append("plan_resource_id_mismatch")
        if resource.simulation_id is not None:
            simulation = self._session.scalar(
                select(ResolutionSimulation).where(
                    ResolutionSimulation.id == resource.simulation_id,
                    ResolutionSimulation.resolution_id == resource.resolution_id,
                    ResolutionSimulation.plan_id == resource.plan_id,
                    ResolutionSimulation.simulation_hash
                    == resource.simulation_hash,
                )
            )
            if simulation is None:
                reasons.append("simulation_resolution_plan_hash_mismatch")
        if resource.revalidation_id is not None:
            revalidation = self._session.scalar(
                select(ResolutionRevalidation).where(
                    ResolutionRevalidation.id
                    == resource.revalidation_id,
                    ResolutionRevalidation.resolution_id
                    == resource.resolution_id,
                    ResolutionRevalidation.plan_id == resource.plan_id,
                    ResolutionRevalidation.revalidation_hash
                    == resource.revalidation_hash,
                )
            )
            if revalidation is None:
                reasons.append(
                    "revalidation_resolution_plan_hash_mismatch"
                )
        if resource.resource_type == "resolution_execution":
            try:
                execution_id = int(resource.resource_id)
            except (TypeError, ValueError):
                execution_id = None
            execution = (
                self._session.scalar(
                    select(ResolutionExecution).where(
                        ResolutionExecution.id == execution_id,
                        ResolutionExecution.resolution_id
                        == resource.resolution_id,
                    )
                )
                if execution_id is not None
                else None
            )
            if execution is None:
                reasons.append("execution_resolution_mismatch")
        if resource.authorization_request_id is not None:
            authorization = self._session.scalar(
                select(ResolutionAuthorizationRequest).where(
                    ResolutionAuthorizationRequest.id
                    == resource.authorization_request_id,
                    ResolutionAuthorizationRequest.resolution_id
                    == resource.resolution_id,
                    ResolutionAuthorizationRequest.plan_id == resource.plan_id,
                    ResolutionAuthorizationRequest.plan_hash
                    == resource.plan_hash,
                    ResolutionAuthorizationRequest.simulation_id
                    == resource.simulation_id,
                    ResolutionAuthorizationRequest.simulation_hash
                    == resource.simulation_hash,
                )
            )
            if authorization is None:
                reasons.append("authorization_evidence_mismatch")
        return tuple(reasons)
