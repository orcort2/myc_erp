from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog_item import CatalogItem, CatalogItemComponent
from app.models.controlled_document import ControlledDocument, ControlledDocumentVersion
from app.services.storage_service import resolve_storage_path
from datetime import date
from app.schemas.catalog_item import (
    CatalogItemComponentCreate,
    CatalogItemCreate,
    CatalogItemUpdate,
    CATEGORY_LEGENDS,
    CATEGORY_TO_COMMODITY,
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
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _normalize_currency(value: str | None) -> str | None:
    return value.upper() if value else value


KEY_PREFIX_BY_ITEM_TYPE = {
    "product": "PRO",
    "service": "SER",
}

KEY_PREFIX_BY_CATEGORY = {
    "Calibracion": "CAL",
    "Mantenimiento": "MAN",
    "Reparacion": "REP",
    "Venta": "VEN",
    "Servicio general": "GEN",
    "Calificacion": "CALF",
    "Validacion": "VAL",
    "Capacitacion": "CAP",
    "Consultoria": "CON",
    "Patrones": "PAT",
    "Equipos": "EQU",
    "Accesorios": "ACC",
    "Consumibles": "CON",
}

LEGACY_KEY_PREFIX_BY_COMMODITY = {
    "calibration": "CAL",
    "maintenance": "MAN",
    "repair": "REP",
    "sale": "VEN",
    "general_service": "GEN",
}


def _normalize_category_key(category: str | None) -> str:
    return (category or "").strip().lower()


def _commodity_from_category(item_type: str | None, category: str | None, fallback: str | None = None) -> str:
    if item_type == "product":
        return "sale"
    return CATEGORY_TO_COMMODITY.get(_normalize_category_key(category), fallback or "general_service")


def _category_prefix(category: str | None, commodity: str | None) -> str:
    return KEY_PREFIX_BY_CATEGORY.get(category or "") or LEGACY_KEY_PREFIX_BY_COMMODITY.get(commodity or "", "GEN")


def _generate_internal_key(db: Session, item_type: str, category: str, commodity: str) -> str:
    prefix = f"{KEY_PREFIX_BY_ITEM_TYPE[item_type]}-{_category_prefix(category, commodity)}-"
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
    if payload.get("calibration_scope"):
        return LEGENDS_BY_SCOPE.get(payload.get("calibration_scope"))
    category = payload.get("category")
    if category in CATEGORY_LEGENDS:
        return CATEGORY_LEGENDS[category]
    return payload.get("quotation_legend")


def _prepare_values(values: dict, *, recalculate_price: bool = True) -> dict:
    values = dict(values)
    values["origin_currency"] = _normalize_currency(values.get("origin_currency"))
    values["cost_currency"] = _normalize_currency(values.get("cost_currency"))
    values["commodity"] = _commodity_from_category(
        values.get("item_type"), values.get("category"), values.get("commodity")
    )
    values["tax_object"] = values.get("tax_object") or "iva_16"
    values["tax_rate"] = TAX_RATE_BY_OBJECT[values["tax_object"]]

    values["quotation_legend"] = _quotation_legend(values)
    if values.get("item_type") == "product":
        values["service_kind"] = "simple"
        values["calibration_scope"] = None
        values["expected_certificate_master_id"] = None
    if values.get("category") != "Calibracion":
        values["expected_certificate_master_id"] = None
    if values.get("internal_unit") != "other":
        values["custom_internal_unit"] = None

    if recalculate_price or values.get("final_price_mxn") is None:
        values["final_price_mxn"] = calculate_final_price_mxn(
            values.get("origin_price", Decimal("0.00")),
            values.get("exchange_rate", Decimal("1.00")),
            values.get("margin_percent", Decimal("0.00")),
        )
    return values


def _ensure_certificate_master(db: Session, document_id: int | None) -> None:
    if document_id is None:
        return
    document = db.get(ControlledDocument, document_id)
    if document is None or document.document_type != "certificate_master" or document.status != "active":
        raise HTTPException(status_code=422, detail="La plantilla esperada debe ser un Master de Certificado activo")
    active_version = db.scalar(select(ControlledDocumentVersion.id).where(
        ControlledDocumentVersion.document_id == document_id,
        ControlledDocumentVersion.status == "active",
    ))
    version = db.scalar(select(ControlledDocumentVersion).where(
        ControlledDocumentVersion.document_id == document_id,
        ControlledDocumentVersion.status == "active",
    ))
    if version is None:
        raise HTTPException(status_code=422, detail="El Master de Certificado no tiene una versión activa")
    if version.expires_on and version.expires_on < date.today():
        raise HTTPException(status_code=422, detail="El Master de Certificado está caducado")
    path = resolve_storage_path(version.file_path)
    if not version.file_path or not path or not path.is_file() or path.suffix.lower() != ".xlsx":
        raise HTTPException(status_code=422, detail="El Master de Certificado no tiene un archivo XLSX disponible")


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
    query = (
        select(CatalogItem)
        .options(
            selectinload(CatalogItem.components).selectinload(
                CatalogItemComponent.component_item
            )
        )
        .order_by(CatalogItem.name)
    )
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
    item = db.scalar(
        select(CatalogItem)
        .where(CatalogItem.id == catalog_item_id)
        .options(
            selectinload(CatalogItem.components).selectinload(
                CatalogItemComponent.component_item
            )
        )
    )
    if item is None or not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concepto de catalogo no encontrado",
        )
    return item


def _component_ids(components) -> list[int]:
    return [component.component_catalog_item_id for component in components]


def _ensure_valid_components(
    db: Session,
    *,
    parent_id: int | None,
    service_kind: str,
    components,
) -> None:
    if service_kind == "simple":
        if components:
            raise HTTPException(status_code=422, detail="Un servicio simple no puede tener componentes")
        return
    if not components:
        raise HTTPException(
            status_code=422,
            detail="Un servicio compuesto debe tener al menos un componente",
        )

    component_ids = _component_ids(components)
    if len(component_ids) != len(set(component_ids)):
        raise HTTPException(status_code=422, detail="No se puede repetir un componente")
    if parent_id is not None and parent_id in component_ids:
        raise HTTPException(
            status_code=422,
            detail="Un servicio no puede agregarse a sí mismo como componente",
        )

    resolved = list(
        db.scalars(
            select(CatalogItem).where(
                CatalogItem.id.in_(component_ids),
                CatalogItem.is_active.is_(True),
                CatalogItem.item_type == "service",
            )
        ).all()
    )
    if {item.id for item in resolved} != set(component_ids):
        raise HTTPException(
            status_code=422,
            detail="Todos los componentes deben ser servicios activos existentes del catálogo",
        )

    if parent_id is None:
        return

    proposed_children = set(component_ids)

    def descendants(node_id: int, visited: set[int]) -> set[int]:
        if node_id in visited:
            return set()
        visited.add(node_id)
        if node_id == parent_id:
            children = proposed_children
        else:
            children = set(
                db.scalars(
                    select(CatalogItemComponent.component_catalog_item_id).where(
                        CatalogItemComponent.parent_catalog_item_id == node_id,
                        CatalogItemComponent.is_active.is_(True),
                    )
                ).all()
            )
        result = set(children)
        for child_id in children:
            result.update(descendants(child_id, visited))
        return result

    for child_id in component_ids:
        if parent_id in descendants(child_id, set()):
            raise HTTPException(
                status_code=422,
                detail="La composición genera una referencia circular",
            )


def _replace_components(item: CatalogItem, components) -> None:
    existing = {
        component.component_catalog_item_id: component
        for component in item.components
        if component.is_active
    }
    synchronized = []
    for component in components:
        link = existing.pop(component.component_catalog_item_id, None)
        if link is None:
            link = CatalogItemComponent(
                component_catalog_item_id=component.component_catalog_item_id
            )
        link.quantity = component.quantity
        synchronized.append(link)
    item.components = synchronized


def expand_catalog_item_for_operations(
    db: Session,
    catalog_item_id: int,
    quantity: int,
) -> list[dict]:
    """Expand a commercial catalog concept into simple operational leaves."""
    aggregated: dict[int, dict] = {}

    def walk(item_id: int, multiplier: int, path: tuple[int, ...]) -> None:
        if item_id in path:
            raise HTTPException(status_code=409, detail="El servicio compuesto contiene un ciclo")
        item = db.scalar(
            select(CatalogItem)
            .where(CatalogItem.id == item_id)
            .options(
                selectinload(CatalogItem.components).selectinload(
                    CatalogItemComponent.component_item
                )
            )
        )
        if item is None:
            raise HTTPException(status_code=409, detail="El concepto de catálogo ya no existe")
        if item.service_kind == "simple":
            current = aggregated.setdefault(
                item.id,
                {
                    "catalog_item_id": item.id,
                    "service_name": item.name,
                    "calibration_scope": item.calibration_scope,
                    "expected_certificate_master_id": (
                        item.expected_certificate_master_id
                    ),
                    "quantity": 0,
                    "status": "pending",
                },
            )
            current["quantity"] += multiplier
            return
        active_components = [component for component in item.components if component.is_active]
        if not active_components:
            raise HTTPException(
                status_code=409,
                detail=f"El servicio compuesto {item.name} no tiene componentes activos",
            )
        for component in active_components:
            if not component.component_item.is_active:
                raise HTTPException(
                    status_code=409,
                    detail=f"El componente {component.component_item.name} está inactivo",
                )
            walk(
                component.component_catalog_item_id,
                multiplier * component.quantity,
                (*path, item_id),
            )

    walk(catalog_item_id, quantity, tuple())
    return list(aggregated.values())


def create_catalog_item(
    db: Session,
    payload: CatalogItemCreate,
    *,
    user_id: int | None = None,
) -> CatalogItem:
    raw_values = payload.model_dump()
    components = payload.components
    raw_values.pop("components", None)
    values = _prepare_values(raw_values)
    _ensure_valid_components(
        db,
        parent_id=None,
        service_kind=values["service_kind"],
        components=components,
    )
    _ensure_certificate_master(db, values.get("expected_certificate_master_id"))
    values["internal_key"] = _generate_internal_key(
        db, values["item_type"], values["category"], values["commodity"]
    )
    item = CatalogItem(**values)
    _replace_components(item, components)
    db.add(item)
    db.flush()
    write_audit_log(
        db,
        action="catalog_item.created",
        entity="catalog_items",
        entity_id=item.id,
        user_id=user_id,
        new_values=_json_safe({
            "name": item.name,
            "internal_key": item.internal_key,
            "service_kind": item.service_kind,
            "components": [component.model_dump() for component in components],
        }),
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
    components_provided = "components" in updates
    requested_components = payload.components if components_provided else None
    updates.pop("components", None)
    previous_values = {key: getattr(item, key) for key in updates}
    if components_provided or "service_kind" in updates:
        previous_values["components"] = [
            {
                "component_catalog_item_id": component.component_catalog_item_id,
                "quantity": component.quantity,
            }
            for component in item.components
            if component.is_active
        ]
    merged = {
        "item_type": item.item_type,
        "service_kind": item.service_kind,
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
        "expected_certificate_master_id": item.expected_certificate_master_id,
        "quotation_legend": item.quotation_legend,
        "tax_object": item.tax_object,
    } | updates

    should_recalculate = bool({"origin_price", "exchange_rate", "margin_percent"} & set(updates))
    prepared = _prepare_values(merged, recalculate_price=should_recalculate)
    _ensure_certificate_master(db, prepared.get("expected_certificate_master_id"))
    if prepared["service_kind"] == "simple":
        effective_components = []
    elif components_provided:
        effective_components = requested_components or []
    else:
        effective_components = [
            CatalogItemComponentCreate(
                component_catalog_item_id=component.component_catalog_item_id,
                quantity=component.quantity,
            )
            for component in item.components
            if component.is_active
        ]
    _ensure_valid_components(
        db,
        parent_id=item.id,
        service_kind=prepared["service_kind"],
        components=effective_components,
    )
    if {"item_type", "category"} & set(updates):
        prepared["internal_key"] = _generate_internal_key(
            db, prepared["item_type"], prepared["category"], prepared["commodity"]
        )
    else:
        prepared["internal_key"] = item.internal_key

    keys_to_apply = set(updates) | {
        "service_kind",
        "calibration_scope",
        "custom_internal_unit",
        "final_price_mxn",
        "internal_key",
        "quotation_legend",
        "tax_rate",
    }
    for key in keys_to_apply:
        setattr(item, key, prepared[key])
    if components_provided or prepared["service_kind"] == "simple":
        _replace_components(item, effective_components)

    write_audit_log(
        db,
        action="catalog_item.updated",
        entity="catalog_items",
        entity_id=item.id,
        user_id=user_id,
        previous_values=_json_safe(previous_values),
        new_values=_json_safe(updates | {
            "components": [component.model_dump() for component in effective_components]
        }),
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
    referenced_by = db.scalar(
        select(CatalogItemComponent.id).where(
            CatalogItemComponent.component_catalog_item_id == catalog_item_id,
            CatalogItemComponent.is_active.is_(True),
        )
    )
    if referenced_by is not None:
        raise HTTPException(
            status_code=409,
            detail="El servicio no puede desactivarse porque forma parte de un servicio compuesto",
        )
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
