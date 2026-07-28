from __future__ import annotations

from typing import Protocol

from app.resolution_integrations.certificates.domain import (
    CertificateFacts,
    CertificateOperationOutcome,
)


class CertificateFactsReader(Protocol):
    def read(self, certificate_id: int, /) -> CertificateFacts:
        """Obtiene un snapshot canónico sin efectos."""


class CertificateCommandPort(Protocol):
    def withdraw_incorrect_release(
        self,
        *,
        certificate_id: int,
        expected_status: str,
        reason: str,
        actor_id: str,
        correlation_id: str,
        idempotency_key: str,
        request_hash: str,
    ) -> CertificateOperationOutcome:
        """Ejecuta la mutación canónica exacta."""

    def restore_incorrect_release_visibility(
        self,
        *,
        certificate_id: int,
        source_operation_key: str,
        actor_id: str,
        correlation_id: str,
        idempotency_key: str,
        request_hash: str,
    ) -> CertificateOperationOutcome:
        """Compensa la operación canónica exacta."""


class SourceOperationReferenceReader(Protocol):
    def operation_key_for_step_execution(
        self,
        step_execution_id: int,
        /,
    ) -> str:
        """Resuelve la referencia propietaria confirmada de un checkpoint."""
