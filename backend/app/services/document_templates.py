from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_template import DocumentTemplate
from app.schemas.document_template import DocumentTemplateUpdate


QUOTATION_TEMPLATE_KEY = "quotation"

DEFAULT_QUOTATION_TEMPLATE = {
    "template_key": QUOTATION_TEMPLATE_KEY,
    "name": "Plantilla de cotizacion MYC",
    "company_name": "Metrologia y Servicios MYC",
    "company_tagline": "Servicios de metrologia, calibracion, venta y soporte tecnico especializado.",
    "company_rfc": "MYC000000XXX",
    "company_email": "contacto@mycmetrology.com.mx",
    "company_website": "www.mycmetrology.com.mx",
    "company_address": "",
    "company_phone": "",
    "document_title": "COTIZACION",
    "document_subtitle": "Propuesta comercial de servicios, calibracion y soluciones tecnicas",
    "document_code": "FCA-23-2",
    "document_revision": None,
    "document_issued_on": date(2025, 3, 28),
    "terms_version": "V1",
    "commercial_terms": "\n".join(
        [
            "Precios expresados en moneda nacional, salvo indicacion contraria.",
            "Vigencia sujeta a la fecha indicada en esta cotizacion.",
            "Tiempos de entrega y alcance final se confirman al recibir autorizacion.",
        ]
    ),
    "metrological_terms": "Los servicios metrologicos se ejecutan conforme al alcance tecnico autorizado y a la disponibilidad de patrones aplicables.",
    "legal_terms": "La autorizacion de esta cotizacion implica aceptacion de las condiciones comerciales, tecnicas y documentales descritas.",
    "privacy_notice": "Los datos del cliente se usan exclusivamente para fines comerciales, operativos, documentales y de facturacion relacionados con el servicio solicitado.",
    "acceptance_text": "Acepto las condiciones comerciales, metrologicas y legales de la presente cotizacion.",
    "show_summary_terms": True,
    "show_full_terms": True,
    "show_acceptance_signature": True,
    "is_active": True,
}


def get_default_quotation_template_values() -> dict:
    return dict(DEFAULT_QUOTATION_TEMPLATE)


def get_or_create_quotation_template(db: Session) -> DocumentTemplate:
    template = db.scalar(
        select(DocumentTemplate).where(
            DocumentTemplate.template_key == QUOTATION_TEMPLATE_KEY,
            DocumentTemplate.is_active.is_(True),
        )
    )
    if template is not None:
        return template
    template = DocumentTemplate(**get_default_quotation_template_values())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_quotation_template(
    db: Session,
    payload: DocumentTemplateUpdate,
) -> DocumentTemplate:
    template = get_or_create_quotation_template(db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return template
    for key, value in updates.items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template


def restore_quotation_template_defaults(db: Session) -> DocumentTemplate:
    template = get_or_create_quotation_template(db)
    defaults = get_default_quotation_template_values()
    defaults.pop("template_key", None)
    for key, value in defaults.items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template


def get_document_template(db: Session, template_key: str) -> DocumentTemplate:
    if template_key != QUOTATION_TEMPLATE_KEY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada")
    return get_or_create_quotation_template(db)
