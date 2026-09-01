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
    upper = lambda value: value.upper() if isinstance(value, str) else value
    client = SimpleNamespace(
        commercial_name=upper(work_order.client_name),
        legal_name=upper(work_order.client_name),
        rfc="",
        contacts=[SimpleNamespace(name=upper(work_order.contact_name or ""), is_active=True)],
        street=upper(work_order.address),
        exterior_number=None,
        interior_number=None,
        neighborhood=None,
        city=upper(work_order.city),
        state=upper(work_order.state_name),
        postal_code=work_order.postal_code,
        country=None,
    )
    purchase_order = (work_order.purchase_order or "").strip()
    notes = upper(work_order.notes or "")
    revision_number = work_order.revision_number or 1
    if revision_number > 1 and work_order.reopen_ticket_id:
        reopening_note = upper(
            f"Revisión {revision_number}: reapertura autorizada mediante "
            f"Ticket #{work_order.reopen_ticket_id}. "
            + (
                "Firma de la revisión anterior preservada."
                if work_order.signature_preserved
                else "Se recabaron nuevas firmas para esta revisión."
            )
        )
        notes = f"{notes}\n{reopening_note}".strip()
    document = SimpleNamespace(
        created_at=work_order.reception_date,
        service_date=work_order.departure_date,
        work_order_number=work_order.folio,
        equipment=[
            SimpleNamespace(
                **{
                    key: upper(getattr(item, key))
                    for key in ("instrument", "brand", "identification", "serial_number", "report_number")
                },
                is_good_condition=item.is_good_condition,
                name=upper(item.name),
                internal_id=upper(item.internal_id),
                certificates=[],
            )
            for item in work_order.equipment
        ],
        client=client,
        notes=notes,
        quotation=SimpleNamespace(folio=purchase_order) if purchase_order else None,
        technician_signature_data_url=(technician.signature_data_url if technician else None),
        technician_signed_name=(upper(technician.signer_name) if technician else None),
        client_received_signature_data_url=(
            client_signature.signature_data_url if client_signature else None
        ),
        client_received_signed_name=(upper(client_signature.signer_name) if client_signature else None),
        client_acceptance_signature_data_url=(
            client_signature.signature_data_url if client_signature else None
        ),
        client_acceptance_signed_name=(upper(client_signature.signer_name) if client_signature else None),
    )
    lab_work_order = SimpleNamespace(work_order_number=work_order.folio)
    html = _render_html(
        document,
        work_order=lab_work_order,
        equipment_list=document.equipment,
        client_address_override=upper(work_order.address or ""),
        client_postal_code=work_order.postal_code or "",
        client_city=upper(work_order.city or ""),
        client_state=upper(work_order.state_name or ""),
    )
    return (
        HTML(string=html, base_url=str(APP_DIR)).write_pdf(),
        f"OT-{work_order.folio}-r{revision_number}-{_filename(work_order.client_name)}.pdf",
    )
