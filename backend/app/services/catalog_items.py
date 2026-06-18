from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.catalog_item import CatalogItem
from app.schemas.catalog_item import (
    CatalogItemCreate,
    CatalogItemUpdate,
    LEGENDS_BY_COMMODITY,
    LEGENDS_BY_SCOPE,
    TAX_RATE_BY_OBJECT,
    calculate_final_price_mxn,
)
from app.services.audit_logs import write_audit_log


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _normalize_currency(value: str | None) -> str | None:
    return value.upper() if value else value


KEY_PREFIX_BY_ITEM_TYPE = {
    "product": "PRO",
    "service": "SER",
}

KEY_PREFIX_BY_COMMODITY = {
    "calibration": "CAL",
    "maintenance": "MAN",
    "repair": "REP",
    "sale": "VEN",
    "general_service": "GEN",
}


def _generate_internal_key(db: Session, item_type: str, commodity: str) -> str:
    prefix = f"{KEY_PREFIX_BY_ITEM_TYPE[item_type]}-{KEY_PREFIX_BY_COMMODITY[commodity]}-"
    last_key = db.scalar(
        select(CatalogItem.internal_key)
        .where(CatalogItem.internal_key.like(f"{prefix}%"))
        .order_by(CatalogItem.internal_key.desc())
        .limit(1)
    )
    if not last_key:
        sequence = 1
    else:
        sequence = int(last_key.rsplit("-", 1)[-1]) + 1
    return f"{prefix}{sequence:04d}"


def _quotation_legend(payload: dict) -> str | None:
    commodity = payload.get("commodity")
    if commodity == "calibration":
        return LEGENDS_BY_SCOPE.get(payload.get("calibration_scope"))
    if commodity in LEGENDS_BY_COMMODITY:
        return LEGENDS_BY_COMMODITY[commodity]
    return payload.get("quotation_legend")


def _prepare_values(values: dict, *, recalculate_price: bool = True) -> dict:
    values = dict(values)
    values["origin_currency"] = _normalize_currency(values.get("origin_currency"))
    values["cost_currency"] = _normalize_currency(values.get("cost_currency"))
    values["tax_object"] = values.get("tax_object") or "iva_16"
    values["tax_rate"] = TAX_RATE_BY_OBJECT[values["tax_object"]]

    if values.get("commodity") == "general_service":
        values["quotation_legend"] = values.get("quotation_legend")
    else:
        values["quotation_legend"] = _quotation_legend(values)
    if values.get("commodity") != "calibration":
        values["calibration_scope"] = None
    if values.get("internal_unit") != "other":
        values["custom_internal_unit"] = None

    if recalculate_price or values.get("final_price_mxn") is None:
        values["final_price_mxn"] = calculate_final_price_mxn(
            values.get("origin_price", Decimal("0.00")),
            values.get("exchange_rate", Decimal("1.00")),
            values.get("margin_percent", Decimal("0.00")),
        )
    return values


def list_catalog_items(
    db: Session,
    *,
    item_type: str | None = None,
    commodity: str | None = None,
    category: str | None = None,
    origin_currency: str | None = None,
    tax_object: str | None = None,
    is_active: bool | None = True,
    search: str | None = None,
) -> list[CatalogItem]:
    query = select(CatalogItem).order_by(CatalogItem.name)
    if is_active is not None:
        query = query.where(CatalogItem.is_active.is_(is_active))
    if item_type:
        query = query.where(CatalogItem.item_type == item_type)
    if commodity:
        query = query.where(CatalogItem.commodity == commodity)
    if category:
        query = query.where(CatalogItem.category.ilike(f"%{category}%"))
    if origin_currency:
        query = query.where(CatalogItem.origin_currency == origin_currency.upper())
    if tax_object:
        query = query.where(CatalogItem.tax_object == tax_object)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                CatalogItem.name.ilike(pattern),
                CatalogItem.internal_key.ilike(pattern),
                CatalogItem.description.ilike(pattern),
                CatalogItem.category.ilike(pattern),
                CatalogItem.sat_key.ilike(pattern),
                CatalogItem.sat_unit.ilike(pattern),
            )
        )
    return list(db.scalars(query).all())


def get_catalog_item(db: Session, catalog_item_id: int) -> CatalogItem:
    item = db.get(CatalogItem, catalog_item_id)
    if item is None or not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concepto de catalogo no encontrado",
        )
    return item


def create_catalog_item(
    db: Session,
    payload: CatalogItemCreate,
    *,
    user_id: int | None = None,
) -> CatalogItem:
    values = _prepare_values(payload.model_dump())
    values["internal_key"] = _generate_internal_key(db, values["item_type"], values["commodity"])
    item = CatalogItem(**values)
    db.add(item)
    db.flush()
    write_audit_log(
        db,
        action="catalog_item.created",
        entity="catalog_items",
        entity_id=item.id,
        user_id=user_id,
        new_values=_json_safe({"name": item.name, "internal_key": item.internal_key}),
    )
    db.commit()
    db.refresh(item)
    return item


def update_catalog_item(
    db: Session,
    catalog_item_id: int,
    payload: CatalogItemUpdate,
    *,
    user_id: int | None = None,
) -> CatalogItem:
    item = get_catalog_item(db, catalog_item_id)
    updates = payload.model_dump(exclude_unset=True)
    previous_values = {key: getattr(item, key) for key in updates}
    merged = {
        "item_type": item.item_type,
        "commodity": item.commodity,
        "category": item.category,
        "name": item.name,
        "description": item.description,
        "sat_key": item.sat_key,
        "sat_unit": item.sat_unit,
        "internal_unit": item.internal_unit,
        "custom_internal_unit": item.custom_internal_unit,
        "origin_price": item.origin_price,
        "origin_currency": item.origin_currency,
        "exchange_rate": item.exchange_rate,
        "margin_percent": item.margin_percent,
        "final_price_mxn": item.final_price_mxn,
        "internal_cost": item.internal_cost,
        "cost_currency": item.cost_currency,
        "calibration_scope": item.calibration_scope,
        "quotation_legend": item.quotation_legend,
        "tax_object": item.tax_object,
    } | updates

    should_recalculate = bool({"origin_price", "exchange_rate", "margin_percent"} & set(updates))
    prepared = _prepare_values(merged, recalculate_price=should_recalculate)
    CatalogItemCreate(**prepared)
    if {"item_type", "commodity"} & set(updates):
        prepared["internal_key"] = _generate_internal_key(
            db, prepared["item_type"], prepared["commodity"]
        )
    else:
        prepared["internal_key"] = item.internal_key

    keys_to_apply = set(updates) | {
        "calibration_scope",
        "custom_internal_unit",
        "final_price_mxn",
        "internal_key",
        "quotation_legend",
        "tax_rate",
    }
    for key in keys_to_apply:
        setattr(item, key, prepared[key])

    write_audit_log(
        db,
        action="catalog_item.updated",
        entity="catalog_items",
        entity_id=item.id,
        user_id=user_id,
        previous_values=_json_safe(previous_values),
        new_values=_json_safe(updates),
    )
    db.commit()
    db.refresh(item)
    return item


def delete_catalog_item(
    db: Session,
    catalog_item_id: int,
    *,
    user_id: int | None = None,
) -> CatalogItem:
    item = get_catalog_item(db, catalog_item_id)
    item.is_active = False
    item.deleted_at = datetime.now(timezone.utc)
    item.deleted_by = user_id
    write_audit_log(
        db,
        action="catalog_item.deactivated",
        entity="catalog_items",
        entity_id=item.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False},
    )
    db.commit()
    db.refresh(item)
    return item
