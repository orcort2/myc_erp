from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog_item import CatalogItem
from app.models.client import Client
from app.models.linked_company import LinkedCompany
from app.models.quotation import Quotation, QuotationItem, QuotationSnapshot
from app.models.service_execution import (
    ServiceStage,
    ServiceUnit,
    TechnicalServiceRequest,
)
from app.schemas.quotation import (
    QuotationCreate,
    QuotationItemCreate,
    QuotationItemUpdate,
    QuotationStatusChange,
    QuotationUpdate,
)
from app.schemas.service_type import normalize_service_type
from app.services.activity import publish_event
from app.services.audit_logs import write_audit_log
from app.services.catalog_items import expand_catalog_item_for_operations


TERMINAL_STATUSES = {
    "accepted",
    "rejected",
    "expired",
    "cancelled",
}

ALLOWED_TRANSITIONS = {
    "draft": {"sent", "cancelled"},
    "sent": {
        "waiting",
        "accepted",
        "rejected",
        "expired",
        "cancelled",
    },
    "waiting": {
        "accepted",
        "rejected",
        "expired",
        "cancelled",
    },
    "accepted": set(),
    "rejected": set(),
    "expired": set(),
    "cancelled": set(),
}


def _money(value: Decimal) -> Decimal:
    return value.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _decimal_or_zero(
    value: Decimal | None,
) -> Decimal:
    return (
        Decimal("0.00")
        if value is None
        else Decimal(value)
    )


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _json_safe(item)
            for item in value
        ]

    return value


def _ensure_client_exists(
    db: Session,
    client_id: int,
) -> None:
    exists = db.scalar(
        select(Client.id).where(
            Client.id == client_id,
            Client.is_active.is_(True),
        )
    )

    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )


def _get_catalog_item(
    db: Session,
    catalog_item_id: int | None,
) -> CatalogItem | None:
    if catalog_item_id is None:
        return None

    item = db.get(
        CatalogItem,
        catalog_item_id,
    )

    if item is None or not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Concepto de catalogo no encontrado",
        )

    return item


def _build_operational_snapshot(
    db: Session,
    catalog_item: CatalogItem,
) -> dict:
    """
    Construye la realidad comercial/técnica congelada de una partida.

    El catálogo puede evolucionar posteriormente, pero una cotización
    existente debe conservar la configuración que tenía cuando fue creada
    o cuando el concepto fue sustituido explícitamente.
    """

    def snapshot_for(
        item: CatalogItem,
        *,
        include_nested_sale_calibration: bool = True,
    ) -> dict:
        company = (
            db.get(
                LinkedCompany,
                item.linked_company_id,
            )
            if item.linked_company_id is not None
            else None
        )

        service_type = normalize_service_type(
            item.service_type,
            calibration_scope=item.calibration_scope,
        )

        included_calibration_snapshot = None

        if (
            include_nested_sale_calibration
            and item.included_calibration_catalog_item_id
            is not None
        ):
            included_item = db.get(
                CatalogItem,
                item.included_calibration_catalog_item_id,
            )

            if (
                included_item is not None
                and included_item.is_active
            ):
                included_calibration_snapshot = snapshot_for(
                    included_item,
                    include_nested_sale_calibration=False,
                )

        return {
            "service_id": item.id,
            "service_key": item.internal_key,
            "service_name_snapshot": item.name,
            "service_description_snapshot": (
                item.description
            ),

            # Autoridad operacional congelada.
            "operational_category": (
                item.operational_category
            ),

            "service_type_snapshot": (
                service_type.value
                if service_type
                else None
            ),

            "calibration_scope_snapshot": (
                item.calibration_scope
            ),

            "linked_company_id": (
                item.linked_company_id
            ),

            "linked_company_name_snapshot": (
                company.name
                if company
                else None
            ),

            "certificate_prefix_snapshot": (
                item.linked_certificate_prefix
            ),

            "price_snapshot": (
                f"{Decimal(item.final_price_mxn):.2f}"
            ),

            "tax_snapshot": {
                "object": item.tax_object,
                "rate": (
                    f"{Decimal(item.tax_rate):.2f}"
                ),
            },

            "accreditation_snapshot": (
                {
                    "scope": (
                        item.calibration_scope
                    )
                }
                if (
                    service_type
                    and service_type.value
                    == "accredited"
                )
                else None
            ),

            "traceability_snapshot": (
                {
                    "scope": (
                        item.calibration_scope
                    )
                }
                if (
                    service_type
                    and service_type.value
                    == "traceable"
                )
                else None
            ),

            "procedure_snapshot": None,

            "template_snapshot": {
                "expected_certificate_master_id": (
                    item.expected_certificate_master_id
                )
            },

            # Configuración congelada de Venta.
            "sale_configuration_snapshot": {
                "requires_individual_identification": (
                    bool(
                        item.requires_individual_identification
                    )
                ),
                "brand": item.sale_brand,
                "model": item.sale_model,
                "specification": (
                    item.sale_specification
                ),
                "included_calibration_catalog_item_id": (
                    item.included_calibration_catalog_item_id
                ),
                "included_calibration_snapshot": (
                    included_calibration_snapshot
                ),
            },

            # Configuración congelada de Mantenimiento.
            "maintenance_configuration_snapshot": {
                "maintenance_type": (
                    item.maintenance_type
                ),
                "location_mode": (
                    item.maintenance_location
                ),
                "base_materials": list(
                    item.maintenance_base_materials
                    or []
                ),
            },
        }

    if catalog_item.service_kind == "composite":
        operational_items = (
            expand_catalog_item_for_operations(
                db,
                catalog_item.id,
                1,
            )
        )

        # La expansión existente se realiza contra el catálogo
        # únicamente en el momento de crear el snapshot.
        #
        # Después de este punto la cotización conserva esta identidad
        # y no debe reinterpretarse contra el catálogo vivo.
        for operational_item in operational_items:
            component_id = operational_item.get(
                "catalog_item_id"
            )

            component = (
                db.get(
                    CatalogItem,
                    component_id,
                )
                if component_id is not None
                else None
            )

            if component is None:
                continue

            operational_item[
                "operational_category"
            ] = component.operational_category

            operational_item[
                "expected_certificate_master_id"
            ] = (
                component.expected_certificate_master_id
            )

            operational_item[
                "service_snapshot"
            ] = snapshot_for(component)

    else:
        operational_items = [
            {
                "catalog_item_id": catalog_item.id,
                "service_name": catalog_item.name,

                "operational_category": (
                    catalog_item.operational_category
                ),

                "calibration_scope": (
                    catalog_item.calibration_scope
                ),

                "expected_certificate_master_id": (
                    catalog_item.expected_certificate_master_id
                ),

                "quantity": 1,
                "status": "pending",

                "service_snapshot": snapshot_for(
                    catalog_item
                ),
            }
        ]

    return {
        "schema_version": 2,

        "service_kind": (
            catalog_item.service_kind
        ),

        "commercial_catalog_item_id": (
            catalog_item.id
        ),

        "commercial_service_name": (
            catalog_item.name
        ),

        "commercial_operational_category": (
            catalog_item.operational_category
        ),

        "commercial_service_snapshot": (
            snapshot_for(catalog_item)
        ),

        "operational_items": operational_items,
    }


def _quotation_item_values(
    db: Session,
    payload: (
        QuotationItemCreate
        | QuotationItemUpdate
    ),
    *,
    existing_item: QuotationItem | None = None,
) -> dict:
    values = payload.model_dump(
        exclude_unset=True,
    )

    context_ids = (
        values.get("source_service_order_id"),
        values.get("source_service_unit_id"),
        values.get("source_stage_id"),
        values.get("technical_request_id"),
    )

    if any(
        value is not None
        for value in context_ids
    ):
        if not all(
            value is not None
            for value in context_ids
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_422_UNPROCESSABLE_ENTITY
                ),
                detail=(
                    "La partida derivada requiere ETS, "
                    "unidad, etapa origen y solicitud técnica"
                ),
            )

        unit = db.get(
            ServiceUnit,
            values["source_service_unit_id"],
        )

        stage = db.get(
            ServiceStage,
            values["source_stage_id"],
        )

        request = db.get(
            TechnicalServiceRequest,
            values["technical_request_id"],
        )

        if (
            unit is None
            or stage is None
            or request is None
            or unit.service_order_id
            != values["source_service_order_id"]
            or stage.service_unit_id
            != unit.id
            or request.service_order_id
            != unit.service_order_id
            or request.service_unit_id
            != unit.id
            or request.source_stage_id
            != stage.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "El contexto ETS de la partida "
                    "derivada es inconsistente"
                ),
            )

        values["equipment_snapshot"] = {
            "brand": unit.brand,
            "model": unit.model,
            "serial_number": (
                unit.serial_number
            ),
        }

        request.status = "quoted"

    catalog_item_was_provided = (
        "catalog_item_id" in values
    )

    requested_catalog_item_id = (
        values.get("catalog_item_id")
        if catalog_item_was_provided
        else None
    )

    catalog_item = (
        _get_catalog_item(
            db,
            requested_catalog_item_id,
        )
        if (
            catalog_item_was_provided
            and requested_catalog_item_id
            is not None
        )
        else None
    )

    catalog_item_changed = (
        catalog_item is not None
        and (
            existing_item is None
            or existing_item.catalog_item_id
            != catalog_item.id
        )
    )

    # Sólo una partida nueva o una sustitución explícita de concepto
    # debe reconstruir el snapshot.
    #
    # Si el frontend vuelve a enviar el mismo catalog_item_id durante
    # una edición, se conserva el snapshot histórico existente.
    if catalog_item_changed:
        values[
            "operational_snapshot"
        ] = _build_operational_snapshot(
            db,
            catalog_item,
        )

        values.setdefault(
            "service_name",
            catalog_item.name,
        )

        values.setdefault(
            "description",
            catalog_item.description,
        )

        values.setdefault(
            "unit",
            (
                catalog_item.custom_internal_unit
                if (
                    catalog_item.internal_unit
                    == "other"
                )
                else (
                    catalog_item.internal_unit
                    or catalog_item.sat_unit
                )
            ),
        )

        values.setdefault(
            "sat_key",
            catalog_item.sat_key,
        )

        values.setdefault(
            "sat_unit",
            catalog_item.sat_unit,
        )

        values.setdefault(
            "internal_unit",
            catalog_item.internal_unit,
        )

        values.setdefault(
            "unit_price",
            catalog_item.final_price_mxn,
        )

        values.setdefault(
            "currency",
            "MXN",
        )

        values.setdefault(
            "commodity",
            catalog_item.commodity,
        )

        # operational_category es identidad canónica.
        # No debe poder ser contradicha por el frontend.
        values[
            "operational_category"
        ] = catalog_item.operational_category

        values.setdefault(
            "calibration_scope",
            catalog_item.calibration_scope,
        )

        values.setdefault(
            "quotation_legend",
            catalog_item.quotation_legend,
        )

        values.setdefault(
            "tax_object",
            catalog_item.tax_object,
        )

        values.setdefault(
            "tax_rate",
            catalog_item.tax_rate,
        )

    # Si se envió explícitamente el mismo concepto en una edición,
    # aseguramos que el payload no reemplace la identidad histórica.
    elif (
        existing_item is not None
        and catalog_item is not None
        and existing_item.catalog_item_id
        == catalog_item.id
    ):
        values.pop(
            "operational_snapshot",
            None,
        )

        values[
            "operational_category"
        ] = (
            existing_item.operational_category
        )

    if (
        "currency" in values
        and values["currency"]
    ):
        values["currency"] = (
            values["currency"].upper()
        )

    if (
        existing_item is None
        and values.get("tax_object")
        is None
    ):
        values.setdefault(
            "tax_object",
            "iva_16",
        )

    if (
        existing_item is None
        and values.get("tax_rate")
        is None
    ):
        values["tax_rate"] = Decimal(
            "16.00"
        )

    if (
        existing_item is None
        and values.get("discount_percent")
        is None
    ):
        values[
            "discount_percent"
        ] = Decimal("0.00")

    # Desvincular explícitamente una partida del catálogo elimina
    # también la identidad operacional derivada del concepto.
    if (
        existing_item is not None
        and "catalog_item_id" in values
        and values["catalog_item_id"]
        is None
    ):
        values["commodity"] = None
        values[
            "operational_category"
        ] = None
        values[
            "calibration_scope"
        ] = None
        values[
            "quotation_legend"
        ] = None
        values["sat_key"] = None
        values["sat_unit"] = None
        values[
            "internal_unit"
        ] = None
        values[
            "operational_snapshot"
        ] = None

    if (
        existing_item is None
        and not values.get(
            "service_name"
        )
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Captura el nombre de la partida "
                "o selecciona un concepto del catalogo"
            ),
        )

    return values


def _next_quotation_folio(
    db: Session,
    issued_on: date,
) -> str:
    prefix = (
        f"MYC-{issued_on:%m}-{issued_on:%y}-"
    )

    last_folio = db.scalar(
        select(Quotation.folio)
        .where(
            Quotation.folio.like(
                f"{prefix}%"
            )
        )
        .order_by(
            Quotation.folio.desc()
        )
        .limit(1)
    )

    if not last_folio:
        sequence = 1
    else:
        sequence = (
            int(
                last_folio.rsplit(
                    "-",
                    1,
                )[-1]
            )
            + 1
        )

    return (
        f"{prefix}{sequence:04d}"
    )


def _quotation_snapshot_data(
    quotation: Quotation,
) -> dict:
    return _json_safe(
        {
            "client_id": (
                quotation.client_id
            ),

            "advisor_id": (
                quotation.advisor_id
            ),

            "issued_on": (
                quotation.issued_on
            ),

            "valid_until": (
                quotation.valid_until
            ),

            "payment_terms": (
                quotation.payment_terms
            ),

            "notes": quotation.notes,

            "subtotal": (
                quotation.subtotal
            ),

            "tax_total": (
                quotation.tax_total
            ),

            "total": quotation.total,

            "items": [
                {
                    "id": item.id,

                    "catalog_item_id": (
                        item.catalog_item_id
                    ),

                    "commodity": (
                        item.commodity
                    ),

                    "operational_category": (
                        item.operational_category
                    ),

                    "operational_snapshot": (
                        item.operational_snapshot
                    ),

                    "service_name": (
                        item.service_name
                    ),

                    "description": (
                        item.description
                    ),

                    "calibration_scope": (
                        item.calibration_scope
                    ),

                    "quotation_legend": (
                        item.quotation_legend
                    ),

                    "tax_object": (
                        item.tax_object
                    ),

                    "tax_rate": (
                        item.tax_rate
                    ),

                    "quantity": (
                        item.quantity
                    ),

                    "unit": item.unit,

                    "sat_key": (
                        item.sat_key
                    ),

                    "sat_unit": (
                        item.sat_unit
                    ),

                    "internal_unit": (
                        item.internal_unit
                    ),

                    "unit_price": (
                        item.unit_price
                    ),

                    "discount_percent": (
                        item.discount_percent
                    ),

                    "tax_total": (
                        item.tax_total
                    ),

                    "total": (
                        item.total
                    ),

                    "is_active": (
                        item.is_active
                    ),
                }
                for item in quotation.items
            ],
        }
    )


def _write_snapshot(
    db: Session,
    quotation: Quotation,
    *,
    reason: str,
    user_id: int | None = None,
) -> QuotationSnapshot:
    current_number = db.scalar(
        select(
            func.max(
                QuotationSnapshot.snapshot_number
            )
        ).where(
            QuotationSnapshot.quotation_id
            == quotation.id
        )
    )

    snapshot = QuotationSnapshot(
        quotation_id=quotation.id,
        snapshot_number=(
            current_number or 0
        )
        + 1,
        reason=reason,
        created_by_id=user_id,
        snapshot_data=(
            _quotation_snapshot_data(
                quotation
            )
        ),
    )

    db.add(snapshot)
    db.flush()

    return snapshot


def _date_from_snapshot(
    value: object,
) -> date | None:
    if value in (
        None,
        "",
    ):
        return None

    if isinstance(
        value,
        date,
    ):
        return value

    if isinstance(
        value,
        str,
    ):
        return date.fromisoformat(
            value
        )

    return None


def _recalculate_totals(
    quotation: Quotation,
) -> None:
    active_items = [
        item
        for item in quotation.items
        if item.is_active is not False
    ]

    subtotal = Decimal(
        "0.00"
    )

    tax_total = Decimal(
        "0.00"
    )

    for item in active_items:
        gross = (
            Decimal(item.quantity)
            * _decimal_or_zero(
                item.unit_price
            )
        )

        discount = (
            gross
            * (
                _decimal_or_zero(
                    item.discount_percent
                )
                / Decimal("100")
            )
        )

        item.total = _money(
            gross - discount
        )

        item.tax_total = _money(
            item.total
            * (
                _decimal_or_zero(
                    item.tax_rate
                )
                / Decimal("100")
            )
        )

        subtotal += item.total
        tax_total += item.tax_total

    quotation.subtotal = _money(
        subtotal
    )

    quotation.tax_total = _money(
        tax_total
    )

    quotation.total = _money(
        quotation.subtotal
        + quotation.tax_total
    )


def list_quotations(
    db: Session,
    *,
    include_inactive: bool = False,
    client_id: int | None = None,
) -> list[Quotation]:
    query = (
        select(Quotation)
        .options(
            selectinload(
                Quotation.items
            ).selectinload(
                QuotationItem.decisions
            ),
            selectinload(
                Quotation.advisor
            ),
        )
        .order_by(
            Quotation.created_at.desc()
        )
    )

    if not include_inactive:
        query = query.where(
            Quotation.is_active.is_(True)
        )

    if client_id is not None:
        query = query.where(
            Quotation.client_id
            == client_id
        )

    return list(
        db.scalars(
            query
        ).all()
    )


def get_quotation(
    db: Session,
    quotation_id: int,
) -> Quotation:
    quotation = db.scalar(
        select(Quotation)
        .where(
            Quotation.id
            == quotation_id
        )
        .options(
            selectinload(
                Quotation.items
            ).selectinload(
                QuotationItem.decisions
            ),
            selectinload(
                Quotation.advisor
            ),
        )
    )

    if (
        quotation is None
        or not quotation.is_active
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Cotizacion no encontrada",
        )

    return quotation


def create_quotation(
    db: Session,
    payload: QuotationCreate,
    *,
    user_id: int | None = None,
) -> Quotation:
    _ensure_client_exists(
        db,
        payload.client_id,
    )

    issued_on = (
        payload.issued_on
        or date.today()
    )

    quotation = Quotation(
        folio=_next_quotation_folio(
            db,
            issued_on,
        ),
        client_id=payload.client_id,
        advisor_id=(
            user_id
            or payload.advisor_id
        ),
        issued_on=issued_on,
        valid_until=(
            payload.valid_until
        ),
        payment_terms=(
            payload.payment_terms
        ),
        notes=payload.notes,
        status="draft",
    )

    quotation.items = [
        QuotationItem(
            **_quotation_item_values(
                db,
                item,
            ),
            total=Decimal("0.00"),
        )
        for item in payload.items
    ]

    _recalculate_totals(
        quotation
    )

    db.add(quotation)
    db.flush()

    _write_snapshot(
        db,
        quotation,
        reason="created",
        user_id=user_id,
    )

    write_audit_log(
        db,
        action="quotation.created",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        new_values=_json_safe(
            {
                "folio": (
                    quotation.folio
                ),
                "client_id": (
                    quotation.client_id
                ),
                "advisor_id": (
                    quotation.advisor_id
                ),
                "total": (
                    quotation.total
                ),
            }
        ),
    )

    db.commit()

    return get_quotation(
        db,
        quotation.id,
    )


def update_quotation(
    db: Session,
    quotation_id: int,
    payload: QuotationUpdate,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(
        db,
        quotation_id,
    )

    if (
        quotation.status
        in TERMINAL_STATUSES
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "No se puede editar una "
                "cotizacion en estado terminal"
            ),
        )

    updates = payload.model_dump(
        exclude_unset=True,
    )

    if "client_id" in updates:
        _ensure_client_exists(
            db,
            updates["client_id"],
        )

    previous_values = {
        key: getattr(
            quotation,
            key,
        )
        for key in updates
    }

    for key, value in updates.items():
        setattr(
            quotation,
            key,
            value,
        )

    db.flush()

    if updates:
        _write_snapshot(
            db,
            quotation,
            reason="updated",
            user_id=user_id,
        )

    write_audit_log(
        db,
        action="quotation.updated",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values=_json_safe(
            previous_values
        ),
        new_values=_json_safe(
            updates
        ),
    )

    db.commit()

    return get_quotation(
        db,
        quotation.id,
    )


def list_quotation_snapshots(
    db: Session,
    quotation_id: int,
) -> list[QuotationSnapshot]:
    get_quotation(
        db,
        quotation_id,
    )

    return list(
        db.scalars(
            select(
                QuotationSnapshot
            )
            .where(
                QuotationSnapshot.quotation_id
                == quotation_id
            )
            .order_by(
                QuotationSnapshot.snapshot_number.desc()
            )
        ).all()
    )


def restore_quotation_snapshot(
    db: Session,
    quotation_id: int,
    snapshot_id: int,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(
        db,
        quotation_id,
    )

    if (
        quotation.status
        in TERMINAL_STATUSES
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "No se puede restaurar una "
                "cotizacion en estado terminal"
            ),
        )

    snapshot = db.scalar(
        select(
            QuotationSnapshot
        ).where(
            QuotationSnapshot.id
            == snapshot_id,
            QuotationSnapshot.quotation_id
            == quotation_id,
        )
    )

    if snapshot is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Version de cotizacion "
                "no encontrada"
            ),
        )

    data = (
        snapshot.snapshot_data
        or {}
    )

    previous_values = (
        _quotation_snapshot_data(
            quotation
        )
    )

    if (
        data.get("client_id")
        is not None
    ):
        _ensure_client_exists(
            db,
            int(
                data["client_id"]
            ),
        )

        quotation.client_id = int(
            data["client_id"]
        )

    quotation.issued_on = (
        _date_from_snapshot(
            data.get("issued_on")
        )
    )

    quotation.valid_until = (
        _date_from_snapshot(
            data.get("valid_until")
        )
    )

    quotation.payment_terms = (
        data.get("payment_terms")
    )

    quotation.notes = (
        data.get("notes")
    )

    db.flush()

    _write_snapshot(
        db,
        quotation,
        reason=(
            f"restored:"
            f"{snapshot.snapshot_number}"
        ),
        user_id=user_id,
    )

    write_audit_log(
        db,
        action=(
            "quotation.snapshot_restored"
        ),
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values=(
            previous_values
        ),
        new_values=(
            _quotation_snapshot_data(
                quotation
            )
        ),
    )

    db.commit()

    return get_quotation(
        db,
        quotation.id,
    )


def add_quotation_item(
    db: Session,
    quotation_id: int,
    payload: QuotationItemCreate,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(
        db,
        quotation_id,
    )

    if (
        quotation.status
        in TERMINAL_STATUSES
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "No se pueden agregar partidas "
                "a una cotizacion en estado terminal"
            ),
        )

    item = QuotationItem(
        **_quotation_item_values(
            db,
            payload,
        ),
        total=Decimal("0.00"),
    )

    quotation.items.append(
        item
    )

    _recalculate_totals(
        quotation
    )

    db.flush()

    _write_snapshot(
        db,
        quotation,
        reason="item_added",
        user_id=user_id,
    )

    write_audit_log(
        db,
        action="quotation.item_added",
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        new_values=_json_safe(
            {
                "service_name": (
                    item.service_name
                ),
                "quantity": (
                    item.quantity
                ),
                "total": (
                    item.total
                ),
            }
        ),
    )

    db.commit()

    return get_quotation(
        db,
        quotation.id,
    )


def update_quotation_item(
    db: Session,
    quotation_id: int,
    item_id: int,
    payload: QuotationItemUpdate,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(
        db,
        quotation_id,
    )

    if (
        quotation.status
        in TERMINAL_STATUSES
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "No se pueden editar partidas "
                "de una cotizacion en estado terminal"
            ),
        )

    item = next(
        (
            item
            for item
            in quotation.items
            if (
                item.id == item_id
                and item.is_active
            )
        ),
        None,
    )

    if item is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Partida no encontrada",
        )

    updates = _quotation_item_values(
        db,
        payload,
        existing_item=item,
    )

    previous_values = {
        key: getattr(
            item,
            key,
        )
        for key in updates
    }

    for key, value in updates.items():
        setattr(
            item,
            key,
            value,
        )

    _recalculate_totals(
        quotation
    )

    db.flush()

    _write_snapshot(
        db,
        quotation,
        reason="item_updated",
        user_id=user_id,
    )

    write_audit_log(
        db,
        action=(
            "quotation.item_updated"
        ),
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values=_json_safe(
            previous_values
        ),
        new_values=_json_safe(
            updates
            | {
                "quotation_total": (
                    quotation.total
                )
            }
        ),
    )

    db.commit()

    return get_quotation(
        db,
        quotation.id,
    )


def deactivate_quotation_item(
    db: Session,
    quotation_id: int,
    item_id: int,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(
        db,
        quotation_id,
    )

    if (
        quotation.status
        in TERMINAL_STATUSES
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "No se pueden eliminar partidas "
                "de una cotizacion en estado terminal"
            ),
        )

    item = next(
        (
            item
            for item
            in quotation.items
            if (
                item.id == item_id
                and item.is_active
            )
        ),
        None,
    )

    if item is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Partida no encontrada",
        )

    previous_values = {
        "service_name": (
            item.service_name
        ),
        "quantity": (
            item.quantity
        ),
        "total": (
            item.total
        ),
        "is_active": (
            item.is_active
        ),
    }

    item.is_active = False
    item.deleted_at = (
        datetime.now(
            timezone.utc
        )
    )
    item.deleted_by = user_id

    _recalculate_totals(
        quotation
    )

    db.flush()

    _write_snapshot(
        db,
        quotation,
        reason="item_deactivated",
        user_id=user_id,
    )

    write_audit_log(
        db,
        action=(
            "quotation.item_deactivated"
        ),
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values=(
            _json_safe(
                previous_values
            )
        ),
        new_values=_json_safe(
            {
                "item_id": (
                    item.id
                ),
                "is_active": False,
                "quotation_total": (
                    quotation.total
                ),
            }
        ),
    )

    db.commit()

    return get_quotation(
        db,
        quotation.id,
    )


def change_quotation_status(
    db: Session,
    quotation_id: int,
    new_status: str,
    payload: (
        QuotationStatusChange
        | None
    ) = None,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(
        db,
        quotation_id,
    )

    allowed = (
        ALLOWED_TRANSITIONS.get(
            quotation.status,
            set(),
        )
    )

    if new_status not in allowed:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Transicion no permitida: "
                f"{quotation.status} -> "
                f"{new_status}"
            ),
        )

    previous_status = (
        quotation.status
    )

    quotation.status = (
        new_status
    )

    action = (
        f"quotation.{new_status}"
        if new_status != "sent"
        else "quotation.sent"
    )

    write_audit_log(
        db,
        action=action,
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values={
            "status": (
                previous_status
            )
        },
        new_values={
            "status": (
                new_status
            )
        },
        comment=(
            payload.comment
            if payload
            else None
        ),
    )

    publish_event(
        db,
        entity_type="quotation",
        entity_id=quotation.id,
        event_code=(
            "quotation.status_changed"
        ),
        idempotency_key=(
            f"quotation:{quotation.id}:"
            f"status:{new_status}"
        ),
        body=(
            "Estado actualizado de "
            f"{previous_status} "
            f"a {new_status}."
        ),
        actor_id=user_id,
        metadata={
            "previous_status": (
                previous_status
            ),
            "status": (
                new_status
            ),
        },
    )

    db.commit()

    return get_quotation(
        db,
        quotation.id,
    )


def deactivate_quotation(
    db: Session,
    quotation_id: int,
    *,
    user_id: int | None = None,
) -> Quotation:
    quotation = get_quotation(
        db,
        quotation_id,
    )

    quotation.is_active = False

    quotation.deleted_at = (
        datetime.now(
            timezone.utc
        )
    )

    quotation.deleted_by = (
        user_id
    )

    write_audit_log(
        db,
        action=(
            "quotation.deactivated"
        ),
        entity="quotations",
        entity_id=quotation.id,
        user_id=user_id,
        previous_values={
            "is_active": True
        },
        new_values={
            "is_active": False
        },
    )

    db.commit()

    return quotation