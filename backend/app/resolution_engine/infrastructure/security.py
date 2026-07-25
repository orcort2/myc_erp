"""Adaptador SQLAlchemy para evidencia de seguridad append-only."""

from __future__ import annotations

from typing import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.resolution_engine.domain.security import SecurityDecision
from app.resolution_engine.infrastructure.persistence import (
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
                reason_codes=list(decision.reason_codes),
                actor_snapshot=decision.actor.identity.snapshot(),
                authentication_snapshot=(
                    decision.actor.authentication.snapshot()
                ),
                context_snapshot={
                    **dict(context_snapshot),
                    "attempted_resource": resource.snapshot(),
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
