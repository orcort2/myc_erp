"""MYC Mobile ↔ ERP calibration ETS: candidates and atomic create + link.

Only internal MYC staff use this path during LAB creation. The ERP link is
optional: without ``service_order_id`` the legacy LAB creation is untouched.
With it, validation, LAB folio allocation, the ServiceOrderLabLink to the root
and every audit event happen in ONE transaction; any failure rolls back all of
it (no orphan OT, partial group, partial link or consumed LAB folio).

``ServiceOrderLabLink`` remains the only ERP ↔ LAB relation: a single OT is its
own root, a group links only its root and additional OT inherit it through
``root_work_order_id``. Replace/unlink stay administrative in the ERP bridge.
"""

from fastapi import HTTPException
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.client import Client
from app.models.lab_work_order import LabWorkOrder
from app.models.quotation import Quotation
from app.models.service_order import ServiceOrder, ServiceOrderItem, ServiceWorkOrder
from app.models.service_order_lab_link import ServiceOrderLabLink
from app.models.user import User
from app.schemas.lab_work_order import (
    LabErpCalibrationCandidateRead,
    LabErpCalibrationItemSummary,
    LabWorkOrderCreate,
    LabWorkOrderGroupCreate,
    LabWorkOrderRead,
)
from app.services.lab_work_orders import (
    _create_work_order_row,
    _get,
    _materialize_group,
    _read,
)
from app.services.push_notifications import commit_and_dispatch_notifications
from app.services.service_order_lab_links import (
    link_integrity_conflict,
    link_lab_root_in_transaction,
)
from app.services.service_order_technical_flow import (
    CALIBRATION_CATEGORY,
    is_mobile_calibration_service_order,
)
from app.services.service_orders import TERMINAL_STATUSES


CANDIDATE_LIMIT_MAX = 25
LINK_ORIGIN = "mobile_lab_creation"


def _client_name(client: Client | None) -> str:
    if client is None:
        return "Cliente no disponible"
    return client.commercial_name or client.legal_name or "Cliente sin nombre"


def _eligible_query():
    """Candidates resolved entirely in SQL, mirroring the technical-flow policy.

    Calibration-only = at least one active item and no active item whose
    operational_category is not ``calibration`` (NULL counts as not calibration).
    Filtering in SQL keeps the LIMIT exact: mixed ETS never hide valid ones.
    """
    active_items = select(ServiceOrderItem.id).where(
        ServiceOrderItem.service_order_id == ServiceOrder.id,
        ServiceOrderItem.is_active.is_(True),
    )
    return (
        select(ServiceOrder)
        .join(Quotation, Quotation.id == ServiceOrder.quotation_id)
        .where(
            ServiceOrder.is_active.is_(True),
            ServiceOrder.status.not_in(TERMINAL_STATUSES),
            ServiceOrder.work_order_number.is_(None),
            Quotation.is_active.is_(True),
            Quotation.status == "accepted",
            exists(active_items),
            ~exists(active_items.where(or_(
                ServiceOrderItem.operational_category.is_(None),
                ServiceOrderItem.operational_category != CALIBRATION_CATEGORY,
            ))),
            ~exists(select(ServiceWorkOrder.id).where(
                ServiceWorkOrder.service_order_id == ServiceOrder.id,
            )),
        )
        .options(
            selectinload(ServiceOrder.items),
            selectinload(ServiceOrder.work_orders),
            selectinload(ServiceOrder.quotation),
            selectinload(ServiceOrder.client),
        )
    )


def search_erp_calibration_candidates(
    db: Session, q: str, *, limit: int = 20
) -> list[LabErpCalibrationCandidateRead]:
    """Server-side search by quotation folio, ETS folio or client name."""
    term = q.strip()
    if len(term) < 2:
        return []
    limit = max(1, min(limit, CANDIDATE_LIMIT_MAX))
    needle = term.lower()

    def matches(column):
        # Literal partial match: % and _ typed by the user are not wildcards.
        return func.lower(column).contains(needle, autoescape=True)
    query = (
        _eligible_query()
        .outerjoin(Client, Client.id == ServiceOrder.client_id)
        .where(
            or_(
                matches(Quotation.folio),
                matches(ServiceOrder.folio),
                matches(Client.legal_name),
                matches(Client.commercial_name),
            )
        )
        .order_by(ServiceOrder.created_at.desc(), ServiceOrder.id.desc())
        .limit(limit)
    )
    # The SQL filter is authoritative; the policy check is a consistency guard.
    orders = [
        order for order in db.scalars(query).unique()
        if is_mobile_calibration_service_order(order)
    ]
    if not orders:
        return []
    active_links = {
        service_order_id: (root_id, root_folio)
        for service_order_id, root_id, root_folio in db.execute(
            select(
                ServiceOrderLabLink.service_order_id,
                ServiceOrderLabLink.lab_root_work_order_id,
                LabWorkOrder.folio,
            )
            .join(LabWorkOrder, LabWorkOrder.id == ServiceOrderLabLink.lab_root_work_order_id)
            .where(
                ServiceOrderLabLink.service_order_id.in_([order.id for order in orders]),
                ServiceOrderLabLink.status == "active",
            )
        ).all()
    }
    results = []
    for order in orders:
        calibration_items = [
            item for item in order.items
            if item.is_active and item.operational_category == CALIBRATION_CATEGORY
        ]
        root = active_links.get(order.id)
        results.append(
            LabErpCalibrationCandidateRead(
                service_order_id=order.id,
                service_order_folio=order.folio,
                quotation_id=order.quotation_id,
                quotation_folio=order.quotation.folio,
                client_id=order.client_id,
                client_name=_client_name(order.client),
                calibration_item_count=len(calibration_items),
                calibration_quantity=sum(int(item.quantity or 0) for item in calibration_items),
                calibration_items=[
                    LabErpCalibrationItemSummary(
                        service_name=item.service_name, quantity=int(item.quantity or 0)
                    )
                    for item in calibration_items
                ],
                active_lab_root_id=root[0] if root else None,
                active_lab_root_folio=root[1] if root else None,
                available=root is None,
            )
        )
    return results


def _lock_candidate(db: Session, service_order_id: int) -> ServiceOrder:
    """Lock the ETS first (before any LAB folio allocation) and revalidate it."""
    order = db.scalar(
        select(ServiceOrder)
        .where(ServiceOrder.id == service_order_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None or not order.is_active:
        raise HTTPException(404, "ETS no encontrado")
    quotation = db.get(Quotation, order.quotation_id) if order.quotation_id else None
    eligible = (
        order.status not in TERMINAL_STATUSES
        and quotation is not None
        and quotation.is_active
        and quotation.status == "accepted"
        and is_mobile_calibration_service_order(order)
    )
    if not eligible:
        raise HTTPException(
            409,
            {
                "code": "SERVICE_ORDER_NOT_MOBILE_CALIBRATION_CANDIDATE",
                "message": (
                    "El ETS no es un ETS de calibración MYC Mobile con cotización "
                    "aceptada, activo y abierto."
                ),
                "service_order_id": service_order_id,
            },
        )
    active = db.scalar(
        select(ServiceOrderLabLink.lab_root_work_order_id).where(
            ServiceOrderLabLink.service_order_id == order.id,
            ServiceOrderLabLink.status == "active",
        )
    )
    if active is not None:
        raise HTTPException(
            409,
            {
                "code": "SERVICE_ORDER_ALREADY_LINKED_TO_LAB",
                "message": "El ETS ya está vinculado a otra OT MYC Mobile.",
                "service_order_id": order.id,
                "active_lab_root_id": active,
            },
        )
    return order


def _create_and_link(db: Session, service_order_id: int, user: User, create_root) -> LabWorkOrderRead:
    try:
        _lock_candidate(db, service_order_id)
        root = create_root()
        link_lab_root_in_transaction(
            db, service_order_id, root, user_id=user.id, origin=LINK_ORIGIN
        )
        commit_and_dispatch_notifications(db)
    except IntegrityError as exc:
        db.rollback()
        conflict = link_integrity_conflict(exc)
        if conflict is not None:
            raise conflict from exc
        raise
    except Exception:
        db.rollback()
        raise
    return _read(db, _get(db, root.id))


def create_linked_work_order(
    db: Session, payload: LabWorkOrderCreate, service_order_id: int, user: User
) -> LabWorkOrderRead:
    """Single OT: the new order is its own root and gets the only link."""
    return _create_and_link(
        db,
        service_order_id,
        user,
        lambda: _create_work_order_row(db, payload, user, operator_client_id=None),
    )


def create_linked_work_order_group(
    db: Session, payload: LabWorkOrderGroupCreate, service_order_id: int, user: User
) -> LabWorkOrderRead:
    """Direct staff group: N orders, one link to the root only."""
    return _create_and_link(
        db,
        service_order_id,
        user,
        lambda: _materialize_group(
            db, payload, user, operator_client_id=None, origin="staff_direct"
        ),
    )
