from __future__ import annotations

from dataclasses import dataclass

from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.domain.definitions import (
    ComponentReference,
    ResolutionDefinition,
)
from app.resolution_engine.domain.enums import (
    AnalysisStatus,
    ComponentKind,
    RevalidationStatus,
    SimulationStatus,
)
from app.resolution_engine.domain.value_objects import (
    ComponentKey,
    DefinitionVersion,
    ResolutionType,
)
from app.resolution_integrations.certificates.contracts import (
    CertificateFactsReader,
)
from app.resolution_integrations.certificates.domain import (
    RELEASED_STATUSES,
    CertificateAuthorizationRequirements,
    CertificateResolutionAnalysis,
    CertificateResolutionContext,
    CertificateResolutionPlan,
    CertificateResolutionPlanStep,
    CertificateResolutionRequest,
    CertificateResolutionRevalidation,
    CertificateResolutionSimulation,
    CertificateResolutionStrategy,
    CertificateResolutionStrategyKey,
)


CERTIFICATE_RESOLUTION_TYPE = ResolutionType(
    "certificate.resolve_incorrect_release"
)
CERTIFICATE_RESOLUTION_VERSION = DefinitionVersion("1.0")
WITHDRAW_OPERATION = "certificates.withdraw_incorrect_release"
RESTORE_OPERATION = "certificates.restore_incorrect_release_visibility"


class CertificateContextProvider:
    component_key = ComponentKey(
        "certificates.incorrect_release.context"
    )
    component_version = CERTIFICATE_RESOLUTION_VERSION

    def __init__(self, reader: CertificateFactsReader) -> None:
        self._reader = reader

    def build_context(
        self,
        request: CertificateResolutionRequest,
        /,
    ) -> CertificateResolutionContext:
        return CertificateResolutionContext(
            facts=self._reader.read(request.certificate_id),
            reason=request.reason.strip(),
        )


class CertificateIncorrectReleaseAnalyzer:
    component_key = ComponentKey(
        "certificates.incorrect_release.analyzer"
    )
    component_version = CERTIFICATE_RESOLUTION_VERSION

    def analyze(
        self,
        context: CertificateResolutionContext,
        /,
    ) -> CertificateResolutionAnalysis:
        facts = context.facts
        if not facts.is_active:
            status = AnalysisStatus.BLOCKED
            reasons = ("certificate_inactive",)
        elif facts.status not in RELEASED_STATUSES:
            status = AnalysisStatus.BLOCKED
            reasons = ("certificate_not_released",)
        elif not facts.client_visible:
            status = AnalysisStatus.ALREADY_RESOLVED
            reasons = ("client_access_already_withdrawn",)
        else:
            status = AnalysisStatus.RESOLVABLE
            reasons = ("incorrect_release_can_be_withdrawn",)
        return CertificateResolutionAnalysis(
            status=status,
            reason_codes=reasons,
            context_hash=context.context_hash,
        )


class CertificateIncorrectReleaseStrategySelector:
    component_key = ComponentKey(
        "certificates.incorrect_release.strategy"
    )
    component_version = CERTIFICATE_RESOLUTION_VERSION

    def select_strategy(
        self,
        *,
        context: CertificateResolutionContext,
        analysis: CertificateResolutionAnalysis,
    ) -> CertificateResolutionStrategy:
        if analysis.status is AnalysisStatus.ALREADY_RESOLVED:
            return CertificateResolutionStrategy(
                key=CertificateResolutionStrategyKey.NO_ACTION,
                rationale="El acceso futuro ya se encuentra retirado.",
            )
        return CertificateResolutionStrategy(
            key=(
                CertificateResolutionStrategyKey.WITHDRAW_CLIENT_ACCESS
            ),
            rationale=(
                "Retirar visibilidad sin alterar la liberación histórica."
            ),
        )


class CertificateIncorrectReleasePlanBuilder:
    component_key = ComponentKey(
        "certificates.incorrect_release.plan"
    )
    component_version = CERTIFICATE_RESOLUTION_VERSION

    def build_plan(
        self,
        *,
        context: CertificateResolutionContext,
        analysis: CertificateResolutionAnalysis,
        strategy: CertificateResolutionStrategy,
    ) -> CertificateResolutionPlan:
        if not analysis.is_resolvable:
            return CertificateResolutionPlan(
                context_hash=context.context_hash,
                strategy=strategy,
                steps=(),
                blockers=analysis.reason_codes,
            )
        facts = context.facts
        return CertificateResolutionPlan(
            context_hash=context.context_hash,
            strategy=strategy,
            steps=(
                CertificateResolutionPlanStep(
                    step_key="withdraw_client_access",
                    operation_key=WITHDRAW_OPERATION,
                    owner_module="certificates",
                    input_payload={
                        "certificate_id": facts.certificate_id,
                        "expected_status": facts.status,
                        "reason": context.reason,
                    },
                    compensation_operation_key=RESTORE_OPERATION,
                    compensation_payload={
                        "certificate_id": facts.certificate_id,
                    },
                ),
            ),
        )


class CertificateIncorrectReleaseSimulator:
    component_key = ComponentKey(
        "certificates.incorrect_release.simulator"
    )
    component_version = CERTIFICATE_RESOLUTION_VERSION

    def simulate(
        self,
        *,
        context: CertificateResolutionContext,
        plan: CertificateResolutionPlan,
    ) -> CertificateResolutionSimulation:
        blockers = plan.blockers
        return CertificateResolutionSimulation(
            status=(
                SimulationStatus.BLOCKED
                if blockers
                else SimulationStatus.VALID
            ),
            plan_hash=plan.plan_hash,
            impacts=(
                ("client_visible:true→false",)
                if not blockers
                else ()
            ),
            preserved_evidence=(
                "certificate.status",
                "certificate.released_on",
                "certificate.released_to_client_at",
                "certificate.released_to_client_by_id",
                "certificate.authenticated_pdf_path",
            ),
            blockers=blockers,
        )


class CertificateIncorrectReleaseAuthorizationPolicy:
    component_key = ComponentKey(
        "certificates.incorrect_release.authorization"
    )
    component_version = CERTIFICATE_RESOLUTION_VERSION

    def authorization_requirements(
        self,
        *,
        context: CertificateResolutionContext,
        plan: CertificateResolutionPlan,
        simulation: CertificateResolutionSimulation,
    ) -> CertificateAuthorizationRequirements:
        return CertificateAuthorizationRequirements(
            required_permissions=(
                "certificates.approve",
                "certificates.release",
            ),
            required_functions=("quality", "release_management"),
            plan_hash=plan.plan_hash,
        )


class CertificateIncorrectReleaseRevalidator:
    component_key = ComponentKey(
        "certificates.incorrect_release.revalidator"
    )
    component_version = CERTIFICATE_RESOLUTION_VERSION

    def revalidate(
        self,
        *,
        authorized_context: CertificateResolutionContext,
        current_context: CertificateResolutionContext,
        plan: CertificateResolutionPlan,
        simulation: CertificateResolutionSimulation,
    ) -> CertificateResolutionRevalidation:
        if authorized_context.context_hash == current_context.context_hash:
            return CertificateResolutionRevalidation(
                status=RevalidationStatus.VALID,
                authorized_context_hash=(
                    authorized_context.context_hash
                ),
                current_context_hash=current_context.context_hash,
                reason_codes=("certificate_context_unchanged",),
            )
        return CertificateResolutionRevalidation(
            status=RevalidationStatus.REQUIRES_NEW_PLAN,
            authorized_context_hash=authorized_context.context_hash,
            current_context_hash=current_context.context_hash,
            reason_codes=("certificate_context_changed",),
        )


COMPONENT_IMPLEMENTATIONS = {
    ComponentKind.CONTEXT_PROVIDER: CertificateContextProvider,
    ComponentKind.ANALYZER: CertificateIncorrectReleaseAnalyzer,
    ComponentKind.STRATEGY_SELECTOR: (
        CertificateIncorrectReleaseStrategySelector
    ),
    ComponentKind.PLAN_BUILDER: CertificateIncorrectReleasePlanBuilder,
    ComponentKind.SIMULATOR: CertificateIncorrectReleaseSimulator,
    ComponentKind.AUTHORIZATION_POLICY: (
        CertificateIncorrectReleaseAuthorizationPolicy
    ),
    ComponentKind.REVALIDATOR: CertificateIncorrectReleaseRevalidator,
}


def build_certificate_resolution_definition() -> ResolutionDefinition:
    return ResolutionDefinition(
        resolution_type=CERTIFICATE_RESOLUTION_TYPE,
        version=CERTIFICATE_RESOLUTION_VERSION,
        description=(
            "Retira acceso futuro a un certificado liberado incorrectamente "
            "sin reescribir la liberación histórica."
        ),
        components={
            kind: ComponentReference(
                kind=kind,
                key=implementation.component_key,
                version=CERTIFICATE_RESOLUTION_VERSION,
                implementation=implementation,
            )
            for kind, implementation in COMPONENT_IMPLEMENTATIONS.items()
        },
    )


@dataclass(frozen=True, slots=True)
class CertificateResolutionIntegration:
    definition: ResolutionDefinition
    component_resolver: object
    action_handlers: tuple[object, ...]
    compensation_handlers: tuple[object, ...]

    def register(self, registry: ResolutionRegistry) -> None:
        registry.register(self.definition)
