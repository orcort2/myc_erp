from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.resolution_engine.domain.enums import EntityRelationshipType
from app.resolution_engine.domain.execution import (
    ActionCertainty,
    DomainActionRequest,
    DomainActionResult,
    ExecutionEntityEffect,
)
from app.resolution_engine.domain.compensation import (
    CompensationActionRequest,
)
from app.resolution_engine.domain.exceptions import ComponentBindingError
from app.resolution_engine.domain.value_objects import ComponentKey
from app.resolution_engine.infrastructure.persistence import (
    ResolutionStepExecution,
)
from app.resolution_integrations.certificates.application import (
    CERTIFICATE_RESOLUTION_VERSION,
    COMPONENT_IMPLEMENTATIONS,
    RESTORE_OPERATION,
    WITHDRAW_OPERATION,
    CertificateContextProvider,
    CertificateResolutionIntegration,
    build_certificate_resolution_definition,
)
from app.resolution_integrations.certificates.contracts import (
    CertificateCommandPort,
    CertificateFactsReader,
    SourceOperationReferenceReader,
)
from app.resolution_integrations.certificates.domain import (
    CertificateFacts,
    CertificateOperationOutcome,
)
from app.services.certificate_resolution_operations import (
    CertificateOperationResult,
    CertificateResolutionOperationError,
    get_certificate_resolution_facts,
    restore_incorrect_release_visibility,
    withdraw_incorrect_release,
)


SessionFactory = Callable[[], Session]


class SqlAlchemyCertificateFactsReader:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def read(self, certificate_id: int, /) -> CertificateFacts:
        with self._session_factory() as session:
            values = get_certificate_resolution_facts(
                session,
                certificate_id,
            )
        return CertificateFacts(**values)


class SqlAlchemyCertificateCommandService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def withdraw_incorrect_release(
        self,
        **values,
    ) -> CertificateOperationOutcome:
        with self._session_factory() as session, session.begin():
            result = withdraw_incorrect_release(session, **values)
        return _operation_outcome(result)

    def restore_incorrect_release_visibility(
        self,
        **values,
    ) -> CertificateOperationOutcome:
        with self._session_factory() as session, session.begin():
            result = restore_incorrect_release_visibility(session, **values)
        return _operation_outcome(result)


class SqlAlchemySourceOperationReferenceReader:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def operation_key_for_step_execution(
        self,
        step_execution_id: int,
        /,
    ) -> str:
        with self._session_factory() as session:
            reference = session.scalar(
                select(
                    ResolutionStepExecution.domain_transaction_reference
                ).where(
                    ResolutionStepExecution.id == step_execution_id
                )
            )
        prefix = "certificate-operation:"
        if not reference or not reference.startswith(prefix):
            raise CertificateResolutionOperationError(
                "source_operation_reference_missing",
                "El checkpoint no contiene una referencia de Certificados",
            )
        return reference.removeprefix(prefix)


class CertificateIncorrectReleaseGateway:
    operation_key = ComponentKey(WITHDRAW_OPERATION)

    def __init__(self, commands: CertificateCommandPort) -> None:
        self._commands = commands

    def execute(
        self,
        request: DomainActionRequest,
        /,
    ) -> DomainActionResult:
        payload = request.step.input_payload
        try:
            result = self._commands.withdraw_incorrect_release(
                certificate_id=int(payload["certificate_id"]),
                expected_status=str(payload["expected_status"]),
                reason=str(payload["reason"]),
                actor_id=request.actor_id,
                correlation_id=request.correlation_id,
                idempotency_key=request.idempotency_key,
                request_hash=request.request_hash,
            )
        except CertificateResolutionOperationError as exc:
            return _confirmed_failure(exc)
        return _confirmed_result(result)


class CertificateIncorrectReleaseCompensationGateway:
    operation_key = ComponentKey(RESTORE_OPERATION)

    def __init__(
        self,
        commands: CertificateCommandPort,
        references: SourceOperationReferenceReader,
    ) -> None:
        self._commands = commands
        self._references = references

    def execute(
        self,
        request: CompensationActionRequest,
        /,
    ) -> DomainActionResult:
        payload = request.step.input_payload
        try:
            source_operation_key = (
                self._references.operation_key_for_step_execution(
                    request.step.source_step_execution_id
                )
            )
            result = (
                self._commands.restore_incorrect_release_visibility(
                    certificate_id=int(payload["certificate_id"]),
                    source_operation_key=source_operation_key,
                    actor_id=request.actor_id,
                    correlation_id=request.correlation_id,
                    idempotency_key=request.idempotency_key,
                    request_hash=request.request_hash,
                )
            )
        except CertificateResolutionOperationError as exc:
            return _confirmed_failure(exc)
        return _confirmed_result(result)


class CertificateComponentResolver:
    def __init__(
        self,
        *,
        facts: CertificateFactsReader,
    ) -> None:
        self._instances = {
            implementation.component_key: (
                CertificateContextProvider(facts)
                if implementation is CertificateContextProvider
                else implementation()
            )
            for implementation in COMPONENT_IMPLEMENTATIONS.values()
        }

    def resolve(self, reference, /):
        component = self._instances.get(reference.key)
        if component is None:
            raise ComponentBindingError(
                f"Certificate component not found: {reference.key}"
            )
        if (
            reference.version != CERTIFICATE_RESOLUTION_VERSION
            or not isinstance(component, reference.implementation)
        ):
            raise ComponentBindingError(
                f"Certificate component binding mismatch: {reference.key}"
            )
        return component


def build_certificate_resolution_integration(
    session_factory: SessionFactory,
) -> CertificateResolutionIntegration:
    commands = SqlAlchemyCertificateCommandService(session_factory)
    references = SqlAlchemySourceOperationReferenceReader(session_factory)
    return CertificateResolutionIntegration(
        definition=build_certificate_resolution_definition(),
        component_resolver=CertificateComponentResolver(
            facts=SqlAlchemyCertificateFactsReader(session_factory),
        ),
        action_handlers=(
            CertificateIncorrectReleaseGateway(commands),
        ),
        compensation_handlers=(
            CertificateIncorrectReleaseCompensationGateway(
                commands,
                references,
            ),
        ),
    )


def _confirmed_result(
    result: CertificateOperationOutcome,
) -> DomainActionResult:
    return DomainActionResult(
        success=True,
        certainty=ActionCertainty.CONFIRMED,
        response_payload={
            "certificate_id": result.certificate_id,
            "folio": result.folio,
            "operation_key": result.operation_key,
        },
        entity_effects=(
            ExecutionEntityEffect(
                relationship=EntityRelationshipType.MODIFIED,
                entity_type="certificate",
                entity_id=str(result.certificate_id),
                module="certificates",
                public_identifier=result.folio,
                before_snapshot=result.before_snapshot,
                after_snapshot=result.after_snapshot,
            ),
        ),
        domain_transaction_reference=(
            result.domain_transaction_reference
        ),
    )


def _confirmed_failure(
    exc: CertificateResolutionOperationError,
) -> DomainActionResult:
    return DomainActionResult(
        success=False,
        certainty=ActionCertainty.CONFIRMED,
        error_code=exc.code,
        error_message=str(exc),
    )


def _operation_outcome(
    result: CertificateOperationResult,
) -> CertificateOperationOutcome:
    return CertificateOperationOutcome(
        certificate_id=result.certificate_id,
        folio=result.folio,
        operation_key=result.operation_key,
        idempotency_key=result.idempotency_key,
        before_snapshot=result.before_snapshot,
        after_snapshot=result.after_snapshot,
        domain_transaction_reference=result.domain_transaction_reference,
    )
