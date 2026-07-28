from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.models.certificate_resolution_operation import (
    CertificateResolutionOperation,
)
from app.services.audit_logs import write_audit_log


WITHDRAW_OPERATION = "certificates.withdraw_incorrect_release"
RESTORE_OPERATION = "certificates.restore_incorrect_release_visibility"
RELEASED_STATUSES = {"released_to_client", "released"}


class CertificateResolutionOperationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class CertificateOperationResult:
    certificate_id: int
    folio: str
    operation_key: str
    idempotency_key: str
    before_snapshot: dict[str, Any]
    after_snapshot: dict[str, Any]

    @property
    def domain_transaction_reference(self) -> str:
        return f"certificate-operation:{self.idempotency_key}"


def get_certificate_resolution_facts(
    db: Session,
    certificate_id: int,
) -> dict[str, Any]:
    """Snapshot canónico y read-only para Fact Providers."""

    certificate = db.get(Certificate, certificate_id)
    if certificate is None:
        raise CertificateResolutionOperationError(
            "certificate_not_found",
            "Certificado no encontrado",
        )
    return _certificate_snapshot(certificate)


def withdraw_incorrect_release(
    db: Session,
    *,
    certificate_id: int,
    expected_status: str,
    reason: str,
    actor_id: str,
    correlation_id: str,
    idempotency_key: str,
    request_hash: str,
) -> CertificateOperationResult:
    """Retira acceso futuro sin reescribir la liberación histórica."""

    _validate_common(
        actor_id=actor_id,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise CertificateResolutionOperationError(
            "reason_required",
            "La resolución exige un motivo",
        )
    request_payload = withdraw_operation_request_payload(
        certificate_id=certificate_id,
        expected_status=expected_status,
        reason=normalized_reason,
    )
    replay = _operation_replay(
        db,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        operation_key=WITHDRAW_OPERATION,
        request_payload=request_payload,
    )
    if replay is not None:
        return replay
    certificate = _locked_certificate(db, certificate_id)
    replay = _operation_replay(
        db,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        operation_key=WITHDRAW_OPERATION,
        request_payload=request_payload,
    )
    if replay is not None:
        return replay
    if certificate.status != expected_status:
        raise CertificateResolutionOperationError(
            "certificate_context_changed",
            "El estado del certificado cambió después de la revalidación",
        )
    if certificate.status not in RELEASED_STATUSES:
        raise CertificateResolutionOperationError(
            "certificate_not_released",
            "Sólo puede corregirse una liberación existente",
        )
    if not certificate.client_visible:
        raise CertificateResolutionOperationError(
            "incorrect_release_already_withdrawn",
            "El certificado ya no está visible para el cliente",
        )

    before = _certificate_snapshot(certificate)
    certificate.client_visible = False
    _stabilize_certificate(db, certificate)
    after = _certificate_snapshot(certificate)
    result = CertificateOperationResult(
        certificate_id=certificate.id,
        folio=certificate.folio,
        operation_key=WITHDRAW_OPERATION,
        idempotency_key=idempotency_key,
        before_snapshot=before,
        after_snapshot=after,
    )
    db.add(
        CertificateResolutionOperation(
            certificate_id=certificate.id,
            operation_key=WITHDRAW_OPERATION,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            actor_id=actor_id,
            correlation_id=correlation_id,
            request_payload=request_payload,
            before_snapshot=before,
            after_snapshot=after,
            result_payload=_result_payload(result),
        )
    )
    write_audit_log(
        db,
        action="certificate.incorrect_release_access_withdrawn",
        entity="certificates",
        entity_id=certificate.id,
        user_id=_integer_actor_id(actor_id),
        previous_values=before,
        new_values={
            **after,
            "resolution_operation_key": WITHDRAW_OPERATION,
            "idempotency_key": idempotency_key,
            "correlation_id": correlation_id,
        },
        comment=normalized_reason,
    )
    return result


def restore_incorrect_release_visibility(
    db: Session,
    *,
    certificate_id: int,
    source_operation_key: str,
    actor_id: str,
    correlation_id: str,
    idempotency_key: str,
    request_hash: str,
) -> CertificateOperationResult:
    """Compensa únicamente la operación exacta y sin deriva propietaria."""

    _validate_common(
        actor_id=actor_id,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    request_payload = restore_operation_request_payload(
        certificate_id=certificate_id,
        source_operation_key=source_operation_key,
    )
    replay = _operation_replay(
        db,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        operation_key=RESTORE_OPERATION,
        request_payload=request_payload,
    )
    if replay is not None:
        return replay
    certificate = _locked_certificate(db, certificate_id)
    replay = _operation_replay(
        db,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        operation_key=RESTORE_OPERATION,
        request_payload=request_payload,
    )
    if replay is not None:
        return replay
    source = db.scalar(
        select(CertificateResolutionOperation).where(
            CertificateResolutionOperation.idempotency_key
            == source_operation_key,
            CertificateResolutionOperation.certificate_id == certificate_id,
            CertificateResolutionOperation.operation_key
            == WITHDRAW_OPERATION,
        )
    )
    if source is None:
        raise CertificateResolutionOperationError(
            "source_operation_not_found",
            "No existe la operación propietaria que se pretende compensar",
        )
    expected_status = str(source.after_snapshot["status"])
    if (
        certificate.status != expected_status
        or certificate.client_visible
    ):
        raise CertificateResolutionOperationError(
            "certificate_compensation_context_changed",
            "El certificado cambió después de la operación fuente",
        )

    before = _certificate_snapshot(certificate)
    certificate.client_visible = bool(
        source.before_snapshot["client_visible"]
    )
    _stabilize_certificate(db, certificate)
    after = _certificate_snapshot(certificate)
    result = CertificateOperationResult(
        certificate_id=certificate.id,
        folio=certificate.folio,
        operation_key=RESTORE_OPERATION,
        idempotency_key=idempotency_key,
        before_snapshot=before,
        after_snapshot=after,
    )
    db.add(
        CertificateResolutionOperation(
            certificate_id=certificate.id,
            source_operation_id=source.id,
            operation_key=RESTORE_OPERATION,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            actor_id=actor_id,
            correlation_id=correlation_id,
            request_payload=request_payload,
            before_snapshot=before,
            after_snapshot=after,
            result_payload=_result_payload(result),
        )
    )
    write_audit_log(
        db,
        action="certificate.incorrect_release_access_restored",
        entity="certificates",
        entity_id=certificate.id,
        user_id=_integer_actor_id(actor_id),
        previous_values=before,
        new_values={
            **after,
            "resolution_operation_key": RESTORE_OPERATION,
            "source_operation_key": source_operation_key,
            "idempotency_key": idempotency_key,
            "correlation_id": correlation_id,
        },
        comment="Compensación gobernada por el Motor de Resoluciones",
    )
    return result


def _locked_certificate(db: Session, certificate_id: int) -> Certificate:
    certificate = db.scalar(
        select(Certificate)
        .where(Certificate.id == certificate_id)
        .with_for_update()
    )
    if certificate is None or not certificate.is_active:
        raise CertificateResolutionOperationError(
            "certificate_not_found",
            "Certificado no encontrado",
        )
    return certificate


def _operation_replay(
    db: Session,
    *,
    idempotency_key: str,
    request_hash: str,
    operation_key: str,
    request_payload: dict[str, Any],
) -> CertificateOperationResult | None:
    operation = db.scalar(
        select(CertificateResolutionOperation).where(
            CertificateResolutionOperation.idempotency_key
            == idempotency_key
        )
    )
    if operation is None:
        return None
    if (
        operation.request_hash != request_hash
        or operation.operation_key != operation_key
        or operation.request_payload != request_payload
    ):
        raise CertificateResolutionOperationError(
            "idempotency_conflict",
            "La clave idempotente ya cubre otra intención",
        )
    payload = operation.result_payload
    return CertificateOperationResult(
        certificate_id=int(payload["certificate_id"]),
        folio=str(payload["folio"]),
        operation_key=str(payload["operation_key"]),
        idempotency_key=str(payload["idempotency_key"]),
        before_snapshot=dict(payload["before_snapshot"]),
        after_snapshot=dict(payload["after_snapshot"]),
    )


def recover_confirmed_certificate_operation(
    db: Session,
    *,
    idempotency_key: str,
    request_hash: str,
    operation_key: str,
    request_payload: dict[str, Any],
) -> CertificateOperationResult | None:
    """Recupera únicamente un resultado confirmado de la intención exacta."""

    return _operation_replay(
        db,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        operation_key=operation_key,
        request_payload=request_payload,
    )


def withdraw_operation_request_payload(
    *,
    certificate_id: int,
    expected_status: str,
    reason: str,
) -> dict[str, Any]:
    """Intención propietaria canónica para ejecución y recuperación."""

    return {
        "certificate_id": certificate_id,
        "expected_status": expected_status,
        "reason": reason.strip(),
    }


def restore_operation_request_payload(
    *,
    certificate_id: int,
    source_operation_key: str,
) -> dict[str, Any]:
    """Intención propietaria canónica para compensación y recuperación."""

    return {
        "certificate_id": certificate_id,
        "source_operation_key": source_operation_key,
    }


def _stabilize_certificate(
    db: Session,
    certificate: Certificate,
) -> None:
    """Materializa y recarga valores ORM/BD antes de capturar evidencia."""

    db.flush([certificate])
    db.refresh(certificate)


def _certificate_snapshot(certificate: Certificate) -> dict[str, Any]:
    return {
        "certificate_id": certificate.id,
        "folio": certificate.folio,
        "status": certificate.status,
        "client_visible": certificate.client_visible,
        "authenticated_document_present": bool(
            certificate.authenticated_pdf_path
        ),
        "released_on": _iso(certificate.released_on),
        "released_to_client_at": _iso(
            certificate.released_to_client_at
        ),
        "released_to_client_by_id": (
            certificate.released_to_client_by_id
        ),
        "is_active": certificate.is_active,
        "updated_at": _iso(certificate.updated_at),
    }


def _result_payload(
    result: CertificateOperationResult,
) -> dict[str, Any]:
    return {
        "certificate_id": result.certificate_id,
        "folio": result.folio,
        "operation_key": result.operation_key,
        "idempotency_key": result.idempotency_key,
        "before_snapshot": result.before_snapshot,
        "after_snapshot": result.after_snapshot,
    }


def _validate_common(
    *,
    actor_id: str,
    correlation_id: str,
    idempotency_key: str,
    request_hash: str,
) -> None:
    if not actor_id.strip():
        raise CertificateResolutionOperationError(
            "actor_required",
            "La operación exige actor",
        )
    if not correlation_id.strip():
        raise CertificateResolutionOperationError(
            "correlation_required",
            "La operación exige correlación",
        )
    if not idempotency_key.strip():
        raise CertificateResolutionOperationError(
            "idempotency_key_required",
            "La operación exige clave idempotente",
        )
    if len(request_hash) != 64:
        raise CertificateResolutionOperationError(
            "request_hash_invalid",
            "La operación exige un hash canónico",
        )


def _integer_actor_id(actor_id: str) -> int | None:
    try:
        return int(actor_id)
    except ValueError:
        return None


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None
