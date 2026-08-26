from datetime import date, datetime, timezone
from math import ceil
import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.folios import FolioRequest, generate_folio
from app.models.client import Client
from app.models.catalog_item import CatalogItem
from app.models.activity import ActivityAttachment, ActivityMessage, ActivityThread
from app.models.certificate import (
    Certificate,
    CertificateCaptureFile,
    CertificatePdfVersion,
)
from app.models.certificate_resolution_operation import CertificateResolutionOperation
from app.models.equipment import Equipment
from app.models.field_sheet import FieldSheet, FieldSheetResult, FieldSheetSignature
from app.models.invoice import InvoiceItem
from app.models.notification import Notification
from app.models.quotation import Quotation
from app.models.quotation import QuotationItem
from app.models.reference_standard import FieldSheetReferenceStandard
from app.models.service_execution import (
    ServiceStage,
    ServiceStageDocument,
    ServiceTask,
    ServiceTaskAssignee,
    ServiceUnit,
    TechnicalServiceRequest,
)
from app.models.service_order import (
    ServiceOrder,
    ServiceOrderItem,
    ServiceWorkOrder,
    ServiceOrderSignatureCycle,
    ServiceOrderSignatureCycleWorkOrder,
)
from app.models.service_order_exception import ServiceOrderExceptionRequest
from app.models.user import User
from app.models.uncertainty import UncertaintyCalculation
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderExceptionCreate,
    ServiceOrderStatusChange,
    ServiceOrderUpdate,
)
from app.services.audit_logs import write_audit_log
from app.services.activity import publish_event
from app.services.catalog_items import expand_catalog_item_for_operations
from app.services.institutional_folios import next_work_order_number
from app.services.storage_service import (
    count_active_references,
    resolve_storage_path,
    storage_root,
)



TERMINAL_STATUSES = {"closed", "cancelled"}
WORK_ORDER_EQUIPMENT_LIMIT = 10

ALLOWED_TRANSITIONS = {
    "scheduled": {"confirmed", "cancelled"},
    "confirmed": {"called", "in_progress", "cancelled"},
    "called": {"in_progress", "cancelled"},
    "in_progress": {"technical_review", "capture", "cancelled"},
    "technical_review": {"capture", "cancelled"},
    "capture": {"quality_review", "cancelled"},
    "quality_review": {"pending_payment", "released", "cancelled"},
    "pending_payment": {"released", "cancelled"},
    "released": {"closed"},
    "closed": set(),
    "cancelled": set(),
}

STAGE_STATUS_MAP = {
    "info": "confirmed",
    "resumen": "confirmed",
    "equipment": "technical_review",
    "equipos": "technical_review",
    "field-sheet": "technical_review",
    "hojas": "technical_review",
    "capture": "capture",
    "captura": "capture",
    "quality": "quality_review",
    "calidad": "quality_review",
    "certificates": "quality_review",
    "certificados": "quality_review",
    "documents": "released",
    "documentos": "released",
    "billing": "pending_payment",
    "facturacion": "pending_payment",
}


def _require_actor_id(user_id: int) -> int:
    if user_id is None:
        raise ValueError("Las mutaciones ETS requieren un actor")
    return user_id



def _json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _ensure_active_client(db: Session, client_id: int) -> None:
    exists = db.scalar(
        select(Client.id).where(Client.id == client_id, Client.is_active.is_(True))
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")


def _ensure_active_user(db: Session, user_id: int | None, label: str) -> None:
    if user_id is None:
        return
    exists = db.scalar(
        select(User.id).where(User.id == user_id, User.is_active.is_(True))
    )
    if exists is None:
        raise HTTPException(status_code=404, detail=f"{label} no encontrado")


def _get_active_quotation(
    db: Session,
    quotation_id: int | None,
    *,
    for_update: bool = False,
) -> Quotation | None:
    if quotation_id is None:
        return None
    query = (
        select(Quotation)
        .where(Quotation.id == quotation_id, Quotation.is_active.is_(True))
        .options(selectinload(Quotation.items))
    )
    if for_update:
        query = query.with_for_update()
    quotation = db.scalar(query)
    if quotation is None:
        raise HTTPException(status_code=404, detail="Cotizacion no encontrada")
    return quotation


def _next_service_order_folio(db: Session, issued_on: date) -> str:
    prefix = f"OSMYC-{issued_on:%y}-{issued_on:%m}-"
    last_folio = db.scalar(
        select(ServiceOrder.folio)
        .where(ServiceOrder.folio.like(f"{prefix}%"))
        .order_by(ServiceOrder.folio.desc())
        .limit(1)
    )
    sequence = 1 if not last_folio else int(last_folio.rsplit("-", 1)[-1]) + 1
    return generate_folio(
        FolioRequest(
            document_type="orden_servicio",
            issued_on=issued_on,
            sequence=sequence,
        )
    )


def _next_work_order_number(db: Session) -> int:
    return next_work_order_number(db)


def _service_order_source_snapshot(quotation: Quotation | None) -> dict | None:
    if quotation is None:
        return None
    client = quotation.client
    return {
        "schema_version": 1,
        "quotation_folio": quotation.folio,
        "client": {
            "legal_name": client.legal_name,
            "commercial_name": client.commercial_name,
            "rfc": client.rfc,
            "email": client.email,
            "phone": client.phone,
            "address": {
                "street_type": client.street_type,
                "street": client.street,
                "exterior_number": client.exterior_number,
                "interior_number": client.interior_number,
                "neighborhood": client.neighborhood,
                "locality": client.locality,
                "municipality": client.municipality,
                "city": client.city,
                "state": client.state,
                "postal_code": client.postal_code,
                "country": client.country,
            },
            "contacts": [
                {
                    "name": contact.name,
                    "email": contact.email,
                    "phone": contact.phone,
                    "position": contact.position,
                }
                for contact in client.contacts
                if contact.is_active
            ],
        },
        "quotation": {
            "issued_on": quotation.issued_on.isoformat() if quotation.issued_on else None,
            "valid_until": quotation.valid_until.isoformat() if quotation.valid_until else None,
            "payment_terms": quotation.payment_terms,
            "notes": quotation.notes,
        },
    }


def _count_expected_equipment(items: list[ServiceOrderItem]) -> int:
    total = sum(int(item.quantity or 0) for item in items if item.is_active)
    return max(total, 1)


def _build_work_orders_for_service_order(db: Session, service_order: ServiceOrder) -> None:
    expected_equipment = _count_expected_equipment(service_order.items)
    required_work_orders = max(ceil(expected_equipment / WORK_ORDER_EQUIPMENT_LIMIT), 1)

    next_number = _next_work_order_number(db)

    service_order.work_orders = [
        ServiceWorkOrder(
            service_order_id=service_order.id,
            work_order_number=next_number + index,
            sequence=index + 1,
            status="pending",
            equipment_limit=WORK_ORDER_EQUIPMENT_LIMIT,
            notes=None,
        )
        for index in range(required_work_orders)
    ]


def _legacy_expected_certificate_master_id(
    db: Session,
    catalog_item_id: int | None,
) -> int | None:
    """Compatibility lookup only when no quotation snapshot froze the Master."""
    if catalog_item_id is None:
        return None
    return db.scalar(
        select(CatalogItem.expected_certificate_master_id).where(
            CatalogItem.id == catalog_item_id
        )
    )

def _service_order_items_from_quotation(
    db: Session,
    quotation: Quotation,
) -> tuple[list[ServiceOrderItem], list[dict]]:
    operational_items: list[ServiceOrderItem] = []
    expansion_log: list[dict] = []

    for quotation_item in quotation.items:
        if not quotation_item.is_active:
            continue

        snapshot = quotation_item.operational_snapshot or {}
        snapshot_items = snapshot.get("operational_items") or []

        # ============================================================
        # FLUJO CANÓNICO: SNAPSHOT CONGELADO
        # ============================================================
        #
        # Cuando existen operational_items, el ETS debe construirse
        # exclusivamente desde la realidad congelada de la cotización.
        #
        # No se consulta CatalogItem para reinterpretar:
        # - categoría operacional;
        # - Master esperado;
        # - scope;
        # - configuración de Venta;
        # - configuración de Mantenimiento;
        # - identidad del servicio.
        #
        # ============================================================

        if snapshot_items:
            expanded_items: list[dict] = []

            commercial_service_snapshot = (
                snapshot.get("commercial_service_snapshot") or {}
            )

            for snapshot_item in snapshot_items:
                quantity_per_commercial_unit = int(
                    snapshot_item.get("quantity", 1) or 1
                )

                operational_quantity = (
                    quantity_per_commercial_unit
                    * int(quotation_item.quantity or 1)
                )

                service_snapshot = (
                    snapshot_item.get("service_snapshot")
                    or commercial_service_snapshot
                    or {}
                )

                template_snapshot = (
                    service_snapshot.get("template_snapshot") or {}
                )

                # ----------------------------------------------------
                # Categoría operacional
                # ----------------------------------------------------
                #
                # El quotations.py actual congela la clave como:
                #
                #     "operational_category"
                #
                # No como "operational_category_snapshot".
                #
                operational_category = (
                    snapshot_item.get("operational_category")
                    or service_snapshot.get("operational_category")
                    or quotation_item.operational_category
                    or commercial_service_snapshot.get(
                        "operational_category"
                    )
                )

                # ----------------------------------------------------
                # Master esperado
                # ----------------------------------------------------
                #
                # Si la clave existe explícitamente, incluso con None,
                # respetamos ese valor congelado.
                #
                # No debemos consultar el catálogo vivo cuando ya
                # existe snapshot.
                #
                if "expected_certificate_master_id" in snapshot_item:
                    expected_certificate_master_id = snapshot_item.get(
                        "expected_certificate_master_id"
                    )
                elif "expected_certificate_master_id" in template_snapshot:
                    expected_certificate_master_id = template_snapshot.get(
                        "expected_certificate_master_id"
                    )
                else:
                    expected_certificate_master_id = None

                # ----------------------------------------------------
                # Scope
                # ----------------------------------------------------

                calibration_scope = snapshot_item.get("calibration_scope")

                if calibration_scope is None:
                    calibration_scope = service_snapshot.get(
                        "calibration_scope_snapshot"
                    )

                # ----------------------------------------------------
                # Nombre congelado
                # ----------------------------------------------------

                service_name = (
                    snapshot_item.get("service_name")
                    or service_snapshot.get("service_name_snapshot")
                    or quotation_item.service_name
                )

                item_values = {
                    "catalog_item_id": snapshot_item.get("catalog_item_id"),
                    "service_name": service_name,
                    "operational_category": operational_category,
                    "calibration_scope": calibration_scope,
                    "expected_certificate_master_id": (
                        expected_certificate_master_id
                    ),
                    "quantity": operational_quantity,
                    "status": snapshot_item.get("status", "pending"),
                    "service_snapshot": service_snapshot,
                }

                operational_items.append(
                    ServiceOrderItem(
                        quotation_item_id=quotation_item.id,
                        **item_values,
                    )
                )

                expanded_items.append(item_values)

            if snapshot.get("service_kind") == "composite":
                expansion_log.append(
                    {
                        "quotation_item_id": quotation_item.id,
                        "commercial_catalog_item_id": snapshot.get(
                            "commercial_catalog_item_id"
                        ),
                        "commercial_service_name": (
                            snapshot.get("commercial_service_name")
                            or quotation_item.service_name
                        ),
                        "commercial_operational_category": (
                            snapshot.get("commercial_operational_category")
                            or quotation_item.operational_category
                        ),
                        "commercial_quantity": quotation_item.quantity,
                        "snapshot_schema_version": snapshot.get(
                            "schema_version"
                        ),
                        "operational_items": expanded_items,
                    }
                )

            continue

        # ============================================================
        # COMPATIBILIDAD LEGACY
        # ============================================================
        #
        # Sólo partidas antiguas, creadas antes de operational_snapshot,
        # o partidas manuales sin snapshot pueden llegar aquí.
        #
        # En esta ruta sí está permitido consultar CatalogItem porque
        # no existe una realidad operacional histórica congelada.
        #
        # ============================================================

        catalog_item = (
            db.get(
                CatalogItem,
                quotation_item.catalog_item_id,
            )
            if quotation_item.catalog_item_id is not None
            else None
        )

        # ------------------------------------------------------------
        # LEGACY SIMPLE / MANUAL
        # ------------------------------------------------------------

        if catalog_item is None or catalog_item.service_kind == "simple":
            operational_category = quotation_item.operational_category

            if operational_category is None and catalog_item is not None:
                operational_category = catalog_item.operational_category

            expected_certificate_master_id = (
                _legacy_expected_certificate_master_id(
                    db,
                    catalog_item.id,
                )
                if catalog_item is not None
                else None
            )

            legacy_service_snapshot = (
                snapshot.get("commercial_service_snapshot") or None
            )

            operational_items.append(
                ServiceOrderItem(
                    quotation_item_id=quotation_item.id,
                    catalog_item_id=quotation_item.catalog_item_id,
                    service_name=quotation_item.service_name,
                    operational_category=operational_category,
                    calibration_scope=quotation_item.calibration_scope,
                    expected_certificate_master_id=(
                        expected_certificate_master_id
                    ),
                    quantity=quotation_item.quantity,
                    status="pending",
                    service_snapshot=legacy_service_snapshot,
                )
            )

            expansion_log.append(
                {
                    "quotation_item_id": quotation_item.id,
                    "commercial_catalog_item_id": (
                        quotation_item.catalog_item_id
                    ),
                    "commercial_service_name": quotation_item.service_name,
                    "commercial_quantity": quotation_item.quantity,
                    "snapshot_schema_version": snapshot.get(
                        "schema_version"
                    ),
                    "legacy_catalog_fallback": catalog_item is not None,
                }
            )

            continue

        # ------------------------------------------------------------
        # LEGACY COMPUESTO
        # ------------------------------------------------------------

        legacy_expanded = expand_catalog_item_for_operations(
            db,
            catalog_item.id,
            quotation_item.quantity,
        )

        normalized_legacy_items: list[dict] = []

        for legacy_item in legacy_expanded:
            item_values = dict(legacy_item)

            component_catalog_item_id = item_values.get(
                "catalog_item_id"
            )

            component_catalog_item = (
                db.get(
                    CatalogItem,
                    component_catalog_item_id,
                )
                if component_catalog_item_id is not None
                else None
            )

            if item_values.get("operational_category") is None:
                item_values["operational_category"] = (
                    component_catalog_item.operational_category
                    if component_catalog_item is not None
                    else None
                )

            if "expected_certificate_master_id" not in item_values:
                item_values["expected_certificate_master_id"] = (
                    _legacy_expected_certificate_master_id(
                        db,
                        component_catalog_item_id,
                    )
                )

            operational_items.append(
                ServiceOrderItem(
                    quotation_item_id=quotation_item.id,
                    **item_values,
                )
            )

            normalized_legacy_items.append(item_values)

        expansion_log.append(
            {
                "quotation_item_id": quotation_item.id,
                "commercial_catalog_item_id": catalog_item.id,
                "commercial_service_name": quotation_item.service_name,
                "commercial_quantity": quotation_item.quantity,
                "snapshot_schema_version": None,
                "legacy_catalog_expansion": True,
                "operational_items": normalized_legacy_items,
            }
        )

    return operational_items, expansion_log

def list_service_orders(
    db: Session,
    *,
    include_inactive: bool = False,
    client_id: int | None = None,
) -> list[ServiceOrder]:
    query = (
        select(ServiceOrder)
        .options(
            selectinload(ServiceOrder.items),
            selectinload(ServiceOrder.work_orders).selectinload(
                ServiceWorkOrder.signature_cycle_links
            ),
            selectinload(ServiceOrder.equipment),
            selectinload(ServiceOrder.client).selectinload(Client.contacts),
            selectinload(ServiceOrder.quotation),
            selectinload(ServiceOrder.certificates),
            selectinload(ServiceOrder.advisor),
            selectinload(ServiceOrder.technician),
        )
        .order_by(ServiceOrder.created_at.desc())
    )
    if not include_inactive:
        query = query.where(ServiceOrder.is_active.is_(True))
    if client_id is not None:
        query = query.where(ServiceOrder.client_id == client_id)
    return list(db.scalars(query).all())


def get_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    service_order = db.scalar(
        select(ServiceOrder)
        .where(ServiceOrder.id == service_order_id)
        .options(
            selectinload(ServiceOrder.items),
            selectinload(ServiceOrder.work_orders).selectinload(
                ServiceWorkOrder.signature_cycle_links
            ),
            selectinload(ServiceOrder.equipment),
            selectinload(ServiceOrder.client).selectinload(Client.contacts),
            selectinload(ServiceOrder.quotation),
            selectinload(ServiceOrder.certificates),
            selectinload(ServiceOrder.advisor),
            selectinload(ServiceOrder.technician),
        )
    )
    if service_order is None or not service_order.is_active:
        raise HTTPException(status_code=404, detail="Orden de servicio no encontrada")
    return service_order


def create_service_order(
    db: Session,
    payload: ServiceOrderCreate,
    *,
    user_id: int,
    commit: bool = True,
) -> ServiceOrder:
    user_id = _require_actor_id(user_id)

    # ------------------------------------------------------------
    # Idempotencia por cotización
    # ------------------------------------------------------------

    quotation = _get_active_quotation(
        db,
        payload.quotation_id,
        for_update=payload.quotation_id is not None,
    )

    if payload.quotation_id is not None:
        existing_order_id = db.scalar(
            select(ServiceOrder.id)
            .where(
                ServiceOrder.quotation_id == payload.quotation_id,
                ServiceOrder.is_active.is_(True),
            )
            .order_by(ServiceOrder.id.asc())
            .limit(1)
        )

        if existing_order_id is not None:
            return get_service_order(
                db,
                existing_order_id,
            )

        inactive_order_id = db.scalar(
            select(ServiceOrder.id)
            .where(
                ServiceOrder.quotation_id == payload.quotation_id,
                ServiceOrder.is_active.is_(False),
            )
            .order_by(ServiceOrder.id.asc())
            .limit(1)
        )
        if inactive_order_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "inactive_service_order_requires_resolution",
                    "message": (
                        "La cotización conserva un ETS inactivo. Use el Centro "
                        "de Resoluciones para restaurarlo o determinar una reconstrucción."
                    ),
                    "service_order_id": inactive_order_id,
                },
            )

    # ------------------------------------------------------------
    # Validaciones
    # ------------------------------------------------------------

    _ensure_active_client(
        db,
        payload.client_id,
    )

    _ensure_active_user(
        db,
        payload.advisor_id,
        "Asesor",
    )

    _ensure_active_user(
        db,
        payload.technician_id,
        "Tecnico",
    )

    if (
        quotation is not None
        and quotation.client_id != payload.client_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "La cotizacion no pertenece "
                "al cliente indicado"
            ),
        )

    # ------------------------------------------------------------
    # Cabecera ETS
    # ------------------------------------------------------------

    primary_work_order_number = _next_work_order_number(db)

    service_order = ServiceOrder(
        folio=_next_service_order_folio(
            db,
            date.today(),
        ),
        work_order_number=primary_work_order_number,
        client_id=payload.client_id,
        quotation_id=payload.quotation_id,
        advisor_id=payload.advisor_id,
        technician_id=payload.technician_id,
        agenda_date=payload.agenda_date,
        service_date=payload.service_date,
        total_equipment=payload.total_equipment,
        completed_equipment=payload.completed_equipment,
        requires_payment=payload.requires_payment,
        notes=payload.notes,
        source_snapshot=_service_order_source_snapshot(
            quotation
        ),
        status="scheduled",
    )

    expansion_log: list[dict] = []

    # ============================================================
    # AUTORIDAD DE PARTIDAS
    # ============================================================
    #
    # Cotización vinculada:
    #     la cotización congelada es la autoridad.
    #
    # ETS sin cotización:
    #     se permiten payload.items y, al no existir snapshot
    #     comercial previo, puede consultarse el catálogo durante
    #     esta creación.
    #
    # Esto evita que frontend pueda sustituir silenciosamente la
    # identidad operacional de una cotización ya aprobada.
    #
    # ============================================================

    if quotation is not None:
        (
            service_order.items,
            expansion_log,
        ) = _service_order_items_from_quotation(
            db,
            quotation,
        )

        incomplete_verification = next(
            (
                item
                for item in service_order.items
                if item.operational_category == "verification"
                and item.expected_certificate_master_id is None
            ),
            None,
        )
        if incomplete_verification is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "La cotización contiene una partida histórica de Verificación "
                    "sin Master genérico. Corrige el concepto y sustituye explícitamente "
                    "la partida antes de materializar el ETS."
                ),
            )

    elif payload.items:
        direct_items: list[ServiceOrderItem] = []

        for item in payload.items:
            item_values = item.model_dump(
                exclude={
                    "operational_category",
                }
            )

            catalog_item = (
                db.get(
                    CatalogItem,
                    item.catalog_item_id,
                )
                if item.catalog_item_id is not None
                else None
            )

            operational_category = (
                item.operational_category
                or (
                    catalog_item.operational_category
                    if catalog_item is not None
                    else None
                )
            )

            expected_certificate_master_id = (
                _legacy_expected_certificate_master_id(
                    db,
                    item.catalog_item_id,
                )
            )

            direct_items.append(
                ServiceOrderItem(
                    **item_values,
                    operational_category=operational_category,
                    expected_certificate_master_id=(
                        expected_certificate_master_id
                    ),
                )
            )

        service_order.items = direct_items

    # ------------------------------------------------------------
    # Persistencia inicial
    # ------------------------------------------------------------

    db.add(service_order)
    db.flush()

    # ------------------------------------------------------------
    # Órdenes de trabajo
    # ------------------------------------------------------------

    _build_work_orders_for_service_order(
        db,
        service_order,
    )

    db.flush()

    # ------------------------------------------------------------
    # Inicialización de verticales ETS
    # ------------------------------------------------------------

    from app.services.maintenance_execution import (
        initialize_maintenance_execution,
    )
    from app.services.repair_execution import (
        initialize_repair_execution,
    )
    from app.services.sale_execution import (
        initialize_sale_execution,
    )

    initialize_sale_execution(
        db,
        service_order,
        user_id=user_id,
    )

    initialize_maintenance_execution(
        db,
        service_order,
        user_id=user_id,
    )

    initialize_repair_execution(
        db,
        service_order,
        user_id=user_id,
    )

    db.flush()

    # ------------------------------------------------------------
    # Auditoría
    # ------------------------------------------------------------

    write_audit_log(
        db,
        action="service_order.created",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        new_values={
            "folio": service_order.folio,
            "work_order_number": (
                service_order.work_order_number
            ),
            "work_orders": [
                {
                    "id": work_order.id,
                    "work_order_number": (
                        work_order.work_order_number
                    ),
                    "sequence": work_order.sequence,
                    "equipment_limit": (
                        work_order.equipment_limit
                    ),
                }
                for work_order in service_order.work_orders
            ],
            "client_id": service_order.client_id,
            "quotation_id": service_order.quotation_id,
            "status": service_order.status,
            "composite_service_expansions": (
                expansion_log
            ),
        },
    )

    if commit:
        db.commit()
    else:
        db.flush()

    return get_service_order(
        db,
        service_order.id,
    )

def update_service_order(
    db: Session,
    service_order_id: int,
    payload: ServiceOrderUpdate,
    *,
    user_id: int,
) -> ServiceOrder:
    user_id = _require_actor_id(user_id)
    service_order = get_service_order(db, service_order_id)
    if service_order.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede editar una orden de servicio cerrada o cancelada",
        )

    updates = payload.model_dump(exclude_unset=True)
    signature_fields = [
        (
            "technician_signature_data_url",
            "technician_signed_at",
        ),
        (
            "client_received_signature_data_url",
            "client_received_signed_at",
        ),
        (
            "client_acceptance_signature_data_url",
            "client_acceptance_signed_at",
        ),
    ]

    for signature_field, signed_at_field in signature_fields:
        if signature_field in updates:
            updates[signed_at_field] = (
                datetime.now(timezone.utc)
                if updates[signature_field]
                else None
            )
    _ensure_active_user(db, updates.get("advisor_id"), "Asesor")
    _ensure_active_user(db, updates.get("technician_id"), "Tecnico")

    previous_values = {key: getattr(service_order, key) for key in updates}

    for key, value in updates.items():
        setattr(service_order, key, value)

    if (
        service_order.status == "scheduled"
        and service_order.agenda_date
        and service_order.service_date
        and service_order.technician_id
    ):
        previous_values.setdefault("status", "scheduled")
        updates["status"] = "confirmed"
        service_order.status = "confirmed"

    write_audit_log(
        db,
        action="service_order.updated",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values=_json_safe(previous_values),
        new_values=_json_safe(updates),
    )
    db.commit()
    return get_service_order(db, service_order.id)

def confirm_signature_cycle(
    db: Session,
    service_order_id: int,
    *,
    user_id: int,
) -> ServiceOrder:
    user_id = _require_actor_id(user_id)
    service_order = get_service_order(db, service_order_id)

    required_signature_fields = {
        "technician_signature_data_url": service_order.technician_signature_data_url,
        "client_received_signature_data_url": (
            service_order.client_received_signature_data_url
        ),
        "client_acceptance_signature_data_url": (
            service_order.client_acceptance_signature_data_url
        ),
        "technician_signed_name": service_order.technician_signed_name,
        "client_received_signed_name": service_order.client_received_signed_name,
        "client_acceptance_signed_name": (
            service_order.client_acceptance_signed_name
        ),
        "technician_signed_at": service_order.technician_signed_at,
        "client_received_signed_at": service_order.client_received_signed_at,
        "client_acceptance_signed_at": (
            service_order.client_acceptance_signed_at
        ),
    }

    missing_fields = [
        field_name
        for field_name, field_value in required_signature_fields.items()
        if not field_value
    ]

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No se pueden confirmar las firmas porque faltan datos: "
                + ", ".join(missing_fields)
            ),
        )

    active_work_orders = list(
        db.scalars(
            select(ServiceWorkOrder)
            .where(
                ServiceWorkOrder.service_order_id == service_order.id,
                ServiceWorkOrder.is_active.is_(True),
                ServiceWorkOrder.status != "cancelled",
            )
            .order_by(ServiceWorkOrder.sequence.asc())
        ).all()
    )

    if not active_work_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La orden de servicio no tiene órdenes de trabajo activas",
        )

    active_work_order_ids = [work_order.id for work_order in active_work_orders]

    already_signed_work_order_ids = set(
        db.scalars(
            select(ServiceOrderSignatureCycleWorkOrder.work_order_id).where(
                ServiceOrderSignatureCycleWorkOrder.work_order_id.in_(
                    active_work_order_ids
                ),
                ServiceOrderSignatureCycleWorkOrder.is_current.is_(True),
            )
        ).all()
    )

    pending_work_orders = [
        work_order
        for work_order in active_work_orders
        if work_order.id not in already_signed_work_order_ids
    ]

    if not pending_work_orders:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Todas las órdenes de trabajo activas ya tienen una firma vigente"
            ),
        )

    last_cycle_number = db.scalar(
        select(func.max(ServiceOrderSignatureCycle.cycle_number)).where(
            ServiceOrderSignatureCycle.service_order_id == service_order.id
        )
    )

    next_cycle_number = int(last_cycle_number or 0) + 1
    confirmed_at = datetime.now(timezone.utc)

    trigger = "initial" if next_cycle_number == 1 else "additional_work_order"

    signature_cycle = ServiceOrderSignatureCycle(
        service_order_id=service_order.id,
        cycle_number=next_cycle_number,
        trigger=trigger,
        comment=None,
        status="confirmed",
        technician_signature_data_url=(
            service_order.technician_signature_data_url
        ),
        client_received_signature_data_url=(
            service_order.client_received_signature_data_url
        ),
        client_acceptance_signature_data_url=(
            service_order.client_acceptance_signature_data_url
        ),
        technician_signed_name=service_order.technician_signed_name,
        client_received_signed_name=(
            service_order.client_received_signed_name
        ),
        client_acceptance_signed_name=(
            service_order.client_acceptance_signed_name
        ),
        technician_signed_at=service_order.technician_signed_at,
        client_received_signed_at=service_order.client_received_signed_at,
        client_acceptance_signed_at=(
            service_order.client_acceptance_signed_at
        ),
        authorized_by_id=(
            user_id if trigger != "initial" else None
        ),
        authorization_comment=None,
        confirmed_at=confirmed_at,
    )

    db.add(signature_cycle)
    db.flush()

    assignment_type = (
        "initial"
        if next_cycle_number == 1
        else "additional_work_order"
    )

    signature_links = [
        ServiceOrderSignatureCycleWorkOrder(
            signature_cycle_id=signature_cycle.id,
            work_order_id=work_order.id,
            assignment_type=assignment_type,
            is_current=True,
            applied_at=confirmed_at,
        )
        for work_order in pending_work_orders
    ]

    db.add_all(signature_links)

    previous_signature_status = service_order.signature_status
    previous_cycle_number = service_order.signature_cycle_number

    service_order.signature_status = "confirmed"
    service_order.signature_cycle_number = next_cycle_number
    service_order.signatures_confirmed_at = confirmed_at
    service_order.signature_reopen_available = False
    service_order.signature_reopened_by_id = None
    service_order.signature_reopened_at = None
    service_order.signature_reopen_source = None

    write_audit_log(
        db,
        action="service_order.signatures_confirmed",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values={
            "signature_status": previous_signature_status,
            "signature_cycle_number": previous_cycle_number,
        },
        new_values={
            "signature_status": "confirmed",
            "signature_cycle_number": next_cycle_number,
            "signature_cycle_id": signature_cycle.id,
            "trigger": trigger,
            "work_orders": [
                {
                    "id": work_order.id,
                    "work_order_number": work_order.work_order_number,
                    "sequence": work_order.sequence,
                }
                for work_order in pending_work_orders
            ],
            "confirmed_at": confirmed_at.isoformat(),
        },
    )

    db.commit()

    return get_service_order(db, service_order.id)


def change_status(
    db: Session,
    service_order_id: int,
    new_status: str,
    payload: ServiceOrderStatusChange | None = None,
    *,
    user_id: int,
) -> ServiceOrder:
    user_id = _require_actor_id(user_id)
    service_order = get_service_order(db, service_order_id)
    allowed = ALLOWED_TRANSITIONS.get(service_order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transicion no permitida: {service_order.status} -> {new_status}",
        )

    previous_status = service_order.status
    service_order.status = new_status

    if new_status == "closed":
        service_order.closed_at = date.today()

    write_audit_log(
        db,
        action=f"service_order.{new_status}",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values={"status": previous_status},
        new_values={"status": new_status},
        comment=payload.comment if payload else None,
    )
    publish_event(
        db,
        entity_type="service_order",
        entity_id=service_order.id,
        event_code="service_order.status_changed",
        idempotency_key=f"service_order:{service_order.id}:status:{new_status}",
        body=f"Estado del ETS actualizado de {previous_status} a {new_status}.",
        actor_id=user_id,
        metadata={"previous_status": previous_status, "status": new_status},
    )
    db.commit()
    return get_service_order(db, service_order.id)


def close_service_order(
    db: Session,
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    *,
    user_id: int,
) -> ServiceOrder:
    return change_status(db, service_order_id, "closed", payload, user_id=user_id)


def request_service_order_exception(
    db: Session,
    service_order_id: int,
    payload: ServiceOrderExceptionCreate,
    *,
    user_id: int,
) -> ServiceOrderExceptionRequest:
    user_id = _require_actor_id(user_id)
    service_order = get_service_order(db, service_order_id)
    source_stage = payload.source_stage.strip()
    target_stage = payload.target_stage.strip()
    target_status = STAGE_STATUS_MAP.get(target_stage.lower())
    exception_request = ServiceOrderExceptionRequest(
        service_order_id=service_order.id,
        requested_by_id=user_id,
        status="requested",
        source_stage=source_stage,
        target_stage=target_stage,
        target_status=target_status,
        service_order_status_at_request=service_order.status,
        reason=payload.reason.strip(),
    )
    db.add(exception_request)
    db.flush()

    write_audit_log(
        db,
        action="service_order.exception_requested",
        entity="service_order_exceptions",
        entity_id=exception_request.id,
        user_id=user_id,
        previous_values=None,
        new_values={
            "status": "requested",
            "service_order_id": service_order.id,
            "service_order_status": service_order.status,
            "source_stage": source_stage,
            "target_stage": target_stage,
            "target_status": target_status,
        },
        comment=payload.reason,
    )
    publish_event(
        db,
        entity_type="service_order",
        entity_id=service_order.id,
        event_code="service_order.exception_requested",
        idempotency_key=f"service_order_exception:{exception_request.id}:requested",
        body=f"Excepción solicitada de {source_stage} a {target_stage}.",
        actor_id=user_id,
        metadata={
            "exception_id": exception_request.id,
            "status": "requested",
            "source_stage": source_stage,
            "target_stage": target_stage,
            "target_status": target_status,
            "service_order_status": service_order.status,
        },
    )
    db.commit()
    db.refresh(exception_request)
    return exception_request


def _get_service_order_exception(
    db: Session,
    service_order_id: int,
    exception_id: int,
    *,
    for_update: bool = False,
) -> ServiceOrderExceptionRequest:
    query = select(ServiceOrderExceptionRequest).where(
        ServiceOrderExceptionRequest.id == exception_id,
        ServiceOrderExceptionRequest.service_order_id == service_order_id,
    )
    if for_update:
        query = query.with_for_update()
    exception_request = db.scalar(query)
    if exception_request is None:
        raise HTTPException(
            status_code=404, detail="Solicitud de excepción no encontrada"
        )
    return exception_request


def authorize_service_order_exception(
    db: Session,
    service_order_id: int,
    exception_id: int,
    *,
    user_id: int,
    comment: str | None = None,
) -> ServiceOrderExceptionRequest:
    user_id = _require_actor_id(user_id)
    exception_request = _get_service_order_exception(
        db, service_order_id, exception_id, for_update=True
    )
    if exception_request.status != "requested":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo una solicitud en estado requested puede autorizarse",
        )
    authorized_at = datetime.now(timezone.utc)
    exception_request.status = "authorized"
    exception_request.authorized_by_id = user_id
    exception_request.authorized_at = authorized_at
    exception_request.authorization_comment = comment
    write_audit_log(
        db,
        action="service_order.exception_authorized",
        entity="service_order_exceptions",
        entity_id=exception_request.id,
        user_id=user_id,
        previous_values={"status": "requested"},
        new_values={
            "status": "authorized",
            "authorized_by_id": user_id,
            "authorized_at": authorized_at.isoformat(),
        },
        comment=comment,
    )
    publish_event(
        db,
        entity_type="service_order",
        entity_id=service_order_id,
        event_code="service_order.exception_authorized",
        idempotency_key=f"service_order_exception:{exception_request.id}:authorized",
        body=(
            f"Excepción autorizada de {exception_request.source_stage} "
            f"a {exception_request.target_stage}."
        ),
        actor_id=user_id,
        metadata={"exception_id": exception_request.id, "status": "authorized"},
    )
    db.commit()
    db.refresh(exception_request)
    return exception_request


def execute_service_order_exception(
    db: Session,
    service_order_id: int,
    exception_id: int,
    *,
    user_id: int,
) -> ServiceOrderExceptionRequest:
    user_id = _require_actor_id(user_id)
    exception_request = _get_service_order_exception(
        db, service_order_id, exception_id, for_update=True
    )
    if exception_request.status != "authorized":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo una excepción autorizada puede ejecutarse",
        )
    service_order = get_service_order(db, service_order_id)
    previous_status = service_order.status
    if previous_status != exception_request.service_order_status_at_request:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El ETS cambió desde la solicitud; la excepción debe reevaluarse",
        )
    if exception_request.target_status and previous_status not in TERMINAL_STATUSES:
        service_order.status = exception_request.target_status

    # Las facturas derivadas solo se resincronizan en la ejecución autorizada.
    from app.services.invoices import resync_invoices_for_service_exception

    resync_invoices_for_service_exception(
        db,
        service_order.id,
        comment=exception_request.reason,
        user_id=user_id,
    )
    executed_at = datetime.now(timezone.utc)
    exception_request.status = "executed"
    exception_request.executed_by_id = user_id
    exception_request.executed_at = executed_at
    write_audit_log(
        db,
        action="service_order.exception_executed",
        entity="service_order_exceptions",
        entity_id=exception_request.id,
        user_id=user_id,
        previous_values={
            "status": "authorized",
            "service_order_status": previous_status,
        },
        new_values={
            "status": "executed",
            "service_order_status": service_order.status,
            "executed_by_id": user_id,
            "executed_at": executed_at.isoformat(),
        },
        comment=exception_request.reason,
    )
    publish_event(
        db,
        entity_type="service_order",
        entity_id=service_order.id,
        event_code="service_order.exception_executed",
        idempotency_key=f"service_order_exception:{exception_request.id}:executed",
        body=(
            f"Excepción ejecutada de {exception_request.source_stage} "
            f"a {exception_request.target_stage}."
        ),
        actor_id=user_id,
        metadata={
            "exception_id": exception_request.id,
            "status": "executed",
            "previous_status": previous_status,
            "service_order_status": service_order.status,
        },
    )
    db.commit()
    db.refresh(exception_request)
    return exception_request


def deactivate_service_order(
    db: Session, service_order_id: int, *, user_id: int
) -> ServiceOrder:
    _require_actor_id(user_id)
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "administrative_resolution_required",
            "message": (
                "La baja de un ETS sólo puede ejecutarse mediante una "
                "resolución administrativa autorizada."
            ),
            "service_order_id": service_order_id,
        },
    )


def delete_service_work_order(
    db: Session, work_order_id: int, *, user_id: int
) -> None:
    """Delete one productive OT and only the operational records it owns.

    The parent ETS, commercial/financial records, master catalogs, users,
    resolution aggregates and signature cycles still used by another OT are
    shared resources and are therefore retained.  All database mutations and
    the minimal audit event are committed as one transaction.
    """
    user_id = _require_actor_id(user_id)
    work_order = db.scalar(
        select(ServiceWorkOrder)
        .where(ServiceWorkOrder.id == work_order_id)
        .with_for_update()
    )
    if work_order is None:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")

    service_order = db.scalar(
        select(ServiceOrder)
        .where(ServiceOrder.id == work_order.service_order_id)
        .with_for_update()
    )
    if service_order is None:
        raise HTTPException(status_code=409, detail="La OT no tiene un ETS válido")

    equipment_ids = set(
        db.scalars(
            select(Equipment.id).where(Equipment.work_order_id == work_order.id)
        ).all()
    )
    field_sheet_ids = set(
        db.scalars(
            select(FieldSheet.id).where(
                or_(
                    FieldSheet.work_order_id == work_order.id,
                    FieldSheet.equipment_id.in_(equipment_ids) if equipment_ids else False,
                )
            )
        ).all()
    )
    certificate_ids = set(
        db.scalars(
            select(Certificate.id).where(
                or_(
                    Certificate.equipment_id.in_(equipment_ids) if equipment_ids else False,
                    Certificate.field_sheet_id.in_(field_sheet_ids) if field_sheet_ids else False,
                )
            )
        ).all()
    )

    protected_operations = 0
    if certificate_ids:
        protected_operations = int(
            db.scalar(
                select(func.count(CertificateResolutionOperation.id)).where(
                    CertificateResolutionOperation.certificate_id.in_(certificate_ids)
                )
            )
            or 0
        )
    if protected_operations:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WORK_ORDER_DELETE_BLOCKED",
                "message": "La OT contiene certificados con evidencia inmutable del Motor de Resoluciones.",
                "blocking_dependencies": {
                    "certificate_resolution_operations": protected_operations
                },
            },
        )

    file_references: set[tuple[str, str | None, int | None]] = set()
    if certificate_ids:
        for certificate in db.scalars(
            select(Certificate).where(Certificate.id.in_(certificate_ids))
        ):
            file_references.add(
                (certificate.final_pdf_path or "", certificate.final_pdf_original_filename, certificate.id)
            )
            file_references.add(
                (certificate.authenticated_pdf_path or "", None, certificate.id)
            )
        for version in db.scalars(
            select(CertificatePdfVersion).where(
                CertificatePdfVersion.certificate_id.in_(certificate_ids)
            )
        ):
            file_references.add((version.file_path, version.original_filename, version.certificate_id))
        for capture_file in db.scalars(
            select(CertificateCaptureFile).where(
                CertificateCaptureFile.certificate_id.in_(certificate_ids)
            )
        ):
            file_references.add(
                (capture_file.stored_path or "", capture_file.original_filename, capture_file.certificate_id)
            )

    signature_cycle_ids = set(
        db.scalars(
            select(ServiceOrderSignatureCycleWorkOrder.signature_cycle_id).where(
                ServiceOrderSignatureCycleWorkOrder.work_order_id == work_order.id
            )
        ).all()
    )
    thread_ids = set(
        db.scalars(
            select(ActivityThread.id).where(
                ActivityThread.entity_type.in_(("work_order", "service_work_order")),
                ActivityThread.entity_id == work_order.id,
            )
        ).all()
    )
    activity_message_ids = set(
        db.scalars(
            select(ActivityMessage.id).where(ActivityMessage.thread_id.in_(thread_ids))
        ).all()
    ) if thread_ids else set()
    if activity_message_ids:
        for attachment in db.scalars(
            select(ActivityAttachment).where(
                ActivityAttachment.message_id.in_(activity_message_ids)
            )
        ):
            file_references.add(
                (attachment.stored_path, attachment.original_name, None)
            )
    service_unit_ids = set(
        db.scalars(
            select(ServiceUnit.id).where(ServiceUnit.work_order_id == work_order.id)
        ).all()
    )
    service_stage_ids = set(
        db.scalars(
            select(ServiceStage.id).where(
                ServiceStage.service_unit_id.in_(service_unit_ids)
            )
        ).all()
    ) if service_unit_ids else set()
    technical_request_ids = set(
        db.scalars(
            select(TechnicalServiceRequest.id).where(
                or_(
                    TechnicalServiceRequest.service_unit_id.in_(service_unit_ids)
                    if service_unit_ids else False,
                    TechnicalServiceRequest.source_stage_id.in_(service_stage_ids)
                    if service_stage_ids else False,
                    TechnicalServiceRequest.source_message_id.in_(activity_message_ids)
                    if activity_message_ids else False,
                )
            )
        ).all()
    )
    task_ids = set(
        db.scalars(
            select(ServiceTask.id).where(
                or_(
                    ServiceTask.service_unit_id.in_(service_unit_ids)
                    if service_unit_ids else False,
                    ServiceTask.service_stage_id.in_(service_stage_ids)
                    if service_stage_ids else False,
                    ServiceTask.source_message_id.in_(activity_message_ids)
                    if activity_message_ids else False,
                )
            )
        ).all()
    )

    staged_files: list[tuple[Path, Path]] = []
    try:
        # Financial and commercial evidence is shared: detach nullable pointers.
        if equipment_ids or certificate_ids:
            db.execute(
                update(InvoiceItem)
                .where(
                    or_(
                        InvoiceItem.equipment_id.in_(equipment_ids) if equipment_ids else False,
                        InvoiceItem.certificate_id.in_(certificate_ids) if certificate_ids else False,
                    )
                )
                .values(equipment_id=None, certificate_id=None)
            )
        if technical_request_ids or service_unit_ids or service_stage_ids:
            db.execute(
                update(QuotationItem)
                .where(
                    or_(
                        QuotationItem.technical_request_id.in_(technical_request_ids)
                        if technical_request_ids else False,
                        QuotationItem.source_service_unit_id.in_(service_unit_ids)
                        if service_unit_ids else False,
                        QuotationItem.source_stage_id.in_(service_stage_ids)
                        if service_stage_ids else False,
                    )
                )
                .values(
                    technical_request_id=None,
                    source_service_unit_id=None,
                    source_stage_id=None,
                )
            )
        if service_stage_ids:
            db.execute(
                update(ServiceStage)
                .where(
                    ServiceStage.source_stage_id.in_(service_stage_ids),
                    ServiceStage.id.not_in(service_stage_ids),
                )
                .values(source_stage_id=None)
            )

        if certificate_ids:
            db.execute(delete(CertificateCaptureFile).where(CertificateCaptureFile.certificate_id.in_(certificate_ids)))
            db.execute(delete(CertificatePdfVersion).where(CertificatePdfVersion.certificate_id.in_(certificate_ids)))
            db.execute(delete(Certificate).where(Certificate.id.in_(certificate_ids)))
        if field_sheet_ids:
            db.execute(delete(UncertaintyCalculation).where(UncertaintyCalculation.field_sheet_id.in_(field_sheet_ids)))
            db.execute(delete(FieldSheetReferenceStandard).where(FieldSheetReferenceStandard.field_sheet_id.in_(field_sheet_ids)))
            db.execute(delete(FieldSheetResult).where(FieldSheetResult.field_sheet_id.in_(field_sheet_ids)))
            db.execute(delete(FieldSheetSignature).where(FieldSheetSignature.field_sheet_id.in_(field_sheet_ids)))
            db.execute(delete(FieldSheet).where(FieldSheet.id.in_(field_sheet_ids)))
        if task_ids:
            db.execute(delete(ServiceTaskAssignee).where(ServiceTaskAssignee.task_id.in_(task_ids)))
            db.execute(delete(ServiceTask).where(ServiceTask.id.in_(task_ids)))
        if technical_request_ids:
            db.execute(delete(TechnicalServiceRequest).where(TechnicalServiceRequest.id.in_(technical_request_ids)))
        if service_stage_ids:
            db.execute(delete(ServiceStageDocument).where(ServiceStageDocument.service_stage_id.in_(service_stage_ids)))
            db.execute(delete(ServiceStage).where(ServiceStage.id.in_(service_stage_ids)))
        if service_unit_ids:
            db.execute(delete(ServiceUnit).where(ServiceUnit.id.in_(service_unit_ids)))
        if equipment_ids:
            db.execute(delete(Equipment).where(Equipment.id.in_(equipment_ids)))

        now = datetime.now(timezone.utc)
        db.execute(
            update(Notification)
            .where(
                Notification.entity_type.in_(("work_order", "service_work_order")),
                Notification.entity_id == work_order.id,
                Notification.revoked_at.is_(None),
            )
            .values(revoked_at=now, read_at=now, dismissed_at=now)
        )
        if activity_message_ids:
            db.execute(
                update(Notification)
                .where(Notification.activity_message_id.in_(activity_message_ids))
                .values(
                    activity_message_id=None,
                    revoked_at=now,
                    read_at=now,
                    dismissed_at=now,
                )
            )
        if thread_ids:
            for thread in db.scalars(
                select(ActivityThread).where(ActivityThread.id.in_(thread_ids))
            ):
                db.delete(thread)

        db.execute(
            delete(ServiceOrderSignatureCycleWorkOrder).where(
                ServiceOrderSignatureCycleWorkOrder.work_order_id == work_order.id
            )
        )
        db.flush()
        if signature_cycle_ids:
            unreferenced_cycle_ids = set(
                db.scalars(
                    select(ServiceOrderSignatureCycle.id)
                    .where(ServiceOrderSignatureCycle.id.in_(signature_cycle_ids))
                    .where(
                        ~ServiceOrderSignatureCycle.work_order_links.any()
                    )
                ).all()
            )
            if unreferenced_cycle_ids:
                db.execute(
                    delete(ServiceOrderSignatureCycle).where(
                        ServiceOrderSignatureCycle.id.in_(unreferenced_cycle_ids)
                    )
                )

        db.execute(delete(ServiceWorkOrder).where(ServiceWorkOrder.id == work_order.id))
        remaining = db.scalar(
            select(ServiceWorkOrder)
            .where(ServiceWorkOrder.service_order_id == service_order.id)
            .order_by(ServiceWorkOrder.sequence.asc(), ServiceWorkOrder.id.asc())
            .limit(1)
        )
        if remaining is not None and service_order.work_order_number == work_order.work_order_number:
            service_order.work_order_number = remaining.work_order_number
        service_order.total_equipment = max(service_order.total_equipment - len(equipment_ids), 0)
        service_order.completed_equipment = min(
            service_order.completed_equipment,
            service_order.total_equipment,
        )

        write_audit_log(
            db,
            action="service_work_order.deleted",
            entity="service_work_orders",
            entity_id=work_order.id,
            user_id=user_id,
            previous_values={
                "work_order_number": work_order.work_order_number,
                "service_order_id": service_order.id,
            },
            new_values={"deleted": True},
            comment="Eliminación administrativa completa de la OT productiva.",
        )
        db.flush()
        staging_directory = (
            storage_root()
            / ".pending-deletions"
            / f"work-order-{work_order.id}-{uuid4().hex}"
        )
        for index, (path, _filename, _certificate_id) in enumerate(
            sorted(file_references, key=lambda item: (item[0], item[1] or "", item[2] or 0))
        ):
            if not path:
                continue
            resolved = resolve_storage_path(path)
            if (
                resolved is None
                or resolved.is_symlink()
                or not resolved.is_file()
                or count_active_references(db, resolved) > 0
            ):
                continue
            staging_directory.mkdir(parents=True, exist_ok=True)
            staged = staging_directory / f"{index}-{resolved.name}"
            os.replace(resolved, staged)
            staged_files.append((resolved, staged))
        db.commit()
        for _original, staged in staged_files:
            try:
                staged.unlink(missing_ok=True)
            except OSError:
                # The file is already outside every deliverable path and can be
                # swept safely from the private staging directory later.
                pass
        if staged_files:
            try:
                staging_directory.rmdir()
                staging_directory.parent.rmdir()
            except OSError:
                pass
    except HTTPException:
        db.rollback()
        for original, staged in reversed(staged_files):
            if staged.exists():
                original.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged, original)
        raise
    except Exception as exc:
        db.rollback()
        for original, staged in reversed(staged_files):
            if staged.exists():
                original.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged, original)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WORK_ORDER_DELETE_FAILED",
                "message": "No fue posible eliminar la OT de forma segura; no se aplicaron cambios.",
            },
        ) from exc
