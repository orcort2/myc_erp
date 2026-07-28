"""Flujo administrativo guiado sobre servicios canónicos del Motor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.user import User
from app.resolution_center.actor import actor_for_user
from app.resolution_center.schemas import (
    AuthorizationRequest,
    CreateAdministrativeResolutionRequest,
    OperationAccepted,
    ResolutionDefinitionResource,
)
from app.resolution_engine.application.distribution import DistributedDispatcher
from app.resolution_engine.application.lifecycle import (
    LifecycleActor,
    ResolutionLifecycleService,
)
from app.resolution_engine.application.orchestration import ResolutionOrchestrator
from app.resolution_engine.application.registry import ResolutionRegistry
from app.resolution_engine.application.security import (
    ResolutionAuthorizationService,
    SecurityPolicyEvaluator,
)
from app.resolution_engine.contracts.execution import (
    execution_security_operation_payload,
)
from app.resolution_engine.contracts.lifecycle import (
    CreateResolutionCommand,
    ResolutionProblemInput,
    lifecycle_transition_operation_payload,
)
from app.resolution_engine.domain.canonical import canonical_sha256
from app.resolution_engine.domain.distribution import (
    DeterministicRetryPolicy,
    DistributedWorkKind,
    DistributedWorkRequest,
)
from app.resolution_engine.domain.enums import (
    ResolutionPriority,
    ResolutionSource,
)
from app.resolution_engine.domain.lifecycle import (
    LifecycleAction,
    ResolutionStateMachine,
)
from app.resolution_engine.domain.security import (
    SecurityDecisionOutcome,
    SecurityDecisionUseMode,
    SecurityRequest,
    SecurityResource,
)
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.distribution import (
    SqlAlchemyDistributedWorkStore,
)
from app.resolution_engine.infrastructure.lifecycle import SqlAlchemyLifecycleStore
from app.resolution_engine.infrastructure.persistence import (
    Resolution,
    ResolutionAnalysis,
    ResolutionAuthorizationDecision,
    ResolutionAuthorizationRequest,
    ResolutionContextSnapshot,
    ResolutionPlan,
    ResolutionPlanStep,
    ResolutionRevalidation,
    ResolutionSecurityDecision,
    ResolutionSimulation,
    ResolutionStrategySelection,
    ResolutionWorkItem,
)
from app.resolution_engine.infrastructure.runtime import (
    SystemClock,
    UuidIdentifierFactory,
)
from app.resolution_engine.infrastructure.security import (
    SqlAlchemySecurityEvidenceStore,
    SqlAlchemySecurityResourceVerifier,
)
from app.resolution_integrations.certificates import (
    CERTIFICATE_RESOLUTION_TYPE,
    build_certificate_resolution_integration,
)
from app.resolution_integrations.certificates.domain import (
    CertificateFacts,
    CertificateResolutionContext,
    CertificateResolutionRequest,
)
from app.services.auth import user_has_permission


class ResolutionCenterWorkflowError(ValueError):
    def __init__(self, code: str, message: str, *, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class ResolutionCenterWorkflowService:
    """Único compositor del flujo web; routers sólo traducen HTTP."""

    def __init__(
        self,
        session: Session,
        *,
        organization_id: str | None = None,
        session_factory: Callable[[], Session] = SessionLocal,
        integration=None,
    ) -> None:
        self._session = session
        self._organization_id = (
            organization_id or settings.resolution_center_organization_id
        )
        self._clock = SystemClock()
        self._session_factory = session_factory
        self._registry = ResolutionRegistry()
        self._integration = integration or build_certificate_resolution_integration(
            session_factory
        )
        self._integration.register(self._registry)
        self._orchestrator = ResolutionOrchestrator(
            registry=self._registry,
            components=self._integration.component_resolver,
        )

    def definitions(self) -> tuple[ResolutionDefinitionResource, ...]:
        definition = self._registry.resolve(
            str(CERTIFICATE_RESOLUTION_TYPE),
            "1.0",
        )
        return (
            ResolutionDefinitionResource(
                resolution_type=str(definition.resolution_type),
                version=str(definition.version),
                name="Retiro de certificado liberado incorrectamente",
                description=definition.description,
                domain="certificates",
                object_type="certificate",
                object_route="/dashboard#certificados",
                capabilities=(
                    "context",
                    "analysis",
                    "plan",
                    "simulation",
                    "authorization",
                    "distributed_execution",
                    "compensation",
                ),
                required_permissions=(
                    "certificates.approve",
                    "certificates.release",
                ),
                parameter_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["reason"],
                    "properties": {
                        "reason": {
                            "type": "string",
                            "title": "Motivo",
                            "minLength": 1,
                            "maxLength": 2000,
                        }
                    },
                },
                warnings=(
                    "Retira visibilidad futura sin reescribir la liberación histórica.",
                ),
            ),
        )

    def create(
        self,
        payload: CreateAdministrativeResolutionRequest,
        *,
        user: User,
        idempotency_key: str,
        correlation_id: str | None,
    ) -> OperationAccepted:
        actor = actor_for_user(
            user,
            organization_id=self._organization_id,
            correlation_id=correlation_id,
        )
        definition = self._registry.resolve(
            payload.resolution_type,
            payload.definition_version,
        )
        self._validate_parameters(payload)
        request_key = (
            f"resolution-center:{self._organization_id}:"
            f"{user.id}:{idempotency_key}"
        )
        existing = self._session.scalar(
            select(Resolution).where(Resolution.request_key == request_key)
        )
        request_hash = canonical_sha256(payload.model_dump(mode="json"))
        if existing:
            if existing.metadata_json.get("center_request_hash") != request_hash:
                raise ResolutionCenterWorkflowError(
                    "idempotency_conflict",
                    "La clave ya fue utilizada con otra solicitud.",
                    status_code=409,
                )
            return self._accepted(existing, "Resolución existente recuperada")
        problem = ResolutionProblemInput(
            problem_code="administrative_resolution",
            summary=payload.title,
            description=payload.description,
            detected_by=actor.identity.actor_id,
            detected_at=self._clock.now(),
            severity=ResolutionPriority(payload.priority),
            source_payload={
                "parameters": payload.parameters,
                "origin": "resolution_center",
            },
            external_reference=payload.subject_id,
        )
        provisional = CreateResolutionCommand(
            resolution_type=payload.resolution_type,
            definition_version=payload.definition_version,
            source=ResolutionSource.ADMINISTRATOR,
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            title=payload.title,
            description=payload.description,
            reason=payload.reason,
            priority=ResolutionPriority(payload.priority),
            requires_authorization=True,
            problem=problem,
            actor=actor,
            security_decision_id=1,
            request_key=request_key,
            metadata={
                "center_request_hash": request_hash,
                "parameters": payload.parameters,
                "subject_label": None,
                "subject_route": "/dashboard#certificados",
            },
        )
        decision_id = self._authorize(
            actor=actor,
            action="resolution.create",
            resource=SecurityResource(
                resource_type="resolution_definition",
                resource_id=(
                    f"{definition.resolution_type}@{definition.version}"
                ),
                organization_id=self._organization_id,
            ),
            operation_id=request_key,
            operation_payload=provisional.security_operation_payload(definition),
            context={"source": provisional.source.value},
        )
        command = replace(provisional, security_decision_id=decision_id)
        lifecycle = self._lifecycle().create(command)
        self._session.commit()
        root = self._session.get(Resolution, lifecycle.resolution_id)
        assert root is not None
        return self._accepted(root, "Resolución administrativa creada")

    def prepare_context(
        self,
        public_id: str,
        *,
        user: User,
        correlation_id: str | None,
    ) -> OperationAccepted:
        root, actor = self._root_and_actor(public_id, user, correlation_id)
        self._expect(root, "draft")
        request = self._domain_request(root)
        context = self._orchestrator.build_context(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            request=request,
        )
        snapshot = context.snapshot()
        self._authorize_stage(
            root,
            actor,
            action="resolution.context.build",
            payload={"request": self._request_snapshot(request)},
        )
        row = ResolutionContextSnapshot(
            resolution_id=root.id,
            snapshot_type="initial",
            sequence=self._next_sequence(ResolutionContextSnapshot, root.id),
            context_version=root.definition_version,
            context_hash=context.context_hash,
            schema_version="1.0",
            captured_at=self._clock.now(),
            captured_by_actor_id=actor.identity.actor_id,
            captured_by_actor=actor.snapshot(),
            facts=snapshot,
            source_references=[
                {
                    "subject_type": root.subject_type,
                    "subject_id": root.subject_id,
                }
            ],
        )
        self._session.add(row)
        self._session.flush()
        root.current_context_snapshot_id = row.id
        facts = snapshot.get("facts", {})
        if facts.get("folio"):
            root.metadata_json = {
                **root.metadata_json,
                "subject_label": facts["folio"],
            }
        self._transition(root, actor, LifecycleAction.RECORD_CONTEXT)
        self._session.commit()
        return self._accepted(root, "Contexto preparado")

    def analyze(
        self,
        public_id: str,
        *,
        user: User,
        correlation_id: str | None,
    ) -> OperationAccepted:
        root, actor = self._root_and_actor(public_id, user, correlation_id)
        self._expect(root, "context_ready")
        context = self._current_context(root)
        analysis = self._orchestrator.analyze(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=context,
        )
        self._authorize_stage(
            root,
            actor,
            action="resolution.analyze",
            payload={"context_hash": context.context_hash},
        )
        snapshot = analysis.snapshot()
        row = ResolutionAnalysis(
            resolution_id=root.id,
            context_snapshot_id=root.current_context_snapshot_id,
            analysis_version=self._next_sequence(ResolutionAnalysis, root.id),
            is_resolvable=analysis.is_resolvable,
            status=analysis.status.value,
            findings=list(analysis.reason_codes),
            blockers=(
                [] if analysis.is_resolvable else list(analysis.reason_codes)
            ),
            available_strategies=(
                ["withdraw_client_access"] if analysis.is_resolvable else []
            ),
            analyzed_at=self._clock.now(),
            analyzed_by=actor.identity.actor_id,
            analysis_hash=canonical_sha256(snapshot),
        )
        self._session.add(row)
        self._session.flush()
        self._transition(root, actor, LifecycleAction.RECORD_ANALYSIS)
        self._session.commit()
        return self._accepted(root, "Análisis confirmado")

    def build_plan(
        self,
        public_id: str,
        *,
        user: User,
        correlation_id: str | None,
    ) -> OperationAccepted:
        root, actor = self._root_and_actor(public_id, user, correlation_id)
        self._expect(root, "analyzed")
        context = self._current_context(root)
        analysis = self._current_analysis(root, context)
        strategy, plan = self._orchestrator.build_plan(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=context,
            analysis=analysis,
        )
        if plan.blockers:
            raise ResolutionCenterWorkflowError(
                "plan_blocked",
                "El Motor no pudo construir un plan ejecutable.",
            )
        preview_simulation = self._orchestrator.simulate(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=context,
            plan=plan,
        )
        requirements = self._orchestrator.authorization_requirements(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=context,
            plan=plan,
            simulation=preview_simulation,
        )
        self._authorize_stage(
            root,
            actor,
            action="resolution.strategy.select",
            payload={
                "context_hash": context.context_hash,
                "analysis": analysis.snapshot(),
                "strategy": strategy.snapshot(),
            },
        )
        self._authorize_stage(
            root,
            actor,
            action="resolution.plan.build",
            payload={
                "context_hash": context.context_hash,
                "analysis": analysis.snapshot(),
            },
        )
        analysis_row = self._latest_analysis(root.id)
        strategy_row = ResolutionStrategySelection(
            resolution_id=root.id,
            analysis_id=analysis_row.id,
            strategy_key=strategy.key.value,
            strategy_version=root.definition_version,
            selection_mode="automatic",
            selected_by_actor_id=actor.identity.actor_id,
            selected_at=self._clock.now(),
            justification=strategy.rationale,
            is_active=True,
        )
        self._session.add(strategy_row)
        self._session.flush()
        plan_row = ResolutionPlan(
            resolution_id=root.id,
            strategy_selection_id=strategy_row.id,
            context_snapshot_id=root.current_context_snapshot_id,
            version=1,
            schema_version="1.0",
            status="ready",
            summary="Retirar acceso futuro al certificado",
            rationale=strategy.rationale,
            expected_impact={"changes": ["client_visible:true→false"]},
            preserved_entities=[
                "certificate.status",
                "certificate.release_history",
            ],
            blockers=list(plan.blockers),
            authorization_requirements=requirements.snapshot(),
            plan_hash=plan.plan_hash,
            created_by_actor_id=actor.identity.actor_id,
            activated_at=self._clock.now(),
            is_active=True,
        )
        self._session.add(plan_row)
        self._session.flush()
        for sequence, step in enumerate(plan.steps, start=1):
            snapshot = step.snapshot()
            self._session.add(
                ResolutionPlanStep(
                    plan_id=plan_row.id,
                    step_key=step.step_key,
                    sequence=sequence,
                    operation_key=step.operation_key,
                    owner_module=step.owner_module,
                    description="Retirar visibilidad futura del certificado",
                    input_payload=step.input_payload,
                    expected_output={"client_visible": False},
                    criticality="high",
                    retry_policy={"mode": "distributed_deterministic"},
                    is_compensable=True,
                    compensation_operation_key=step.compensation_operation_key,
                    compensation_payload=step.compensation_payload,
                    step_hash=canonical_sha256(snapshot),
                )
            )
        root.current_strategy_selection_id = strategy_row.id
        root.current_plan_id = plan_row.id
        self._session.flush()
        self._transition(root, actor, LifecycleAction.RECORD_PLAN)
        self._session.commit()
        return self._accepted(root, "Plan construido")

    def simulate(
        self,
        public_id: str,
        *,
        user: User,
        correlation_id: str | None,
    ) -> OperationAccepted:
        root, actor = self._root_and_actor(public_id, user, correlation_id)
        self._expect(root, "plan_ready")
        context = self._current_context(root)
        analysis = self._current_analysis(root, context)
        _, plan = self._orchestrator.build_plan(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=context,
            analysis=analysis,
        )
        simulation = self._orchestrator.simulate(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=context,
            plan=plan,
        )
        requirements = self._orchestrator.authorization_requirements(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=context,
            plan=plan,
            simulation=simulation,
        )
        plan_row = self._session.get(ResolutionPlan, root.current_plan_id)
        assert plan_row is not None
        self._authorize_stage(
            root,
            actor,
            action="resolution.simulate",
            payload={"plan_id": plan_row.id, "plan_hash": plan_row.plan_hash},
            plan=plan_row,
        )
        simulation_snapshot = simulation.snapshot()
        row = ResolutionSimulation(
            resolution_id=root.id,
            plan_id=plan_row.id,
            context_snapshot_id=root.current_context_snapshot_id,
            simulation_version=1,
            status=simulation.status.value,
            is_valid=simulation.status.value in {"valid", "valid_with_warnings"},
            expected_actions=[
                step.snapshot() for step in plan.steps
            ],
            expected_changes=list(simulation.impacts),
            preserved_entities=list(simulation.preserved_evidence),
            blockers=list(simulation.blockers),
            required_authorizations=requirements.snapshot(),
            simulation_hash=canonical_sha256(simulation_snapshot),
            simulated_at=self._clock.now(),
            simulated_by=actor.identity.actor_id,
        )
        self._session.add(row)
        plan_row.status = "simulated"
        self._session.flush()
        self._transition(root, actor, LifecycleAction.RECORD_SIMULATION)
        self._session.commit()
        return self._accepted(root, "Simulación completada")

    def authorize(
        self,
        public_id: str,
        payload: AuthorizationRequest,
        *,
        user: User,
        correlation_id: str | None,
    ) -> OperationAccepted:
        root, actor = self._root_and_actor(public_id, user, correlation_id)
        if root.status not in {"simulated", "pending_authorization"}:
            self._expect(root, "simulated")
        plan = self._session.get(ResolutionPlan, root.current_plan_id)
        simulation = self._latest_simulation(root.id)
        assert plan is not None and simulation is not None
        missing_permissions = [
            permission
            for permission in plan.authorization_requirements.get(
                "required_permissions", ()
            )
            if not user_has_permission(user, permission)
        ]
        if missing_permissions:
            raise ResolutionCenterWorkflowError(
                "authorization_requirements_missing",
                "Faltan permisos requeridos por la definición: "
                + ", ".join(missing_permissions),
                status_code=403,
            )
        request = self._session.scalar(
            select(ResolutionAuthorizationRequest)
            .where(
                ResolutionAuthorizationRequest.resolution_id == root.id,
                ResolutionAuthorizationRequest.plan_id == plan.id,
            )
            .order_by(ResolutionAuthorizationRequest.id.desc())
        )
        if request is None:
            request = ResolutionAuthorizationRequest(
                resolution_id=root.id,
                plan_id=plan.id,
                simulation_id=simulation.id,
                policy_key="resolution.center.administrative",
                policy_version="1.0",
                status="pending",
                requested_by_actor_id=root.requested_by_actor_id
                or actor.identity.actor_id,
                requester_actor_snapshot=actor.snapshot(),
                requested_at=self._clock.now(),
                required_approvals=1,
                authorization_scope={
                    "organization_id": self._organization_id,
                    "resolution_id": root.id,
                },
                plan_hash=plan.plan_hash,
                simulation_hash=simulation.simulation_hash,
            )
            self._session.add(request)
            self._session.flush()
            self._transition(
                root,
                actor,
                LifecycleAction.REQUEST_AUTHORIZATION,
            )
        operation_payload = {
            "resolution_id": root.id,
            "plan_id": plan.id,
            "plan_version": plan.version,
            "plan_hash": plan.plan_hash,
            "simulation_id": simulation.id,
            "simulation_hash": simulation.simulation_hash,
            "authorization_request_id": request.id,
        }
        self._authorize(
            actor=actor,
            action="resolution.plan.authorize",
            resource=SecurityResource(
                resource_type="resolution_plan",
                resource_id=str(plan.id),
                organization_id=self._organization_id,
                resolution_id=root.id,
                resolution_public_id=root.public_id,
                plan_id=plan.id,
                plan_version=plan.version,
                plan_hash=plan.plan_hash,
                simulation_id=simulation.id,
                simulation_hash=simulation.simulation_hash,
                authorization_request_id=request.id,
            ),
            operation_id=f"center:authorize:{root.public_id}:{request.id}",
            operation_payload=operation_payload,
        )
        prior = self._session.scalar(
            select(ResolutionAuthorizationDecision).where(
                ResolutionAuthorizationDecision.authorization_request_id
                == request.id,
                ResolutionAuthorizationDecision.approver_actor_id
                == actor.identity.actor_id,
            )
        )
        if prior is None:
            self._session.add(
                ResolutionAuthorizationDecision(
                    authorization_request_id=request.id,
                    decision="approved",
                    approver_actor_id=actor.identity.actor_id,
                    approver_actor_type=actor.identity.actor_type.value,
                    approver_function="resolution_authorizer",
                    decided_at=self._clock.now(),
                    comment=payload.comment,
                    permission_snapshot={
                        "permissions": [
                            str(item.permission) for item in actor.permissions
                        ]
                    },
                    actor_snapshot=actor.snapshot(),
                )
            )
        request.status = "approved"
        plan.status = "authorized"
        self._session.flush()
        self._transition(root, actor, LifecycleAction.CONFIRM_AUTHORIZATION)
        self._transition(root, actor, LifecycleAction.BEGIN_REVALIDATION)
        revalidation_valid = self._revalidate(
            root,
            actor,
            plan,
            simulation,
        )
        self._session.commit()
        if not revalidation_valid:
            raise ResolutionCenterWorkflowError(
                "revalidation_requires_new_plan",
                "El contexto cambió y se requiere un plan nuevo.",
                status_code=409,
            )
        return self._accepted(root, "Resolución autorizada y revalidada")

    def execute(
        self,
        public_id: str,
        *,
        user: User,
        idempotency_key: str,
        correlation_id: str | None,
    ) -> OperationAccepted:
        root, actor = self._root_and_actor(public_id, user, correlation_id)
        self._expect(root, "ready_for_execution")
        work_key = f"center:execution:{self._organization_id}:{root.public_id}"
        existing_work = self._session.scalar(
            select(ResolutionWorkItem).where(
                ResolutionWorkItem.work_key == work_key
            )
        )
        if existing_work is not None:
            return OperationAccepted(
                public_id=root.public_id,
                lifecycle_status=root.status,
                distributed_status=existing_work.status,
                work_key=work_key,
                message="Resolución aceptada para ejecución",
            )
        plan = self._session.get(ResolutionPlan, root.current_plan_id)
        revalidation = self._session.scalar(
            select(ResolutionRevalidation)
            .where(ResolutionRevalidation.resolution_id == root.id)
            .order_by(ResolutionRevalidation.id.desc())
        )
        assert plan is not None and revalidation is not None
        operation_id = (
            f"center:execute:{self._organization_id}:{root.public_id}:"
            f"{idempotency_key}"
        )
        operation_payload = execution_security_operation_payload(
            resolution_id=root.id,
            plan_id=plan.id,
            plan_version=plan.version,
            plan_hash=plan.plan_hash,
            revalidation_id=revalidation.id,
            revalidation_hash=revalidation.revalidation_hash,
            actor_id=actor.identity.actor_id,
            organization_id=self._organization_id,
        )
        decision_id = self._authorize(
            actor=actor,
            action="resolution.execute",
            resource=SecurityResource(
                resource_type="resolution_plan",
                resource_id=str(plan.id),
                organization_id=self._organization_id,
                resolution_id=root.id,
                resolution_public_id=root.public_id,
                plan_id=plan.id,
                plan_version=plan.version,
                plan_hash=plan.plan_hash,
                revalidation_id=revalidation.id,
                revalidation_hash=revalidation.revalidation_hash,
            ),
            operation_id=operation_id,
            operation_payload=operation_payload,
        )
        # La decisión debe ser visible para cualquier worker antes de publicar
        # el trabajo en la cola, que usa deliberadamente otra sesión corta.
        self._session.commit()
        request = DistributedWorkRequest(
            work_key=work_key,
            resolution_id=root.id,
            organization_id=self._organization_id,
            kind=DistributedWorkKind.EXECUTION,
            payload={
                "resolution_id": root.id,
                "idempotency_key": operation_id,
                "security_decision_id": decision_id,
                "actor": actor.snapshot(),
                "lock_owner": "resolution-center-worker",
                "lock_ttl_seconds": 300,
            },
            correlation_id=actor.authentication.correlation_id,
            priority={"low": -10, "normal": 0, "high": 50, "critical": 100}[
                root.priority
            ],
            retry_policy=DeterministicRetryPolicy(
                max_attempts=5,
                base_delay=timedelta(seconds=5),
                maximum_delay=timedelta(minutes=5),
            ),
        )
        item = DistributedDispatcher(
            store=SqlAlchemyDistributedWorkStore(self._session_factory),
            clock=self._clock,
        ).enqueue(request)
        return OperationAccepted(
            public_id=root.public_id,
            lifecycle_status=root.status,
            distributed_status=item.status.value,
            work_key=work_key,
            message="Resolución aceptada para ejecución",
        )

    def _revalidate(
        self,
        root: Resolution,
        actor,
        plan: ResolutionPlan,
        simulation: ResolutionSimulation,
    ) -> bool:
        authorized_context_row = self._session.get(
            ResolutionContextSnapshot,
            root.current_context_snapshot_id,
        )
        authorized_context = self._current_context(root)
        current_context = self._orchestrator.build_context(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            request=self._domain_request(root),
        )
        _, domain_plan = self._orchestrator.build_plan(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=authorized_context,
            analysis=self._current_analysis(root, authorized_context),
        )
        domain_simulation = self._orchestrator.simulate(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=authorized_context,
            plan=domain_plan,
        )
        result = self._orchestrator.revalidate(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            authorized_context=authorized_context,
            current_context=current_context,
            plan=domain_plan,
            simulation=domain_simulation,
        )
        self._authorize_stage(
            root,
            actor,
            action="resolution.revalidate",
            payload={
                "plan_id": plan.id,
                "authorized_context_hash": authorized_context.context_hash,
                "current_context_hash": current_context.context_hash,
            },
            plan=plan,
        )
        current_row = ResolutionContextSnapshot(
            resolution_id=root.id,
            snapshot_type="revalidation",
            sequence=self._next_sequence(ResolutionContextSnapshot, root.id),
            context_version=root.definition_version,
            context_hash=current_context.context_hash,
            schema_version="1.0",
            captured_at=self._clock.now(),
            captured_by_actor_id=actor.identity.actor_id,
            captured_by_actor=actor.snapshot(),
            facts=current_context.snapshot(),
        )
        self._session.add(current_row)
        self._session.flush()
        revalidation = ResolutionRevalidation(
            resolution_id=root.id,
            plan_id=plan.id,
            previous_context_snapshot_id=authorized_context_row.id,
            current_context_snapshot_id=current_row.id,
            status=result.status.value,
            changed_facts=(
                []
                if result.is_valid
                else list(result.reason_codes)
            ),
            invalidating_changes=(
                [] if result.is_valid else list(result.reason_codes)
            ),
            result=result.snapshot(),
            revalidated_at=self._clock.now(),
            revalidated_by=actor.identity.actor_id,
            validator_version=root.definition_version,
            revalidation_hash=canonical_sha256(result.snapshot()),
        )
        self._session.add(revalidation)
        root.current_context_snapshot_id = current_row.id
        self._session.flush()
        if not result.is_valid:
            self._transition(
                root,
                actor,
                LifecycleAction.REQUIRE_NEW_PLAN,
            )
            return False
        self._transition(root, actor, LifecycleAction.ACCEPT_REVALIDATION)
        return True

    def _authorize_stage(
        self,
        root: Resolution,
        actor,
        *,
        action: str,
        payload: dict,
        plan: ResolutionPlan | None = None,
    ) -> int:
        return self._authorize(
            actor=actor,
            action=action,
            resource=SecurityResource(
                resource_type=(
                    "resolution_plan" if plan is not None else "resolution"
                ),
                resource_id=str(plan.id if plan else root.id),
                organization_id=self._organization_id,
                resolution_id=root.id,
                resolution_public_id=root.public_id,
                plan_id=plan.id if plan else None,
                plan_version=plan.version if plan else None,
                plan_hash=plan.plan_hash if plan else None,
            ),
            operation_id=f"center:{action}:{root.public_id}:{root.version}",
            operation_payload=payload,
        )

    def _authorize(
        self,
        *,
        actor,
        action: str,
        resource: SecurityResource,
        operation_id: str,
        operation_payload: dict,
        context: dict | None = None,
    ) -> int:
        request = SecurityRequest(
            actor=actor,
            action=ComponentKey(action),
            resource=resource,
            required_permissions=(ComponentKey(action),),
            use_mode=SecurityDecisionUseMode.SINGLE_OPERATION,
            operation_id=operation_id,
            operation_payload=operation_payload,
            context=context or {},
        )
        decision = ResolutionAuthorizationService(
            evaluator=SecurityPolicyEvaluator(()),
            evidence_store=SqlAlchemySecurityEvidenceStore(self._session),
            resource_verifier=SqlAlchemySecurityResourceVerifier(self._session),
            clock=self._clock,
        ).authorize(request)
        self._session.flush()
        evidence = self._session.scalar(
            select(ResolutionSecurityDecision)
            .where(
                ResolutionSecurityDecision.evidence_hash
                == decision.evidence_hash
            )
            .order_by(ResolutionSecurityDecision.id.desc())
        )
        if decision.outcome is SecurityDecisionOutcome.DENIED or evidence is None:
            raise ResolutionCenterWorkflowError(
                "authorization_denied",
                "El Motor denegó la operación solicitada.",
                status_code=403,
            )
        return evidence.id

    def _transition(
        self,
        root: Resolution,
        actor,
        action: LifecycleAction,
    ) -> None:
        metadata = {"origin": "resolution_center"}
        operation_id = (
            f"center:lifecycle:{root.public_id}:{root.version}:{action.value}"
        )
        decision_id = self._authorize(
            actor=actor,
            action="resolution.lifecycle.transition",
            resource=SecurityResource(
                resource_type="resolution",
                resource_id=str(root.id),
                organization_id=self._organization_id,
                resolution_id=root.id,
                resolution_public_id=root.public_id,
            ),
            operation_id=operation_id,
            operation_payload=lifecycle_transition_operation_payload(
                resolution_id=root.id,
                action=action.value,
                expected_state=root.status,
                expected_version=root.version,
                reason=None,
                metadata=metadata,
            ),
            context={
                "lifecycle_action": action.value,
                "expected_state": root.status,
                "expected_version": root.version,
            },
        )
        lifecycle = self._lifecycle().transition(
            root.id,
            action,
            actor=LifecycleActor(
                context=actor,
                security_decision_id=decision_id,
                operation_id=operation_id,
                actor_function="resolution_center",
            ),
            metadata=metadata,
        )
        root.status = lifecycle.status.value
        root.version = lifecycle.version
        self._session.flush()

    def _lifecycle(self) -> ResolutionLifecycleService:
        return ResolutionLifecycleService(
            registry=self._registry,
            store=SqlAlchemyLifecycleStore(self._session),
            state_machine=ResolutionStateMachine(),
            clock=self._clock,
            identifiers=UuidIdentifierFactory(),
        )

    def _root_and_actor(
        self,
        public_id: str,
        user: User,
        correlation_id: str | None,
    ):
        root = self._session.scalar(
            select(Resolution).where(
                Resolution.public_id == public_id,
                Resolution.organization_id == self._organization_id,
            )
        )
        if root is None:
            raise ResolutionCenterWorkflowError(
                "resolution_not_found",
                "Resolución no encontrada.",
                status_code=404,
            )
        return root, actor_for_user(
            user,
            organization_id=self._organization_id,
            correlation_id=correlation_id,
        )

    def _domain_request(self, root: Resolution) -> CertificateResolutionRequest:
        if root.resolution_type != str(CERTIFICATE_RESOLUTION_TYPE):
            raise ResolutionCenterWorkflowError(
                "unsupported_definition",
                "La definición no está habilitada para operación administrativa.",
            )
        parameters = root.metadata_json.get("parameters", {})
        return CertificateResolutionRequest(
            certificate_id=int(root.subject_id),
            reason=str(parameters.get("reason") or root.reason or "").strip(),
        )

    def _current_context(self, root: Resolution):
        row = self._session.get(
            ResolutionContextSnapshot,
            root.current_context_snapshot_id,
        )
        if row is None:
            raise ResolutionCenterWorkflowError(
                "context_not_found",
                "La resolución no tiene un contexto persistido.",
                status_code=409,
            )
        snapshot = row.facts
        return CertificateResolutionContext(
            facts=CertificateFacts(**snapshot["facts"]),
            reason=str(snapshot["reason"]),
        )

    def _current_analysis(self, root: Resolution, context):
        return self._orchestrator.analyze(
            resolution_type=root.resolution_type,
            definition_version=root.definition_version,
            context=context,
        )

    def _latest_analysis(self, resolution_id: int) -> ResolutionAnalysis:
        row = self._session.scalar(
            select(ResolutionAnalysis)
            .where(ResolutionAnalysis.resolution_id == resolution_id)
            .order_by(ResolutionAnalysis.analysis_version.desc())
        )
        assert row is not None
        return row

    def _latest_simulation(self, resolution_id: int) -> ResolutionSimulation:
        row = self._session.scalar(
            select(ResolutionSimulation)
            .where(ResolutionSimulation.resolution_id == resolution_id)
            .order_by(ResolutionSimulation.id.desc())
        )
        assert row is not None
        return row

    def _next_sequence(self, model, resolution_id: int) -> int:
        column = (
            model.sequence
            if hasattr(model, "sequence")
            else model.analysis_version
        )
        return (
            self._session.scalar(
                select(func.max(column)).where(
                    model.resolution_id == resolution_id
                )
            )
            or 0
        ) + 1

    @staticmethod
    def _expect(root: Resolution, expected: str) -> None:
        if root.status != expected:
            raise ResolutionCenterWorkflowError(
                "invalid_lifecycle_state",
                f"La resolución está en {root.status}; se esperaba {expected}.",
                status_code=409,
            )

    def _validate_parameters(
        self,
        payload: CreateAdministrativeResolutionRequest,
    ) -> None:
        if payload.resolution_type != str(CERTIFICATE_RESOLUTION_TYPE):
            raise ResolutionCenterWorkflowError(
                "unsupported_definition",
                "Tipo de resolución no habilitado.",
            )
        if payload.subject_type != "certificate":
            raise ResolutionCenterWorkflowError(
                "invalid_subject_type",
                "Esta definición requiere un certificado.",
            )
        if set(payload.parameters) - {"reason"}:
            raise ResolutionCenterWorkflowError(
                "unknown_parameters",
                "La solicitud contiene parámetros no declarados.",
            )
        reason = str(payload.parameters.get("reason") or payload.reason).strip()
        if not reason:
            raise ResolutionCenterWorkflowError(
                "reason_required",
                "El motivo es obligatorio.",
            )

    @staticmethod
    def _request_snapshot(request: CertificateResolutionRequest) -> dict:
        return {
            "certificate_id": request.certificate_id,
            "reason": request.reason,
        }

    @staticmethod
    def _accepted(root: Resolution, message: str) -> OperationAccepted:
        return OperationAccepted(
            public_id=root.public_id,
            lifecycle_status=root.status,
            message=message,
        )
