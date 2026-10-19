"""Consulta autenticada de la evidencia histórica de aceptaciones de una cotización.

Sólo lectura. No reutiliza ni reactiva enlaces públicos de firmado (revocados).
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.quotation_acceptance import QuotationAcceptance
from app.models.quotation import Quotation


def _ensure_quotation(db: Session, quotation_id: int) -> None:
    if db.scalar(select(Quotation.id).where(Quotation.id == quotation_id)) is None:
        raise HTTPException(status_code=404, detail="Cotizacion no encontrada")


def list_acceptances(db: Session, quotation_id: int) -> list[dict]:
    _ensure_quotation(db, quotation_id)
    rows = db.scalars(
        select(QuotationAcceptance)
        .where(QuotationAcceptance.quotation_id == quotation_id)
        .order_by(QuotationAcceptance.accepted_at.desc(), QuotationAcceptance.id.desc())
    ).all()
    return [
        {
            "id": row.id,
            "confirmation_folio": row.confirmation_folio,
            "snapshot_id": row.snapshot_id,
            "signer_name": row.signer_name,
            "signer_email": row.signer_email,
            "pdf_sha256": row.pdf_sha256,
            "verified_at": row.verified_at,
            "accepted_at": row.accepted_at,
            "is_current": row.invalidated_at is None,
            "invalidated_at": row.invalidated_at,
            "invalidation_reason": row.invalidation_reason,
        }
        for row in rows
    ]


def get_acceptance_pdf(
    db: Session, quotation_id: int, acceptance_id: int
) -> tuple[bytes, str]:
    acceptance = db.scalar(
        select(QuotationAcceptance).where(
            QuotationAcceptance.id == acceptance_id,
            QuotationAcceptance.quotation_id == quotation_id,
        )
    )
    if acceptance is None:
        raise HTTPException(status_code=404, detail="Aceptación no encontrada")
    name = acceptance.confirmation_folio or f"aceptacion-{acceptance.id}"
    return acceptance.pdf_bytes, f"{name}.pdf"
