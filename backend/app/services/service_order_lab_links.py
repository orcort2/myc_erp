"""ERP link lifecycle only. Never mutates LAB orders or their technical data."""

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.lab_work_order import LabWorkOrder, LabWorkOrderEquipment
from app.models.service_order import ServiceOrder
from app.models.service_order_lab_link import ServiceOrderLabLink
from app.schemas.service_order_lab_link import ServiceOrderLabCandidateRead
from app.services.audit_logs import write_audit_log
from app.services.service_orders import TERMINAL_STATUSES


def link_integrity_conflict(exc: IntegrityError) -> HTTPException | None:
    """Translate only active-link uniqueness races; never mask other DB failures."""
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    sqlite_message = str(exc.orig)
    if constraint in {
        "uq_service_order_lab_link_active_ets",
        "uq_service_order_lab_link_active_root",
    } or any(
        f"UNIQUE constraint failed: service_order_lab_links.{column}" in sqlite_message
        for column in ("service_order_id", "lab_root_work_order_id")
    ):
        return HTTPException(409, "El ETS o grupo LAB ya tiene un vínculo activo")
    return None


@contextmanager
def _mutation(db: Session, user_id: int):
    """Own one request transaction, including audit; never leave partial replacement."""
    if user_id is None:
        raise ValueError("Los vínculos LAB requieren un actor")
    try:
        yield
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        conflict = link_integrity_conflict(exc)
        if conflict is not None:
            raise conflict from exc
        raise
    except Exception:
        db.rollback()
        raise


def _service_order(db: Session, service_order_id: int, *, lock: bool = False):
    query = select(ServiceOrder).where(ServiceOrder.id == service_order_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    order = db.scalar(query)
    if order is None:
        raise HTTPException(404, "Orden de servicio no encontrada")
    # History stays readable after deactivation/closure; mutations do not.
    if lock and (not order.is_active or order.status in TERMINAL_STATUSES):
        raise HTTPException(409, "No se puede gestionar el vínculo de un ETS inactivo, cerrado o cancelado")
    return order


def _links():
    return select(ServiceOrderLabLink).options(
        selectinload(ServiceOrderLabLink.lab_root_work_order),
        selectinload(ServiceOrderLabLink.linked_by),
        selectinload(ServiceOrderLabLink.unlinked_by),
    ).execution_options(populate_existing=True)


def _active(db: Session, service_order_id: int) -> ServiceOrderLabLink | None:
    return db.scalar(_links().where(
        ServiceOrderLabLink.service_order_id == service_order_id,
        ServiceOrderLabLink.status == "active",
    ))


def get_active_lab_link(db: Session, service_order_id: int) -> ServiceOrderLabLink | None:
    _service_order(db, service_order_id)
    return _active(db, service_order_id)


def list_lab_link_history(db: Session, service_order_id: int) -> list[ServiceOrderLabLink]:
    _service_order(db, service_order_id)
    return list(db.scalars(_links().where(
        ServiceOrderLabLink.service_order_id == service_order_id,
    ).order_by(ServiceOrderLabLink.linked_at.desc(), ServiceOrderLabLink.id.desc())))


def resolve_lab_root_work_order(
    db: Session, work_order_id: int, *, lock: bool = False,
) -> LabWorkOrder:
    order = db.get(LabWorkOrder, work_order_id, populate_existing=True)
    if order is None:
        raise HTTPException(404, "Orden de trabajo LAB no encontrada")
    root_id = order.root_work_order_id or order.id
    query = select(LabWorkOrder).where(LabWorkOrder.id == root_id)
    if lock:
        query = query.with_for_update()
    root = db.scalar(query.execution_options(populate_existing=True))
    # LAB historically uses both NULL roots and self-referencing roots.
    if root is None or root.root_work_order_id not in (None, root.id):
        raise HTTPException(409, "La OT LAB no pertenece a una raíz válida")
    if root.status == "cancelled":
        raise HTTPException(409, "No se puede vincular un grupo LAB cancelado")
    return root


def _ensure_available(db: Session, root_id: int, service_order_id: int) -> None:
    other = db.scalar(select(ServiceOrderLabLink.id).where(
        ServiceOrderLabLink.lab_root_work_order_id == root_id,
        ServiceOrderLabLink.status == "active",
        ServiceOrderLabLink.service_order_id != service_order_id,
    ))
    if other is not None:
        raise HTTPException(409, "El grupo LAB está vinculado a otro ETS")


def _reason(reason: str) -> str:
    if not reason or not reason.strip():
        raise HTTPException(422, "El motivo es obligatorio")
    return reason.strip()


def _new_link(db: Session, service_order_id: int, root_id: int, user_id: int):
    link = ServiceOrderLabLink(
        service_order_id=service_order_id, lab_root_work_order_id=root_id,
        status="active", linked_at=datetime.now(timezone.utc), linked_by_user_id=user_id,
    )
    db.add(link)
    db.flush()
    return link


def _snapshot(link: ServiceOrderLabLink, root_folio: int) -> dict:
    return {
        "service_order_id": link.service_order_id,
        "link_id": link.id,
        "lab_root_work_order_id": link.lab_root_work_order_id,
        "root_folio": root_folio,
        "status": link.status,
        "linked_by_user_id": link.linked_by_user_id,
    }


def _close(link: ServiceOrderLabLink, status: str, reason: str, user_id: int):
    link.status = status
    link.unlinked_at = datetime.now(timezone.utc)
    link.unlinked_by_user_id = user_id
    link.unlink_reason = reason


def link_lab_root_in_transaction(
    db: Session, service_order_id: int, root: LabWorkOrder, *, user_id: int,
    origin: str | None = None,
) -> ServiceOrderLabLink:
    """Link core shared by the ERP bridge and MYC Mobile creation. NEVER commits.

    Locks the ETS, validates availability, creates the active link and writes
    the audit event inside the caller's transaction. ``root`` must already be a
    resolved (and, for concurrent callers, locked) LAB root.
    """
    if user_id is None:
        raise ValueError("Los vínculos LAB requieren un actor")
    _service_order(db, service_order_id, lock=True)
    link = _active(db, service_order_id)
    if link is not None:
        if link.lab_root_work_order_id != root.id:
            raise HTTPException(409, "El ETS ya tiene un vínculo activo; use replace")
        return link
    _ensure_available(db, root.id, service_order_id)
    link = _new_link(db, service_order_id, root.id, user_id)
    new_values = _snapshot(link, root.folio)
    if origin is not None:
        new_values["origin"] = origin
    write_audit_log(
        db, action="service_order.lab_group_linked", entity="service_orders",
        entity_id=service_order_id, user_id=user_id, new_values=new_values,
    )
    return link


def link_lab_group(
    db: Session, service_order_id: int, work_order_id: int, *, user_id: int,
) -> ServiceOrderLabLink:
    with _mutation(db, user_id):
        # Stable lock order: ETS, then target LAB root. Partial indexes remain
        # the final guard for callers without locks (including SQLite tests).
        _service_order(db, service_order_id, lock=True)
        root = resolve_lab_root_work_order(db, work_order_id, lock=True)
        link = link_lab_root_in_transaction(db, service_order_id, root, user_id=user_id)
    return link


def replace_lab_group(
    db: Session, service_order_id: int, work_order_id: int, reason: str, *, user_id: int,
) -> ServiceOrderLabLink:
    with _mutation(db, user_id):
        reason = _reason(reason)
        _service_order(db, service_order_id, lock=True)
        old = _active(db, service_order_id)
        if old is None:
            raise HTTPException(409, "El ETS no tiene un vínculo activo")
        root = resolve_lab_root_work_order(db, work_order_id, lock=True)
        link = old
        if old.lab_root_work_order_id != root.id:
            _ensure_available(db, root.id, service_order_id)
            previous = _snapshot(old, old.root_folio)
            _close(old, "replaced", reason, user_id)
            db.flush()  # Release the partial unique ETS key within this transaction.
            link = _new_link(db, service_order_id, root.id, user_id)
            old.replaced_by_link_id = link.id
            write_audit_log(
                db, action="service_order.lab_group_replaced", entity="service_orders",
                entity_id=service_order_id, user_id=user_id, previous_values=previous,
                new_values={**_snapshot(link, root.folio), "reason": reason,
                            "previous_link_status": "replaced", "replaced_by_link_id": link.id},
                comment=reason,
            )
    return link


def unlink_lab_group(
    db: Session, service_order_id: int, reason: str, *, user_id: int,
) -> ServiceOrderLabLink:
    with _mutation(db, user_id):
        reason = _reason(reason)
        _service_order(db, service_order_id, lock=True)
        link = _active(db, service_order_id)
        if link is None:
            raise HTTPException(409, "El ETS no tiene un vínculo activo")
        previous = _snapshot(link, link.root_folio)
        _close(link, "unlinked", reason, user_id)
        write_audit_log(
            db, action="service_order.lab_group_unlinked", entity="service_orders",
            entity_id=service_order_id, user_id=user_id, previous_values=previous,
            new_values={**_snapshot(link, link.root_folio), "reason": reason}, comment=reason,
        )
    return link


def search_lab_candidates(
    db: Session, service_order_id: int, q: str = "", *, limit: int = 50,
) -> list[ServiceOrderLabCandidateRead]:
    _service_order(db, service_order_id)
    # Searching a child returns its historical group once. Do not load technical
    # relationships (FieldSheets, signatures, PDFs) for a candidate summary.
    matches = select(func.coalesce(LabWorkOrder.root_work_order_id, LabWorkOrder.id)).where(
        cast(LabWorkOrder.folio, String).contains(q.strip(), autoescape=True),
    )
    roots = list(db.scalars(select(LabWorkOrder).where(
        LabWorkOrder.id.in_(matches),
        or_(LabWorkOrder.root_work_order_id.is_(None),
            LabWorkOrder.root_work_order_id == LabWorkOrder.id),
    ).order_by(LabWorkOrder.folio, LabWorkOrder.id).limit(limit)))
    if not roots:
        return []
    root_ids = [root.id for root in roots]
    group_id = func.coalesce(LabWorkOrder.root_work_order_id, LabWorkOrder.id)
    members = db.execute(select(group_id, LabWorkOrder.folio).where(
        group_id.in_(root_ids),
    ).order_by(LabWorkOrder.sequence_number, LabWorkOrder.id)).all()
    folios = {root_id: [] for root_id in root_ids}
    for root_id, folio in members:
        folios[root_id].append(folio)
    counts = dict(db.execute(select(group_id, func.count(LabWorkOrderEquipment.id)).join(
        LabWorkOrderEquipment, LabWorkOrderEquipment.work_order_id == LabWorkOrder.id,
    ).where(group_id.in_(root_ids), LabWorkOrderEquipment.is_active.is_(True)).group_by(group_id)).all())
    active = dict(db.execute(select(
        ServiceOrderLabLink.lab_root_work_order_id, ServiceOrderLabLink.service_order_id,
    ).where(ServiceOrderLabLink.lab_root_work_order_id.in_(root_ids),
            ServiceOrderLabLink.status == "active")).all())
    return [ServiceOrderLabCandidateRead(
        root_id=root.id, root_folio=root.folio, group_folios=folios[root.id],
        client_name=root.client_name, status=root.status,
        work_order_count=len(folios[root.id]), equipment_count=counts.get(root.id, 0),
        active_service_order_id=active.get(root.id),
        linked_to_other_service_order=root.id in active and active[root.id] != service_order_id,
    ) for root in roots]
