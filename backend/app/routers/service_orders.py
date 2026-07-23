from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderExceptionCreate,
    ServiceOrderRead,
    ServiceOrderStatusChange,
    ServiceOrderUpdate,
)
from app.models.user import User
from app.services.auth import get_optional_current_user, require_permission
from app.schemas.certificate import CertificateBatchActionRead, CertificateBulkUploadRead
from app.services.certificates import (
    authenticate_certificates_for_service_order,
    bulk_upload_certificate_pdfs,
    release_authenticated_certificates_for_service_order,
)
from app.services.service_orders import (
    change_status,
    close_service_order,
    create_service_order as create_service_order_service,
    deactivate_service_order,
    get_service_order,
    list_service_orders,
    register_service_order_exception,
    update_service_order,
)
from app.services.work_order_pdfs import (
    generate_service_work_order_pdf,
    generate_service_order_work_orders_pdf,
    generate_work_order_pdf,
)
from app.services.capture_packages import (
    package_summary,
    list_capture_files,
    service_order_package,
    upload_capture_files,
    work_order_package,
)

from io import BytesIO


router = APIRouter(prefix="/service-orders", tags=["service-orders"])


@router.get("/{service_order_id}/capture-package-summary")
def get_capture_package_summary(
    service_order_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.read")),
) -> dict:
    return package_summary(db, service_order_id)


@router.get("/{service_order_id}/capture-package")
def download_capture_package(
    service_order_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.read")),
) -> StreamingResponse:
    payload, filename = service_order_package(db, service_order_id)
    filename = filename or f"ETS-{service_order_id}.zip"
    return StreamingResponse(BytesIO(payload), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{service_order_id}/work-orders/{work_order_id}/capture-package")
def download_work_order_capture_package(
    service_order_id: int, work_order_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.read")),
) -> StreamingResponse:
    payload, filename, media_type = work_order_package(db, service_order_id, work_order_id)
    filename = filename or f"ETS-{service_order_id}-OT-{work_order_id}.zip"
    return StreamingResponse(BytesIO(payload), media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/{service_order_id}/capture-files")
def post_capture_files(
    service_order_id: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.upload_pdf")),
) -> dict:
    return upload_capture_files(db, service_order_id, files, user_id=current_user.id)


@router.get("/{service_order_id}/capture-files")
def get_capture_files(
    service_order_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.read")),
) -> list[dict]:
    return [{"id": item.id, "certificate_id": item.certificate_id, "filename": item.original_filename,
             "status": item.identification_status, "validation": item.validation_results,
             "created_at": item.created_at} for item in list_capture_files(db, service_order_id)]

from datetime import date, datetime, timezone
from math import ceil

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.folios import FolioRequest, generate_folio
from app.models.client import Client
from app.models.quotation import Quotation
from app.models.service_order import (
    ServiceOrder,
    ServiceOrderItem,
    ServiceWorkOrder,
    ServiceOrderSignatureCycle,
    ServiceOrderSignatureCycleWorkOrder,
)
from app.models.user import User
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderExceptionCreate,
    ServiceOrderStatusChange,
    ServiceOrderUpdate,
)
from app.services.audit_logs import write_audit_log



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

@router.post(
    "/{service_order_id}/confirm-signatures",
    response_model=ServiceOrderRead,
)
def confirm_service_order_signatures(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ServiceOrderRead:
    from app.services.service_orders import confirm_signature_cycle

    return confirm_signature_cycle(
        db,
        service_order_id,
        user_id=current_user.id if current_user else None,
    )

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


def _get_active_quotation(db: Session, quotation_id: int | None) -> Quotation | None:
    if quotation_id is None:
        return None
    quotation = db.scalar(
        select(Quotation)
        .where(Quotation.id == quotation_id, Quotation.is_active.is_(True))
        .options(selectinload(Quotation.items))
    )
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
    legacy_last = db.scalar(select(func.max(ServiceOrder.work_order_number)))
    work_order_last = db.scalar(select(func.max(ServiceWorkOrder.work_order_number)))
    last_number = max(int(legacy_last or 7000), int(work_order_last or 7000))
    return max(last_number + 1, 7001)


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


def list_service_orders(
    db: Session, *, include_inactive: bool = False
) -> list[ServiceOrder]:
    query = (
        select(ServiceOrder)
        .options(
            selectinload(ServiceOrder.items),
            selectinload(ServiceOrder.work_orders),
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
    return list(db.scalars(query).all())


def get_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    service_order = db.scalar(
        select(ServiceOrder)
        .where(ServiceOrder.id == service_order_id)
        .options(
            selectinload(ServiceOrder.items),
            selectinload(ServiceOrder.work_orders),
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
    db: Session, payload: ServiceOrderCreate, *, user_id: int | None = None
) -> ServiceOrder:
    _ensure_active_client(db, payload.client_id)
    _ensure_active_user(db, payload.advisor_id, "Asesor")
    _ensure_active_user(db, payload.technician_id, "Tecnico")

    quotation = _get_active_quotation(db, payload.quotation_id)
    if quotation is not None and quotation.client_id != payload.client_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La cotizacion no pertenece al cliente indicado",
        )

    primary_work_order_number = _next_work_order_number(db)

    service_order = ServiceOrder(
        folio=_next_service_order_folio(db, date.today()),
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
        status="scheduled",
    )

    if payload.items:
        service_order.items = [
            ServiceOrderItem(**item.model_dump()) for item in payload.items
        ]
    elif quotation is not None:
        service_order.items = [
            ServiceOrderItem(
                quotation_item_id=item.id,
                service_name=item.service_name,
                calibration_scope=item.calibration_scope,
                quantity=item.quantity,
                status="pending",
            )
            for item in quotation.items
            if item.is_active
        ]

    db.add(service_order)
    db.flush()

    _build_work_orders_for_service_order(db, service_order)
    db.flush()

    write_audit_log(
        db,
        action="service_order.created",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        new_values={
            "folio": service_order.folio,
            "work_order_number": service_order.work_order_number,
            "work_orders": [
                {
                    "id": work_order.id,
                    "work_order_number": work_order.work_order_number,
                    "sequence": work_order.sequence,
                    "equipment_limit": work_order.equipment_limit,
                }
                for work_order in service_order.work_orders
            ],
            "client_id": service_order.client_id,
            "quotation_id": service_order.quotation_id,
            "status": service_order.status,
        },
    )
    db.commit()
    return get_service_order(db, service_order.id)


def update_service_order(
    db: Session,
    service_order_id: int,
    payload: ServiceOrderUpdate,
    *,
    user_id: int | None = None,
) -> ServiceOrder:
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


def change_status(
    db: Session,
    service_order_id: int,
    new_status: str,
    payload: ServiceOrderStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> ServiceOrder:
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
    db.commit()
    return get_service_order(db, service_order.id)


def close_service_order(
    db: Session,
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    *,
    user_id: int | None = None,
) -> ServiceOrder:
    return change_status(db, service_order_id, "closed", payload, user_id=user_id)


def register_service_order_exception(
    db: Session,
    service_order_id: int,
    payload: ServiceOrderExceptionCreate,
    *,
    user_id: int | None = None,
) -> ServiceOrder:
    service_order = get_service_order(db, service_order_id)
    source_stage = payload.source_stage.strip()
    target_stage = payload.target_stage.strip()
    target_status = STAGE_STATUS_MAP.get(target_stage.lower())
    previous_status = service_order.status

    if target_status and previous_status not in TERMINAL_STATUSES:
        service_order.status = target_status

    write_audit_log(
        db,
        action="service_order.exception_requested",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values={
            "status": previous_status,
            "source_stage": source_stage,
        },
        new_values={
            "status": service_order.status,
            "target_stage": target_stage,
            "target_status": target_status,
        },
        comment=payload.reason,
    )
    db.commit()
    return get_service_order(db, service_order.id)


def deactivate_service_order(
    db: Session, service_order_id: int, *, user_id: int | None = None
) -> ServiceOrder:
    service_order = get_service_order(db, service_order_id)
    service_order.is_active = False
    service_order.deleted_at = datetime.now(timezone.utc)
    service_order.deleted_by = user_id

    for work_order in service_order.work_orders:
        work_order.is_active = False
        work_order.status = "cancelled"
        work_order.deleted_at = service_order.deleted_at
        work_order.deleted_by = user_id

    write_audit_log(
        db,
        action="service_order.deactivated",
        entity="service_orders",
        entity_id=service_order.id,
        user_id=user_id,
        previous_values={"is_active": True},
        new_values={"is_active": False},
    )
    db.commit()
    return service_order



@router.get("", response_model=list[ServiceOrderRead])
def get_service_orders(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ServiceOrderRead]:
    return list_service_orders(db, include_inactive=include_inactive)


@router.post("", response_model=ServiceOrderRead, status_code=status.HTTP_201_CREATED)
def post_service_order(
    payload: ServiceOrderCreate,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return create_service_order_service(db, payload)


@router.get("/{service_order_id}", response_model=ServiceOrderRead)
def get_service_order_by_id(
    service_order_id: int, db: Session = Depends(get_db)
) -> ServiceOrderRead:
    return get_service_order(db, service_order_id)


@router.get("/{service_order_id}/work-order-pdf")
def get_service_order_work_order_pdf(
    service_order_id: int,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    pdf_bytes, filename = generate_work_order_pdf(db, service_order_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{service_order_id}/work-orders-pdf")
def get_service_order_work_orders_pdf(
    service_order_id: int,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    pdf_bytes, filename = generate_service_order_work_orders_pdf(db, service_order_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/work-orders/{work_order_id}/pdf")
def get_service_work_order_pdf(
    work_order_id: int,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    pdf_bytes, filename = generate_service_work_order_pdf(db, work_order_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{service_order_id}/certificate-pdfs", response_model=CertificateBulkUploadRead)
def upload_service_order_certificate_pdfs(
    service_order_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.upload_pdf")),
) -> CertificateBulkUploadRead:
    return bulk_upload_certificate_pdfs(db, service_order_id, files, user_id=current_user.id)


@router.post("/{service_order_id}/certificates/authenticate-approved", response_model=CertificateBatchActionRead)
def authenticate_service_order_certificates(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.approve")),
) -> CertificateBatchActionRead:
    return authenticate_certificates_for_service_order(db, service_order_id, user_id=current_user.id)


@router.post("/{service_order_id}/certificates/release-authenticated", response_model=CertificateBatchActionRead)
def release_service_order_certificates(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("release.manage")),
) -> CertificateBatchActionRead:
    return release_authenticated_certificates_for_service_order(db, service_order_id, user_id=current_user.id)


@router.patch("/{service_order_id}", response_model=ServiceOrderRead)
def patch_service_order(
    service_order_id: int,
    payload: ServiceOrderUpdate,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return update_service_order(db, service_order_id, payload)

@router.post(
    "/{service_order_id}/confirm-signatures",
    response_model=ServiceOrderRead,
)
def confirm_service_order_signatures(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ServiceOrderRead:
    from app.services.service_orders import confirm_signature_cycle

    return confirm_signature_cycle(
        db,
        service_order_id,
        user_id=current_user.id if current_user else None,
    )

@router.post("/{service_order_id}/confirm", response_model=ServiceOrderRead)
def confirm_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "confirmed", payload)


@router.post("/{service_order_id}/call", response_model=ServiceOrderRead)
def call_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "called", payload)


@router.post("/{service_order_id}/start", response_model=ServiceOrderRead)
def start_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "in_progress", payload)


@router.post("/{service_order_id}/capture", response_model=ServiceOrderRead)
def capture_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "capture", payload)


@router.post("/{service_order_id}/quality", response_model=ServiceOrderRead)
def quality_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "quality_review", payload)


@router.post("/{service_order_id}/exceptions", response_model=ServiceOrderRead)
def create_service_order_exception(
    service_order_id: int,
    payload: ServiceOrderExceptionCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> ServiceOrderRead:
    return register_service_order_exception(
        db,
        service_order_id,
        payload,
        user_id=current_user.id if current_user else None,
    )


@router.post("/{service_order_id}/pending-payment", response_model=ServiceOrderRead)
def pending_payment_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "pending_payment", payload)


@router.post("/{service_order_id}/release", response_model=ServiceOrderRead)
def release_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return change_status(db, service_order_id, "released", payload)


@router.post("/{service_order_id}/close", response_model=ServiceOrderRead)
def close_service_order_route(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
) -> ServiceOrderRead:
    return close_service_order(db, service_order_id, payload)


@router.delete("/{service_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_order(
    service_order_id: int, db: Session = Depends(get_db)
) -> Response:
    deactivate_service_order(db, service_order_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
