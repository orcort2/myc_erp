"""Evaluación determinista y autorización base del Motor de Resoluciones."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.resolution_engine.contracts.runtime import Clock
from app.resolution_engine.contracts.security import (
    SecurityEvidenceStore,
    SecurityResourceVerifier,
)
from app.resolution_engine.domain.security import (
    PolicyResult,
    SecurityDecision,
    SecurityDecisionOutcome,
    SecurityRequest,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
)


class SecurityPolicy(Protocol):
    """Política localizable, versionada y sin efectos laterales."""

    policy_key: ComponentKey
    policy_version: DefinitionVersion

    def applies_to(self, request: SecurityRequest, /) -> bool:
        """Indica si la política gobierna la solicitud."""

    def evaluate(
        self,
        request: SecurityRequest,
        /,
        *,
        evaluated_at: datetime,
    ) -> PolicyResult:
        """Produce siempre el mismo resultado para las mismas entradas."""


@dataclass(frozen=True, slots=True)
class PermissionPolicy:
    """Exige capacidades atómicas exactas, sin herencia implícita."""

    policy_key = ComponentKey("security.require_permissions")
    policy_version = DefinitionVersion("1.0")

    def applies_to(self, request: SecurityRequest, /) -> bool:
        return True

    def evaluate(
        self,
        request: SecurityRequest,
        /,
        *,
        evaluated_at: datetime,
    ) -> PolicyResult:
        missing = [
            str(permission)
            for permission in request.required_permissions
            if not any(
                grant.applies_to(
                    permission=permission,
                    resource_type=request.resource.resource_type,
                    resource_id=request.resource.resource_id,
                    instant=evaluated_at,
                )
                for grant in request.actor.permissions
            )
        ]
        outcome = (
            SecurityDecisionOutcome.DENIED
            if missing
            else SecurityDecisionOutcome.ALLOWED
        )
        return PolicyResult(
            policy_key=self.policy_key,
            policy_version=self.policy_version,
            outcome=outcome,
            reason_codes=(
                ("missing_required_permissions",)
                if missing
                else ("required_permissions_present",)
            ),
            conditions={
                "required": [
                    str(permission)
                    for permission in request.required_permissions
                ],
                "missing": missing,
            },
        )


@dataclass(frozen=True, slots=True)
class OrganizationBoundaryPolicy:
    """Impide operar recursos pertenecientes a otra organización."""

    policy_key = ComponentKey("security.same_organization")
    policy_version = DefinitionVersion("1.0")

    def applies_to(self, request: SecurityRequest, /) -> bool:
        return True

    def evaluate(
        self,
        request: SecurityRequest,
        /,
        *,
        evaluated_at: datetime,
    ) -> PolicyResult:
        matches = (
            request.actor.identity.organization_id
            == request.resource.organization_id
        )
        return PolicyResult(
            policy_key=self.policy_key,
            policy_version=self.policy_version,
            outcome=(
                SecurityDecisionOutcome.ALLOWED
                if matches
                else SecurityDecisionOutcome.DENIED
            ),
            reason_codes=(
                ("organization_matches",)
                if matches
                else ("organization_mismatch",)
            ),
            conditions={
                "actor_organization_id": (
                    request.actor.identity.organization_id
                ),
                "resource_organization_id": (
                    request.resource.organization_id
                ),
            },
        )


@dataclass(frozen=True, slots=True)
class SegregationRule:
    """Incompatibilidades aplicables a una acción concreta."""

    action: ComponentKey
    current_function: str
    incompatible_functions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SegregationOfDutiesPolicy:
    """Aplica separación de funciones configurada por política."""

    rules: tuple[SegregationRule, ...]
    policy_key = ComponentKey("security.segregation_of_duties")
    policy_version = DefinitionVersion("1.0")

    def applies_to(self, request: SecurityRequest, /) -> bool:
        return any(rule.action == request.action for rule in self.rules)

    def evaluate(
        self,
        request: SecurityRequest,
        /,
        *,
        evaluated_at: datetime,
    ) -> PolicyResult:
        actor_id = request.actor.identity.actor_id
        applicable = tuple(
            rule for rule in self.rules if rule.action == request.action
        )
        conflicts = sorted(
            {
                function
                for rule in applicable
                for function in rule.incompatible_functions
                if actor_id in request.occurred_functions.get(function, ())
            }
        )
        allowed = not conflicts
        return PolicyResult(
            policy_key=self.policy_key,
            policy_version=self.policy_version,
            outcome=(
                SecurityDecisionOutcome.ALLOWED
                if allowed
                else SecurityDecisionOutcome.DENIED
            ),
            reason_codes=(
                ("segregation_satisfied",)
                if allowed
                else ("segregation_conflict",)
            ),
            conditions={
                "actor_id": actor_id,
                "current_functions": sorted(
                    {rule.current_function for rule in applicable}
                ),
                "conflicting_functions": conflicts,
            },
        )


class SecurityPolicyEvaluator:
    """Combina políticas con deny explícito y deny-by-default."""

    def __init__(self, policies: tuple[SecurityPolicy, ...]) -> None:
        self._policies = policies

    def evaluate(
        self,
        request: SecurityRequest,
        /,
        *,
        evaluated_at: datetime,
    ) -> SecurityDecision:
        applicable = tuple(
            policy for policy in self._policies if policy.applies_to(request)
        )
        actor_reasons = request.actor.validate_at(evaluated_at)
        if not applicable:
            return SecurityDecision.build(
                outcome=SecurityDecisionOutcome.DENIED,
                request=request,
                evaluated_at=evaluated_at,
                policy_results=(),
                reason_codes=("no_applicable_policy",),
            )

        results = tuple(
            policy.evaluate(request, evaluated_at=evaluated_at)
            for policy in applicable
        )
        denied_results = tuple(
            result
            for result in results
            if result.outcome is SecurityDecisionOutcome.DENIED
        )
        reasons = actor_reasons + tuple(
            reason
            for result in denied_results
            for reason in result.reason_codes
        )
        if reasons:
            outcome = SecurityDecisionOutcome.DENIED
        else:
            outcome = SecurityDecisionOutcome.ALLOWED
            reasons = ("all_applicable_policies_allowed",)
        return SecurityDecision.build(
            outcome=outcome,
            request=request,
            evaluated_at=evaluated_at,
            policy_results=results,
            reason_codes=reasons,
        )


class ResolutionAuthorizationService:
    """Autoriza recursos del Motor y conserva evidencia, sin lifecycle."""

    def __init__(
        self,
        *,
        evaluator: SecurityPolicyEvaluator,
        evidence_store: SecurityEvidenceStore,
        resource_verifier: SecurityResourceVerifier,
        clock: Clock,
    ) -> None:
        self._evaluator = evaluator
        self._evidence_store = evidence_store
        self._resource_verifier = resource_verifier
        self._clock = clock

    def authorize(
        self,
        request: SecurityRequest,
        /,
    ) -> SecurityDecision:
        evaluated_at = self._clock.now()
        scope_reasons = self._resource_verifier.verify(request.resource)
        if scope_reasons:
            decision = SecurityDecision.build(
                outcome=SecurityDecisionOutcome.DENIED,
                request=request,
                evaluated_at=evaluated_at,
                policy_results=(),
                reason_codes=("evidence_scope_invalid",) + scope_reasons,
            )
        else:
            decision = self._evaluator.evaluate(
                request,
                evaluated_at=evaluated_at,
            )
        self._evidence_store.append(
            decision,
            context_snapshot={
                "occurred_functions": dict(request.occurred_functions),
                "context": dict(request.context),
            },
        )
        return decision
