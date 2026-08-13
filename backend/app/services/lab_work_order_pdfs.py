from __future__ import annotations

from types import SimpleNamespace

from weasyprint import HTML

from app.models.lab_work_order import LabWorkOrder
from app.services.work_order_pdfs import APP_DIR, _filename, _render_html


def generate_lab_work_order_pdf(work_order: LabWorkOrder) -> tuple[bytes, str]:
    """Renderiza el formato institucional sin conectar el LAB al agregado productivo."""

    signatures = {
        item.signature_type: item
        for item in (work_order.signature_session.signatures if work_order.signature_session else [])
    }
    technician = signatures.get("technician")
    client_signature = signatures.get("client")
    client = SimpleNamespace(
        commercial_name=work_order.client_name,
        legal_name=work_order.client_name,
        rfc="",
        contacts=[SimpleNamespace(name=work_order.contact_name or "", is_active=True)],
        street=work_order.address,
        exterior_number=None,
        interior_number=None,
        neighborhood=None,
        city=work_order.city,
        state=work_order.state_name,
        postal_code=work_order.postal_code,
        country=None,
    )
    document = SimpleNamespace(
        created_at=work_order.reception_date,
        service_date=work_order.departure_date,
        work_order_number=work_order.folio,
        equipment=work_order.equipment,
        client=client,
        notes=work_order.notes,
        quotation=(
            SimpleNamespace(folio=work_order.purchase_order)
            if work_order.purchase_order
            else None
        ),
        technician_signature_data_url=(technician.signature_data_url if technician else None),
        technician_signed_name=(technician.signer_name if technician else None),
        client_received_signature_data_url=(
            client_signature.signature_data_url if client_signature else None
        ),
        client_received_signed_name=(client_signature.signer_name if client_signature else None),
        client_acceptance_signature_data_url=(
            client_signature.signature_data_url if client_signature else None
        ),
        client_acceptance_signed_name=(client_signature.signer_name if client_signature else None),
    )
    lab_work_order = SimpleNamespace(work_order_number=work_order.folio)
    html = _render_html(
        document,
        work_order=lab_work_order,
        equipment_list=list(work_order.equipment),
    )
    return (
        HTML(string=html, base_url=str(APP_DIR)).write_pdf(),
        f"OT-{work_order.folio}-{_filename(work_order.client_name)}.pdf",
    )
