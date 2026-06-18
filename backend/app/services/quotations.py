from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.client import Client
from app.models.catalog_item import CatalogItem
from app.models.quotation import Quotation, QuotationItem
from app.schemas.quotation import (
    QuotationCreate,
    QuotationItemCreate,
    QuotationItemUpdate,
    QuotationStatusChange,
    QuotationUpdate,
)
from app.services.audit_logs import write_audit_log

TERMINAL_STATUSES = {"accepted", "rejected", "expired", "cancelled"}
ALLOWED_TRANSITIONS = {
    "draft": {"sent", "cancelled"},
    "sent": {"waiting", "accepted", "rejected", "expired", "cancelled"},
    "waiting": {"accepted", "rejected", "expired", "cancelled"},
    "accepted": set(),
    "rejected": set(),
    "expired": set(),
    "cancelled": set(),
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _decimal_or_zero(value: Decimal | None) -> Decimal:
    return Decimal("0.00") if value is None else Decimal(value)


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _ensure_client_exists(db: Session, client_id: int) -> None:
    exists = db.scalar(
        select(Client.id).where(Client.id == client_id, Client.is_active.is_(True))
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )


def _get_catalog_item(db: Session, catalog_item_id: int | None) -> CatalogItem | None:
    if catalog_item_id is None:
        return None
    item = db.get(CatalogItem, catalog_item_id)
    if item is None or not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concepto de catalogo no encontrado",
        )
    return item


def _quotation_item_values(
    db: Session,
    payload: QuotationItemCreate | QuotationItemUpdate,
    *,
    existing_item: QuotationItem | None = None,
) -> dict:
    values = payload.model_dump(exclude_unset=True)
    catalog_item = _get_catalog_item(db, values.get("catalog_item_id"))
    if catalog_item is not None:
        values.setdefault("service_name", catalog_item.name)
        values.setdefault("description", catalog_item.description)
        values.setdefault(
            "unit",
            catalog_item.custom_internal_unit
            if catalog_item.internal_unit == "other"
            else catalog_item.internal_unit or catalog_item.sat_unit,
        )
        values.setdefault("sat_key", catalog_item.sat_key)
        values.setdefault("sat_unit", catalog_item.sat_unit)
        values.setdefault("internal_unit", catalog_item.internal_unit)
        values.setdefault("unit_price", catalog_item.final_price_mxn)
        values.setdefault("currency", "MXN")
        values.setdefault("commodity", catalog_item.commodity)
        values.setdefault("calibration_scope", catalog_item.calibration_scope)
        values.setdefault("quotation_legend", catalog_item.quotation_legend)
        values.setdefault("tax_object", catalog_item.tax_object)
        values.setdefault("tax_rate", catalog_item.tax_rate)
    if "currency" in values and values["currency"]:
        values["currency"] = values["currency"].upper()
    if existing_item is None and values.get("tax_object") is None:
        values.setdefault("tax_object", "iva_16")
    if existing_item is None and values.get("tax_rate") is None:
        values["tax_rate"] = Decimal("16.00")
    if existing_item is None and values.get("discount_percent") is None:
        values["discount_percent"] = Decimal("0.00")
    if existing_item is not None and "catalog_item_id" in values and values["catalog_item_id"] is None:
        values["commodity"] = None
        values["calibration_scope"] = None
        values["quotation_legend"] = None
        values["sat_key"] = None
        values["sat_unit"] = None
        values["internal_unit"] = None
    if existing_item is None and not values.get("service_name"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Captura el nombre de la partida o selecciona un concepto del catalogo",
        )
    return values


def _next_quotation_folio(db: Session, issued_on: date) -> str:
    prefix = f"MYC-{issued_on:%m}-{issued_on:%y}-"
    last_folio = db.scalar(
        select(Quotation.folio)
        .where(Quotation.folio.like(f"{prefix}%"))
        .order_by(Quotation.folio.desc())
        .limit(1)
    )
    if not last_folio:
        sequence = 1
    else:
        sequence = int(last_folio.rsplit("-", 1)[-1]) + 1
    return f"{prefix}{sequence:04d}"


def _recalculate_totals(quotation: Quotation) -> None:
    active_items = [item for item in quotation.items if item.is_active is not False]
    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")
    for item in active_items:
        gross = Decimal(item.quantity) * _decimal_or_zero(item.unit_price)
        discount = gross * (_decimal_or_zero(item.discount_percent) / Decimal("100"))
        item.total = _money(gross - discount)
        item.tax_total = _money(item.total * (_decimal_or_zero(item.tax_rate) / Decimal("100")))
        subtotal += item.total
        tax_total += item.tax_total
    quotation.subtotal = _money(subtotal)
    quotation.tax_total = _money(tax_total)
    quotation.total = _money(quotation.subtotal + quotation.tax_total)


def list_quotations(db: Session, *, include_inactive: bool = False) -> list[Quotation]:
    query = (
        select(Quotation)
        .options(selectinload(Quotation.items))
        .order_by(Quotation.created_at.desc())
    )
    if not include_inactive:
        query = query.where(Quotation.is_active.is_(True))
    return list(db.scalars(query).all())


def get_quotation(db: Session, quotation_id: int) -> Quotation:
    quotation = db.scalar(
        select(Quotation)
        .where(Quotation.id == quotation_id)
        .options(selectinload(Quotation.items))
    )
    if quotation is None or not quotation.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotizacion no encontrada",
        )
    return quotation


def create_quotation(
    db: Session, payload: QuotationCreate, *, user_id: int | None = None
) -> Quotation:
    _ensure_client_exists(db, payload.client_id)
    issued_on = payload.issued_on or date.today()
    quotation = Quotation(
        folio=_next_quotation_folio(db, issued_on),
        client_id=payload.client_id,
        advisor_id=payload.advisor_id,
        issued_on=issued_on,
        valid_until=payload.valid_until,
        notes=payload.notes,
        status="draft",
    )
    quotation.items = [
        QuotationItem(**_quotation_item_values(db, item), total=Decimal("0.00"))
        for item in payload.items
    ]
    _recalculate_totals(quotation)
    db.add(quotation)
    db.flush()
    write_audit_log(
        db,
        action="quotation.created",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        new_values=_json_safe(
            {
                "folio": quotation.folio,
                "client_id": quotation.client_id,
                "total": quotation.total,
            }
        ),
    )
    db.commit()
    return get_quotation(db, quotation.id)


def update_quotation(
    db: Session,
    quotation_id: int,
    payload: QuotationUpdate,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(db, quotation_id)
    if quotation.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede editar una cotizacion en estado terminal",
        )
    updates = payload.model_dump(exclude_unset=True)
    previous_values = {key: getattr(quotation, key) for key in updates}
    for key, value in updates.items():
        setattr(quotation, key, value)
    write_audit_log(
        db,
        action="quotation.updated",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values=_json_safe(previous_values),
        new_values=_json_safe(updates),
    )
    db.commit()
    return get_quotation(db, quotation.id)


def add_quotation_item(
    db: Session,
    quotation_id: int,
    payload: QuotationItemCreate,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(db, quotation_id)
    if quotation.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pueden agregar partidas a una cotizacion en estado terminal",
        )
    item = QuotationItem(**_quotation_item_values(db, payload), total=Decimal("0.00"))
    quotation.items.append(item)
    _recalculate_totals(quotation)
    db.flush()
    write_audit_log(
        db,
        action="quotation.item_added",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        new_values=_json_safe(
            {"service_name": item.service_name, "quantity": item.quantity, "total": item.total}
        ),
    )
    db.commit()
    return get_quotation(db, quotation.id)


def update_quotation_item(
    db: Session,
    quotation_id: int,
    item_id: int,
    payload: QuotationItemUpdate,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(db, quotation_id)
    if quotation.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pueden editar partidas de una cotizacion en estado terminal",
        )
    item = next((item for item in quotation.items if item.id == item_id and item.is_active), None)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partida no encontrada",
        )
    updates = _quotation_item_values(db, payload, existing_item=item)
    previous_values = {key: getattr(item, key) for key in updates}
    for key, value in updates.items():
        setattr(item, key, value)
    _recalculate_totals(quotation)
    write_audit_log(
        db,
        action="quotation.item_updated",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values=_json_safe(previous_values),
        new_values=_json_safe(updates | {"quotation_total": quotation.total}),
    )
    db.commit()
    return get_quotation(db, quotation.id)


def deactivate_quotation_item(
    db: Session,
    quotation_id: int,
    item_id: int,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(db, quotation_id)
    if quotation.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pueden eliminar partidas de una cotizacion en estado terminal",
        )
    item = next((item for item in quotation.items if item.id == item_id and item.is_active), None)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partida no encontrada",
        )
    previous_values = {
        "service_name": item.service_name,
        "quantity": item.quantity,
        "total": item.total,
        "is_active": item.is_active,
    }
    item.is_active = False
    item.deleted_at = datetime.now(timezone.utc)
    item.deleted_by = user_id
    _recalculate_totals(quotation)
    write_audit_log(
        db,
        action="quotation.item_deactivated",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values=_json_safe(previous_values),
        new_values=_json_safe(
            {
                "item_id": item.id,
                "is_active": False,
                "quotation_total": quotation.total,
            }
        ),
    )
    db.commit()
    return get_quotation(db, quotation.id)


def change_quotation_status(
    db: Session,
    quotation_id: int,
    new_status: str,
    payload: QuotationStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(db, quotation_id)
    allowed = ALLOWED_TRANSITIONS.get(quotation.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transicion no permitida: {quotation.status} -> {new_status}",
        )
    previous_status = quotation.status
    quotation.status = new_status
    action = f"quotation.{new_status}" if new_status != "sent" else "quotation.sent"
    write_audit_log(
        db,
        action=action,
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": new_status},
        comment=payload.comment if payload else None,
    )
    db.commit()
    return get_quotation(db, quotation.id)


def deactivate_quotation(
    db: Session, quotation_id: int, *, user_id: int | None = None
) -> Quotation:
    quotation = get_quotation(db, quotation_id)
    quotation.is_active = False
    quotation.deleted_at = datetime.now(timezone.utc)
    quotation.deleted_by = user_id
    write_audit_log(
        db,
        action="quotation.deactivated",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False},
    )
    db.commit()
    return quotation
