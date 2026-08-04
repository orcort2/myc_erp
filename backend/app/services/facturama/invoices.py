"""Sandbox CFDI issuance, reconciliation and document recovery.

The critical invariant is that a response received from the PAC is persisted
before it is interpreted.  A CFDI must never be re-issued merely because a
partial, malformed or timed-out response left the local state uncertain.
"""
import base64
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.invoice import FacturamaInvoiceAttempt, Invoice, InvoiceSettings
from app.services.audit_logs import write_audit_log
from app.services.facturama.client import FacturamaClient, response_diagnostics
from app.services.facturama.exceptions import FacturamaError, FacturamaProviderResponseError
from app.services.facturama.health import FacturamaHealthService
from app.services.facturama.invoice_mapper import InvoiceValidationError, map_invoice
from app.services.file_security import POLICIES, validate_content, validate_xml
from app.services.storage_service import atomic_write, build_storage_path, relative_storage_path, require_deliverable_file


# Only ``issue_rejected`` represents a confirmed 4xx rejection and may be
# retried. Older ambiguous failures remain blocked until reconciled manually.
ISSUE_BLOCKING_STATUSES = {"issuing", "issue_unknown", "issued", "issue_failed"}
RECONCILIATION_WINDOW = timedelta(minutes=15)
FACTURAMA_TIMEZONE = ZoneInfo("America/Mexico_City")


def _error(code: str, detail: str, status: int = 409, fields: list | None = None, provider_status: int | None = None, provider_detail: str | None = None):
    body = {"detail": detail, "code": code}
    if fields:
        body["fields"] = fields
    if provider_status is not None:
        body["provider_status"] = provider_status
    if provider_detail:
        body["provider_detail"] = provider_detail
    raise HTTPException(status_code=status, detail=body)


def _find_response_value(payload: Any, *names: str) -> Any:
    """Find a non-empty provider field even when it is nested in a wrapper."""
    expected = {name.lower() for name in names}
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in expected and value not in (None, ""):
                return value
        for value in payload.values():
            found = _find_response_value(value, *names)
            if found not in (None, ""):
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_response_value(value, *names)
            if found not in (None, ""):
                return found
    return None


def _parse_provider_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=FACTURAMA_TIMEZONE)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Facturama's Date is expressed in the local time of ExpeditionPlace.
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=FACTURAMA_TIMEZONE)


def _provider_response_snapshot(error: FacturamaProviderResponseError) -> dict:
    return {
        "status_code": error.status_code,
        "text": error.response_text,
        "headers": error.response_headers,
        "json": error.response_json,
    }


def _provider_detail(error: FacturamaProviderResponseError) -> str:
    payload = error.response_json
    if isinstance(payload, dict):
        for key in ("detail", "Detail", "message", "Message", "error", "Error"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return error.response_text.strip() or "Facturama no proporcionó detalle adicional."


def _persist_response(invoice: Invoice, attempt: FacturamaInvoiceAttempt, response_snapshot: dict) -> None:
    """Persist the raw, sanitized PAC response before business interpretation."""
    status_code = response_snapshot["status_code"]
    invoice.facturama_http_status = status_code
    invoice.facturama_response_json = response_snapshot
    attempt.http_status = status_code
    attempt.response_json = response_snapshot


def _mark_unknown(db: Session, invoice: Invoice, attempt: FacturamaInvoiceAttempt, *, user_id: int, reason: str) -> None:
    invoice.status = "issue_unknown"
    invoice.facturama_error_message = reason
    attempt.status = "issue_unknown"
    attempt.error_message = reason
    attempt.completed_at = datetime.now(timezone.utc)
    write_audit_log(
        db,
        action="facturama.issue_unknown",
        entity="invoices",
        entity_id=invoice.id,
        user_id=user_id,
        new_values={"reason": reason},
    )
    db.commit()


def _mark_issued(
    db: Session,
    invoice: Invoice,
    attempt: FacturamaInvoiceAttempt,
    *,
    provider_payload: dict,
    http_status: int,
    user_id: int,
    reconciled: bool = False,
    stored_response_json: dict | None = None,
) -> None:
    facturama_id = _find_response_value(provider_payload, "Id", "id")
    uuid = _find_response_value(provider_payload, "Uuid", "UUID", "uuid")
    if not facturama_id or not uuid:
        raise ValueError("La respuesta de conciliación no contiene Id y UUID.")
    stamped_at = _parse_provider_datetime(_find_response_value(provider_payload, "Date", "date"))
    invoice.facturama_id = str(facturama_id)
    invoice.cfdi_uuid = str(uuid)
    invoice.facturama_environment = "sandbox"
    stored_response = stored_response_json or provider_payload
    invoice.facturama_response_json = stored_response
    invoice.facturama_http_status = http_status
    invoice.stamped_at = stamped_at or datetime.now(timezone.utc)
    if invoice.balance_due <= Decimal("0.00") and invoice.total > Decimal("0.00"):
        invoice.status = "paid"
    elif invoice.amount_paid > Decimal("0.00"):
        invoice.status = "partially_paid"
    else:
        invoice.status = "issued"
    invoice.facturama_error_message = None
    attempt.status = "issued"
    attempt.response_json = stored_response
    attempt.http_status = http_status
    attempt.error_message = None
    attempt.completed_at = datetime.now(timezone.utc)
    write_audit_log(
        db,
        action="facturama.issue_reconciled" if reconciled else "facturama.issue_succeeded",
        entity="invoices",
        entity_id=invoice.id,
        user_id=user_id,
        new_values={
            "uuid": invoice.cfdi_uuid,
            "facturama_id": invoice.facturama_id,
            "environment": "sandbox",
        },
    )
    db.commit()


def _latest_attempt(db: Session, invoice_id: int) -> FacturamaInvoiceAttempt | None:
    return db.scalar(
        select(FacturamaInvoiceAttempt)
        .where(FacturamaInvoiceAttempt.invoice_id == invoice_id)
        .order_by(FacturamaInvoiceAttempt.attempt_number.desc())
    )


def _request_series_and_folio(invoice: Invoice) -> tuple[str | None, str | None]:
    payload = invoice.facturama_request_json or {}
    response = invoice.facturama_response_json or {}
    provider_response = response.get("json", response) if isinstance(response, dict) else {}
    series = _find_response_value(provider_response, "Serie", "series") or payload.get("Serie")
    folio = _find_response_value(provider_response, "Folio", "folio") or payload.get("Folio")
    return str(series) if series not in (None, "") else None, str(folio) if folio not in (None, "") else None


def _receiver_rfc(invoice: Invoice) -> str | None:
    snapshot = invoice.fiscal_snapshot or {}
    value = snapshot.get("receiver_rfc")
    return str(value).strip().upper() if value else None


def _candidate_receiver_rfc(candidate: dict) -> Any:
    """RFC must come from Receiver, never from the Issuer node."""
    receiver = candidate.get("Receiver") or candidate.get("receiver")
    if isinstance(receiver, dict):
        return _find_response_value(receiver, "Rfc", "RFC", "receiver_rfc")
    return candidate.get("receiver_rfc")


def _candidate_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("Data", "data", "Items", "items", "Results", "results"):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
    return []


def _matches_reconciliation(invoice: Invoice, candidate: dict, *, series: str, folio: str, reference_time: datetime) -> bool:
    candidate_series = _find_response_value(candidate, "Serie", "series")
    candidate_folio = _find_response_value(candidate, "Folio", "folio")
    candidate_rfc = _candidate_receiver_rfc(candidate)
    candidate_total = _find_response_value(candidate, "Total", "total")
    candidate_date = _parse_provider_datetime(_find_response_value(candidate, "Date", "date"))
    receiver_rfc = _receiver_rfc(invoice)
    try:
        total_matches = Decimal(str(candidate_total)).quantize(Decimal("0.01")) == Decimal(str(invoice.total)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        total_matches = False
    return (
        str(candidate_series or "") == series
        and str(candidate_folio or "") == folio
        and str(candidate_rfc or "").strip().upper() == receiver_rfc
        and total_matches
        and candidate_date is not None
        and abs(candidate_date - reference_time) <= RECONCILIATION_WINDOW
    )


def _confirmed_reconciliation_payload(invoice: Invoice, provider_payload: dict, confirmation: dict, *, xml_uuid: str | None) -> dict | None:
    """Validate a known Facturama Id through GET before applying it locally."""
    issued_at = _parse_provider_datetime(confirmation["issued_at"])
    if str(confirmation["receiver_rfc"]).strip().upper() != _receiver_rfc(invoice):
        return None
    if issued_at is None or not _matches_reconciliation(
        invoice,
        provider_payload,
        series=str(confirmation["series"]),
        folio=str(confirmation["folio"]),
        reference_time=issued_at,
    ):
        return None
    expected = {
        "Id": "facturama_id",
        "Status": "status",
    }
    for provider_key, confirmation_key in expected.items():
        actual = _find_response_value(provider_payload, provider_key, provider_key.lower())
        if str(actual or "").strip().lower() != str(confirmation[confirmation_key]).strip().lower():
            return None
    provider_cfdi_type = str(_find_response_value(provider_payload, "CfdiType", "cfdi_type") or "").strip().lower()
    expected_cfdi_type = str(confirmation["cfdi_type"]).strip().lower()
    valid_cfdi_types = {expected_cfdi_type, "ingreso" if expected_cfdi_type == "i" else expected_cfdi_type}
    if provider_cfdi_type not in valid_cfdi_types:
        return None
    if str(xml_uuid or "").strip().lower() != str(confirmation["uuid"]).strip().lower():
        return None
    try:
        if Decimal(str(_find_response_value(provider_payload, "Subtotal", "subtotal"))).quantize(Decimal("0.01")) != Decimal(str(confirmation["subtotal"])).quantize(Decimal("0.01")):
            return None
    except (InvalidOperation, TypeError, ValueError):
        return None
    return {
        "Id": str(confirmation["facturama_id"]),
        "CfdiType": str(confirmation["cfdi_type"]),
        "Folio": str(confirmation["folio"]),
        "Serie": str(confirmation["series"]),
        "Uuid": str(confirmation["uuid"]),
        "Date": issued_at.isoformat(),
        "Subtotal": float(confirmation["subtotal"]),
        "Total": float(confirmation["total"]),
        "Status": str(confirmation["status"]),
        "reconciled": True,
    }


async def _xml_uuid_for_reconciliation(client: FacturamaClient, facturama_id: str) -> str | None:
    """Verify the UUID from Facturama's XML before trusting a manual match."""
    response = await client.get(f"/api/Cfdi/xml/issued/{facturama_id}")
    payload = response.json()
    content = base64.b64decode(payload["Content"])
    root = ElementTree.fromstring(content)
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] == "TimbreFiscalDigital":
            for name, value in element.attrib.items():
                if name.lower() == "uuid":
                    return value
    return None


async def reconcile_invoice(
    db: Session,
    invoice_id: int,
    *,
    user_id: int,
    client: FacturamaClient,
    confirmation: dict | None = None,
) -> Invoice:
    """Search issued CFDIs once and reconcile only a unique strict match.

    This function only performs GET requests.  Missing or ambiguous candidates
    preserve ``issue_unknown`` so an operator can reconcile it manually.
    """
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.is_active.is_(True)).with_for_update())
    if invoice is None:
        _error("invoice_not_found", "Factura no encontrada.", 404)
    if invoice.status == "issued" and invoice.facturama_id and confirmation is None:
        return await recover_documents(db, invoice_id, user_id=user_id, client=client)
    attempt = _latest_attempt(db, invoice.id)
    if attempt is None:
        _error("reconciliation_unavailable", "No existe un intento de emisión para conciliar.")
    if confirmation:
        response = await client.get(
            f"/cfdi/{confirmation['facturama_id']}", params={"type": "issued"}
        )
        diagnostics = response_diagnostics(response)
        provider_payload = diagnostics["json"]
        xml_uuid = await _xml_uuid_for_reconciliation(client, str(confirmation["facturama_id"]))
        reconciled = (
            _confirmed_reconciliation_payload(invoice, provider_payload, confirmation, xml_uuid=xml_uuid)
            if isinstance(provider_payload, dict)
            else None
        )
        if reconciled is None:
            _mark_unknown(
                db,
                invoice,
                attempt,
                user_id=user_id,
                reason="Los datos confirmados no coinciden con el CFDI recuperado de Facturama.",
            )
            _error("reconciliation_manual_required", "Los datos recuperados de Facturama no coinciden con la confirmación.")
        _mark_issued(
            db,
            invoice,
            attempt,
            provider_payload=reconciled,
            http_status=response.status_code,
            user_id=user_id,
            reconciled=True,
        )
        return await recover_documents(db, invoice_id, user_id=user_id, client=client)
    series, folio = _request_series_and_folio(invoice)
    if not series or not folio or not _receiver_rfc(invoice):
        _mark_unknown(db, invoice, attempt, user_id=user_id, reason="No hay serie, folio o RFC suficientes para una conciliación automática.")
        _error("reconciliation_manual_required", "No hay datos suficientes para buscar el CFDI sin riesgo de duplicado.")
    reference_time = invoice.facturama_attempted_at or attempt.created_at or datetime.now(timezone.utc)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)
    response = await client.get(
        "/cfdi",
        params={
            "type": "issued",
            "folioStart": folio,
            "folioEnd": folio,
            "rfc": _receiver_rfc(invoice),
            "dateStart": reference_time.strftime("%d/%m/%Y"),
            "dateEnd": reference_time.strftime("%d/%m/%Y"),
            "status": "active",
            "page": 0,
        },
    )
    diagnostics = response_diagnostics(response)
    candidates = [
        item
        for item in _candidate_items(diagnostics["json"])
        if _matches_reconciliation(invoice, item, series=series, folio=folio, reference_time=reference_time)
    ]
    if len(candidates) != 1:
        _mark_unknown(
            db,
            invoice,
            attempt,
            user_id=user_id,
            reason="La conciliación automática no encontró una coincidencia única.",
        )
        _error("reconciliation_manual_required", "No se encontró una coincidencia única; la factura requiere conciliación manual.")
    reconciled = dict(candidates[0])
    reconciled["reconciled"] = True
    _mark_issued(db, invoice, attempt, provider_payload=reconciled, http_status=response.status_code, user_id=user_id, reconciled=True)
    return await recover_documents(db, invoice_id, user_id=user_id, client=client)


async def issue_invoice(db: Session, invoice_id: int, *, user_id: int, client: FacturamaClient, settings: Settings) -> Invoice:
    if settings.facturama_environment != "sandbox":
        _error("facturama_production_disabled", "La emisión en producción todavía no está habilitada.")
    health = await FacturamaHealthService(client, settings).check()
    if not (settings.facturama_enabled and health.status == "connected"):
        _error("facturama_unavailable", "No es posible emitir porque Facturama no está conectado.")
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id, Invoice.is_active.is_(True)).with_for_update())
    if invoice is None:
        _error("invoice_not_found", "Factura no encontrada.", 404)
    if invoice.cfdi_uuid or invoice.facturama_id or invoice.status in ISSUE_BLOCKING_STATUSES:
        _error("invoice_already_issued" if invoice.status == "issued" else "invoice_reissue_blocked", "La factura no puede reemitirse hasta concluir su conciliación.")
    if invoice.review_required:
        _error("invoice_review_required", "Confirma la revisión del borrador antes de emitir.")
    settings_row = db.scalar(select(InvoiceSettings).where(InvoiceSettings.key == "default"))
    try:
        payload = map_invoice(invoice, settings_row)
    except InvoiceValidationError as exc:
        _error("invoice_validation_failed", "La factura no está lista para emitir.", 422, exc.fields)
    invoice.status = "issuing"
    invoice.facturama_request_json = payload
    invoice.facturama_environment = "sandbox"
    invoice.facturama_attempted_at = datetime.now(timezone.utc)
    attempt = FacturamaInvoiceAttempt(
        invoice_id=invoice.id,
        attempt_number=(db.scalar(select(func.count()).select_from(FacturamaInvoiceAttempt).where(FacturamaInvoiceAttempt.invoice_id == invoice.id)) or 0) + 1,
        status="issuing",
        request_json=payload,
        issued_by_id=user_id,
    )
    db.add(attempt)
    write_audit_log(db, action="facturama.issue_attempt", entity="invoices", entity_id=invoice.id, user_id=user_id, new_values={"environment": "sandbox"})
    db.commit()
    try:
        response = await client.post("/3/cfdis", json=payload)
    except FacturamaProviderResponseError as exc:
        invoice = db.get(Invoice, invoice_id)
        attempt = db.get(FacturamaInvoiceAttempt, attempt.id)
        _persist_response(invoice, attempt, _provider_response_snapshot(exc))
        if 400 <= exc.status_code < 500:
            invoice.status, invoice.facturama_error_message = "issue_rejected", str(exc)
            attempt.status, attempt.error_message = "failed", str(exc)
            attempt.completed_at = datetime.now(timezone.utc)
            write_audit_log(db, action="facturama.issue_failed", entity="invoices", entity_id=invoice_id, user_id=user_id, new_values={"error_type": type(exc).__name__, "http_status": exc.status_code})
            db.commit()
        else:
            _mark_unknown(db, invoice, attempt, user_id=user_id, reason="Facturama respondió con un error cuyo efecto de emisión no es concluyente.")
        _error("facturama_api_error", "Facturama rechazó o no pudo procesar la emisión.", 502, provider_status=exc.status_code, provider_detail=_provider_detail(exc))
    except FacturamaError as exc:
        invoice = db.get(Invoice, invoice_id)
        attempt = db.get(FacturamaInvoiceAttempt, attempt.id)
        _mark_unknown(db, invoice, attempt, user_id=user_id, reason="No fue posible confirmar si Facturama recibió la emisión.")
        _error("facturama_api_error", "Facturama rechazó o no pudo procesar la emisión.", 502)

    invoice = db.get(Invoice, invoice_id)
    attempt = db.get(FacturamaInvoiceAttempt, attempt.id)
    snapshot = response_diagnostics(response)
    _persist_response(invoice, attempt, snapshot)
    # Commit before JSON parsing or Id/UUID extraction: no HTTP response leaves issuing.
    db.commit()
    result = snapshot["json"]
    if not isinstance(result, dict):
        _mark_unknown(db, invoice, attempt, user_id=user_id, reason="Facturama respondió 2xx con JSON inválido.")
        return await reconcile_invoice(db, invoice_id, user_id=user_id, client=client)
    if not _find_response_value(result, "Id", "id") or not _find_response_value(result, "Uuid", "UUID", "uuid"):
        _mark_unknown(db, invoice, attempt, user_id=user_id, reason="Facturama respondió 2xx sin identificadores fiscales suficientes.")
        return await reconcile_invoice(db, invoice_id, user_id=user_id, client=client)
    _mark_issued(
        db,
        invoice,
        attempt,
        provider_payload=result,
        http_status=response.status_code,
        user_id=user_id,
        stored_response_json=snapshot,
    )
    return await recover_documents(db, invoice_id, user_id=user_id, client=client)


async def recover_documents(db: Session, invoice_id: int, *, user_id: int, client: FacturamaClient) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice or not invoice.facturama_id:
        _error("invoice_not_issued", "La factura aún no cuenta con identificador Facturama.")
    for fmt, attribute, mime in (("xml", "facturama_xml_path", "application/xml"), ("pdf", "facturama_pdf_path", "application/pdf")):
        if getattr(invoice, attribute):
            continue
        try:
            data = (await client.get(f"/api/Cfdi/{fmt}/issued/{invoice.facturama_id}")).json()
            content = base64.b64decode(data["Content"], validate=True)
            if fmt == "xml":
                validate_xml(content)
            else:
                validate_content(content, ".pdf", POLICIES["certificate_pdf"])
            target = build_storage_path(directory=f"facturama/{invoice.id}", filename=f"{invoice.cfdi_uuid}.{fmt}")
            atomic_write(target, content)
            setattr(invoice, attribute, relative_storage_path(target))
            write_audit_log(db, action=f"facturama.{fmt}_recovered", entity="invoices", entity_id=invoice.id, user_id=user_id, new_values={"path": getattr(invoice, attribute), "mime_type": data.get("ContentType", mime)})
        except Exception:
            write_audit_log(db, action=f"facturama.{fmt}_download_failed", entity="invoices", entity_id=invoice.id, user_id=user_id, new_values={"facturama_id": invoice.facturama_id})
    db.commit()
    return invoice


def read_document(invoice: Invoice, kind: str) -> tuple[bytes, str, str]:
    path = invoice.facturama_xml_path if kind == "xml" else invoice.facturama_pdf_path
    if not path:
        _error("document_pending", f"{kind.upper()} pendiente de recuperación.", 404)
    try:
        target = require_deliverable_file(path, not_found_detail="El documento no se encuentra en almacenamiento.")
    except HTTPException:
        _error("document_missing", "El documento no se encuentra en almacenamiento.", 404)
    return target.read_bytes(), target.name, "application/xml" if kind == "xml" else "application/pdf"
