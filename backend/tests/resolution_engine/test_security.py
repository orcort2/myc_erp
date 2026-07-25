from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.resolution_engine.application.security import (
    OrganizationBoundaryPolicy,
    PermissionPolicy,
    ResolutionAuthorizationService,
    SecurityPolicyEvaluator,
    SegregationOfDutiesPolicy,
    SegregationRule,
)
from app.resolution_engine.domain.security import (
    ActorContext,
    ActorIdentity,
    ActorStatus,
    ActorType,
    AuthenticationContext,
    PermissionGrant,
    PolicyResult,
    SecurityDecisionOutcome,
    SecurityRequest,
    SecurityResource,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
)

NOW = datetime(2026, 7, 24, 20, 0, tzinfo=timezone.utc)
AUTHORIZE_PLAN = ComponentKey("resolution.plan.authorize")
AUTHORIZE_PERMISSION = ComponentKey("resolution.plan.authorize")


class FixedClock:
    def now(self) -> datetime:
        return NOW


class MemoryEvidenceStore:
    def __init__(self) -> None:
        self.items = []

    def append(self, decision, /, *, context_snapshot) -> None:
        self.items.append((decision, dict(context_snapshot)))


class ValidResourceVerifier:
    def verify(self, resource, /):
        return ()


class InvalidResourceVerifier:
    def verify(self, resource, /):
        return ("plan_resolution_version_hash_mismatch",)


def actor_context(
    *,
    actor_id: str = "actor:approver",
    organization_id: str = "organization:myc",
    status: ActorStatus = ActorStatus.ACTIVE,
    permissions: tuple[PermissionGrant, ...] | None = None,
) -> ActorContext:
    return ActorContext(
        identity=ActorIdentity(
            actor_id=actor_id,
            actor_type=ActorType.HUMAN,
            principal="approver@example.test",
            organization_id=organization_id,
            status=status,
        ),
        authentication=AuthenticationContext(
            authenticated_at=NOW - timedelta(minutes=5),
            expires_at=NOW + timedelta(minutes=30),
            method="erp.jwt.access",
            session_id="session:1",
            assurance_level="standard",
            source="erp",
            correlation_id="correlation:phase3",
        ),
        permissions=permissions
        if permissions is not None
        else (PermissionGrant(permission=AUTHORIZE_PERMISSION),),
    )


def plan_resource(
    *,
    organization_id: str = "organization:myc",
) -> SecurityResource:
    return SecurityResource(
        resource_type="resolution_plan",
        resource_id="plan:20",
        organization_id=organization_id,
        resolution_id=10,
        resolution_public_id="resolution:10",
        plan_id=20,
        plan_version=3,
        plan_hash="a" * 64,
        simulation_id=30,
        simulation_hash="b" * 64,
        authorization_request_id=40,
    )


def request(
    *,
    actor: ActorContext | None = None,
    resource: SecurityResource | None = None,
    occurred_functions=None,
) -> SecurityRequest:
    return SecurityRequest(
        actor=actor or actor_context(),
        action=AUTHORIZE_PLAN,
        resource=resource or plan_resource(),
        required_permissions=(AUTHORIZE_PERMISSION,),
        occurred_functions=occurred_functions or {},
        context={"resolution_status": "pending_authorization"},
    )


def service(policies, verifier=None):
    store = MemoryEvidenceStore()
    return (
        ResolutionAuthorizationService(
            evaluator=SecurityPolicyEvaluator(tuple(policies)),
            evidence_store=store,
            resource_verifier=verifier or ValidResourceVerifier(),
            clock=FixedClock(),
        ),
        store,
    )


def test_actor_context_keeps_identity_authentication_and_permissions_separate():
    actor = actor_context()

    snapshot = actor.snapshot()

    assert snapshot["identity"]["actor_id"] == "actor:approver"
    assert snapshot["authentication"]["method"] == "erp.jwt.access"
    assert snapshot["permissions"][0]["permission"] == (
        "resolution.plan.authorize"
    )
    assert "roles" not in snapshot


def test_public_contract_api_preserves_foundation_and_security_ports():
    from app.resolution_engine import contracts

    assert contracts.Analyzer is not None
    assert contracts.Clock is not None
    assert contracts.ActorContextProvider is not None
    assert contracts.SecurityEvidenceStore is not None
    assert contracts.SecurityResourceVerifier is not None


def test_no_applicable_policy_is_denied_and_evidenced():
    authorization, store = service(())

    decision = authorization.authorize(request())

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert decision.reason_codes == ("no_applicable_policy",)
    assert store.items[0][0] is decision


def test_exact_permission_and_organization_allow_plan_authorization():
    authorization, store = service(
        (PermissionPolicy(), OrganizationBoundaryPolicy())
    )

    decision = authorization.authorize(request())

    assert decision.outcome is SecurityDecisionOutcome.ALLOWED
    assert decision.reason_codes == ("all_applicable_policies_allowed",)
    assert decision.resource.plan_version == 3
    assert decision.resource.plan_hash == "a" * 64
    assert decision.resource.simulation_hash == "b" * 64
    assert len(decision.evidence_hash) == 64
    assert len(store.items) == 1


def test_missing_atomic_permission_is_explicitly_denied():
    authorization, _ = service(
        (PermissionPolicy(), OrganizationBoundaryPolicy())
    )

    decision = authorization.authorize(
        request(actor=actor_context(permissions=()))
    )

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert "missing_required_permissions" in decision.reason_codes


def test_cross_organization_access_is_explicitly_denied():
    authorization, _ = service(
        (PermissionPolicy(), OrganizationBoundaryPolicy())
    )

    decision = authorization.authorize(
        request(resource=plan_resource(organization_id="organization:other"))
    )

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert "organization_mismatch" in decision.reason_codes


def test_inactive_actor_is_denied_even_when_every_policy_allows():
    authorization, _ = service(
        (PermissionPolicy(), OrganizationBoundaryPolicy())
    )

    decision = authorization.authorize(
        request(actor=actor_context(status=ActorStatus.REVOKED))
    )

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert "actor_not_active" in decision.reason_codes


def test_segregation_prevents_requester_from_authorizing_own_plan():
    segregation = SegregationOfDutiesPolicy(
        rules=(
            SegregationRule(
                action=AUTHORIZE_PLAN,
                current_function="approver",
                incompatible_functions=("requester", "plan_builder"),
            ),
        )
    )
    authorization, _ = service(
        (PermissionPolicy(), OrganizationBoundaryPolicy(), segregation)
    )

    decision = authorization.authorize(
        request(
            occurred_functions={
                "requester": ("actor:approver",),
                "plan_builder": ("actor:builder",),
            }
        )
    )

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert "segregation_conflict" in decision.reason_codes
    assert decision.policy_results[-1].conditions[
        "conflicting_functions"
    ] == ["requester"]


@dataclass(frozen=True)
class ExplicitDenyPolicy:
    policy_key = ComponentKey("security.explicit_deny_test")
    policy_version = DefinitionVersion("1.0")

    def applies_to(self, request, /):
        return True

    def evaluate(self, request, /, *, evaluated_at):
        return PolicyResult(
            policy_key=self.policy_key,
            policy_version=self.policy_version,
            outcome=SecurityDecisionOutcome.DENIED,
            reason_codes=("institutional_block",),
        )


def test_explicit_deny_overrides_allowing_policies():
    authorization, _ = service(
        (
            PermissionPolicy(),
            OrganizationBoundaryPolicy(),
            ExplicitDenyPolicy(),
        )
    )

    decision = authorization.authorize(request())

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert "institutional_block" in decision.reason_codes


def test_foreign_or_tampered_plan_evidence_is_denied_before_policies():
    authorization, store = service(
        (PermissionPolicy(), OrganizationBoundaryPolicy()),
        verifier=InvalidResourceVerifier(),
    )

    decision = authorization.authorize(request())

    assert decision.outcome is SecurityDecisionOutcome.DENIED
    assert decision.reason_codes == (
        "evidence_scope_invalid",
        "plan_resolution_version_hash_mismatch",
    )
    assert decision.policy_results == ()
    assert store.items[0][0] is decision


def test_same_inputs_produce_the_same_reproducible_evidence_hash():
    authorization, _ = service(
        (PermissionPolicy(), OrganizationBoundaryPolicy())
    )
    security_request = request()

    first = authorization.authorize(security_request)
    second = authorization.authorize(security_request)

    assert first == second
    assert first.evidence_hash == second.evidence_hash
