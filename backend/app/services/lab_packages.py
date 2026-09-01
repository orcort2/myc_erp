from __future__ import annotations

import io

from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter
from sqlalchemy.orm import Session

from app.models.lab_work_order import LabWorkOrder
from app.models.user import User
from app.services.audit_logs import write_audit_log
from app.services.field_sheet_pdfs import generate_field_sheet_pdf
from app.services.lab_work_order_pdfs import generate_lab_work_order_pdf
from app.services.lab_work_orders import _get, _group


def _append_pdf(writer: PdfWriter, content: bytes) -> None:
    reader = PdfReader(io.BytesIO(content))
    for page in reader.pages:
        writer.add_page(page)


def generate_lab_package(
    db: Session,
    work_order_id: int,
    user: User,
    *,
    group: bool,
) -> tuple[bytes, str]:
    selected = _get(db, work_order_id)
    orders = _group(db, selected) if group else [selected]
    orders = sorted(orders, key=lambda item: item.sequence_number)
    writer = PdfWriter()
    for order in orders:
        order_pdf = order.final_pdf or generate_lab_work_order_pdf(order)[0]
        _append_pdf(writer, order_pdf)
        for equipment in sorted(order.equipment, key=lambda item: item.position):
            if equipment.field_sheet is None:
                continue
            sheet_pdf, _ = generate_field_sheet_pdf(db, equipment.field_sheet.id)
            _append_pdf(writer, sheet_pdf)
    output = io.BytesIO()
    writer.write(output)
    content = output.getvalue()
    if not content:
        raise HTTPException(status_code=409, detail="No fue posible componer el paquete LAB")
    write_audit_log(
        db,
        action="lab_package.downloaded",
        entity="lab_work_orders",
        entity_id=selected.id,
        user_id=user.id,
        new_values={
            "scope": "group" if group else "individual",
            "work_order_ids": [item.id for item in orders],
            "folios": [item.folio for item in orders],
        },
    )
    db.commit()
    filename = (
        f"Paquete_LAB_Grupo_{orders[0].folio}.pdf"
        if group
        else f"Paquete_LAB_OT_{selected.folio}.pdf"
    )
    return content, filename
