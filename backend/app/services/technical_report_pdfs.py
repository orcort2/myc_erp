"""PDF institucional del Reporte de Instalación (SG-4G).

Documento propio de la familia TechnicalReport: NO reutiliza FieldSheet ni el
acuse de entrega. Se renderiza SOLO a partir del `document_snapshot` final
(congelado al finalizar) más los activos que éste referencia (fotografías de
evidencia y firmas de la entrega), nunca de datos vivos del cliente/equipo/
usuario. La orquestación transaccional vive en
`technical_reports.finalize_technical_report`."""

from __future__ import annotations

import base64
import hashlib
from datetime import date, datetime
from typing import Any

from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.models.lab_work_order_delivery import LabWorkOrderDelivery
from app.models.technical_report import TechnicalReport
from app.services.field_sheet_layouts import ORGANIZATION_PRINT_PROFILES
from app.services.lab_delivery_pdfs import DELIVERY_METHOD_LABELS
from app.services.storage_service import require_deliverable_file
from app.services.work_order_pdfs import APP_DIR, LOGO_PATH, TEMPLATE_DIR, _filename

INSTALLATION_REPORT_RENDERER_VERSION = 1
INSTALLATION_REPORT_TEMPLATE = "technical_report_installation.html"

EVIDENCE_TYPES = ("before", "during", "incident", "after")

EFFECTIVENESS_LABELS = {
    "satisfactory": "Satisfactorio",
    "satisfactory_with_observations": "Satisfactorio con observaciones",
    "unsatisfactory": "No satisfactorio",
}

_MYC_PRINT_PROFILE = ORGANIZATION_PRINT_PROFILES["myc"]
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_IMAGE_MAGIC = {"image/jpeg": b"\xff\xd8\xff", "image/png": _PNG_MAGIC}


def _document_error(detail: str) -> HTTPException:
    return HTTPException(status_code=409, detail=detail)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_signature_data_url(value: str | None, label: str) -> bytes:
    """Misma validación que las firmas LAB (PNG base64 real), con mensaje de
    dominio. Devuelve los bytes decodificados."""
    from app.services.lab_work_orders import _decode_signature

    if not value:
        raise _document_error(f"La entrega no tiene {label}")
    try:
        return _decode_signature(value)
    except HTTPException as exc:
        raise _document_error(f"La entrega tiene una {label} inválida") from exc


def build_installation_final_snapshot(
    report: TechnicalReport,
    delivery: LabWorkOrderDelivery,
    *,
    delivery_item_id: int | None,
    generated_at: datetime,
) -> dict[str, Any]:
    """Snapshot final: base = `document_snapshot` ya congelado al crear el
    reporte (OT/cliente/equipo); se le suma todo lo demás que el PDF necesita
    para no depender de datos vivos."""
    base = dict(report.document_snapshot or {})
    delivered_by = delivery.delivered_by
    evidence = sorted(report.evidence, key=lambda item: item.position)
    return {
        "document": {
            "technical_report_id": report.id,
            "folio": report.folio,
            "report_type": report.report_type,
            "revision_number": report.revision_number,
            "report_schema_version": report.report_schema_version,
            "generated_at": generated_at.isoformat(),
            "renderer_version": INSTALLATION_REPORT_RENDERER_VERSION,
        },
        "work_order": base.get("work_order") or {},
        "client": base.get("client") or {},
        "equipment": base.get("equipment") or {},
        "capture_values": dict(report.capture_values or {}),
        "technician": {
            "performed_by_user_id": report.performed_by_user_id,
            "performed_by_name_snapshot": report.performed_by_name_snapshot,
            "performed_at": report.performed_at.isoformat() if report.performed_at else None,
        },
        "delivery": {
            "delivery_id": delivery.id,
            "delivery_item_id": delivery_item_id,
            "exhibition_number": delivery.exhibition_number,
            "delivery_type": delivery.delivery_type,
            "delivery_method": delivery.delivery_method,
            "delivered_at": delivery.delivered_at.isoformat(),
            "delivered_by_user_id": delivery.delivered_by_user_id,
            "delivered_by_name": delivered_by.full_name if delivered_by is not None else None,
            "recipient_name": delivery.recipient_name,
            # Las imágenes viven en la entrega (inmutable); aquí queda la huella.
            "delivered_by_signature_sha256": _sha256_text(delivery.delivered_by_signature_data_url),
            "recipient_signature_sha256": _sha256_text(delivery.recipient_signature_data_url),
        },
        "client_conformity_text": report.client_conformity_text_snapshot,
        "evidence": [
            {
                "id": item.id,
                "evidence_type": item.evidence_type,
                "position": item.position,
                "storage_path": item.storage_path,
                "mime_type": item.mime_type,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
                "caption": item.caption,
            }
            for item in evidence
        ],
    }


def load_evidence_images(snapshot: dict[str, Any]) -> dict[int, str]:
    """Carga cada evidencia del snapshot desde el storage administrado y la
    valida contra su metadata. Cualquier falla aborta TODA la generación: una
    fotografía histórica requerida nunca se omite en silencio."""
    images: dict[int, str] = {}
    for item in snapshot["evidence"]:
        label = f"la evidencia {item['evidence_type']} #{item['position']}"
        try:
            path = require_deliverable_file(item["storage_path"])
        except HTTPException as exc:
            raise _document_error(f"No se encontró el archivo de {label}") from exc
        content = path.read_bytes()
        mime = item["mime_type"]
        if (
            hashlib.sha256(content).hexdigest() != item["sha256"]
            or len(content) != item["size_bytes"]
            or mime not in _IMAGE_MAGIC
            or not content.startswith(_IMAGE_MAGIC[mime])
        ):
            raise _document_error(f"El archivo de {label} no coincide con su registro")
        images[item["id"]] = f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"
    return images


def _format_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        return date.fromisoformat(value[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return value


def _format_datetime(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%d/%m/%Y · %H:%M")
    except ValueError:
        return value


def _yes_no(value: bool | None) -> str:
    return "" if value is None else "Sí" if value else "No"


def _view_model(snapshot: dict[str, Any], images: dict[int, str], signatures: dict[str, str]) -> dict[str, Any]:
    capture = snapshot["capture_values"]
    document = snapshot["document"]
    delivery = snapshot["delivery"]
    client = snapshot["client"]
    address = ", ".join(
        part for part in (
            client.get("address"), client.get("postal_code"), client.get("city"), client.get("state_name"),
        ) if part
    )
    contact = " · ".join(
        part for part in (
            client.get("contact_name"), client.get("contact_phone"), client.get("contact_email"),
        ) if part
    )
    photos: dict[str, list[dict[str, Any]]] = {kind: [] for kind in EVIDENCE_TYPES}
    for item in snapshot["evidence"]:
        photos[item["evidence_type"]].append({
            "uri": images[item["id"]], "caption": item.get("caption"), "position": item["position"],
        })
    return {
        "document": document,
        "installation_date": _format_date(capture.get("installation_date")),
        "work_order": snapshot["work_order"],
        "client_name": client.get("name"),
        "client_address": address,
        "client_contact": contact,
        "equipment": snapshot["equipment"],
        "capture": capture,
        "has_incidents": capture.get("has_incidents"),
        "functional_test_label": _yes_no(capture.get("functional_test_performed")),
        "effectiveness_label": EFFECTIVENESS_LABELS.get(capture.get("effectiveness_result") or "", ""),
        # Filas de 2 fotos (tabla): saltos de página por fila, sin huérfanos.
        "photo_rows": {kind: [items[i:i + 2] for i in range(0, len(items), 2)] for kind, items in photos.items()},
        "technician_name": snapshot["technician"]["performed_by_name_snapshot"],
        "performed_at": _format_datetime(snapshot["technician"]["performed_at"]),
        "conformity_text": snapshot["client_conformity_text"],
        "delivery": delivery,
        "delivery_method_label": DELIVERY_METHOD_LABELS.get(delivery["delivery_method"], delivery["delivery_method"]),
        "delivered_at_display": _format_datetime(delivery["delivered_at"]),
        "delivered_by_signature": signatures["delivered_by"],
        "recipient_signature": signatures["recipient"],
        "reception_date": _format_date(snapshot["work_order"].get("reception_date")),
        "logo_uri": LOGO_PATH.as_uri() if LOGO_PATH.exists() else None,
        "primary_color": _MYC_PRINT_PROFILE["primary_color"],
        "header_fill": _MYC_PRINT_PROFILE["header_fill"],
    }


def render_installation_report_pdf(
    snapshot: dict[str, Any],
    images: dict[int, str],
    signatures: dict[str, str],
) -> bytes:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    html = env.get_template(INSTALLATION_REPORT_TEMPLATE).render(**_view_model(snapshot, images, signatures))
    return HTML(string=html, base_url=str(APP_DIR)).write_pdf()


def installation_report_filename(snapshot: dict[str, Any]) -> str:
    document = snapshot["document"]
    return f"Reporte-instalacion-{_filename(document['folio'])}-r{document['revision_number']}.pdf"
