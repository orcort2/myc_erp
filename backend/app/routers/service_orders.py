from io import BytesIO

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.certificate import CertificateBatchActionRead, CertificateBulkUploadRead
from app.schemas.service_order import (
    ServiceOrderCreate,
    ServiceOrderExceptionAuthorize,
    ServiceOrderExceptionCreate,
    ServiceOrderExceptionRead,
    ServiceOrderRead,
    ServiceOrderStatusChange,
    ServiceOrderUpdate,
)
from app.schemas.service_execution import (
    ServiceExecutionBoardRead,
    ServiceStageCreate,
    ServiceStageRead,
    ServiceStageUpdate,
    ServiceUnitBatchCreate,
    ServiceUnitRead,
    TechnicalServiceRequestCreate,
    TechnicalServiceRequestRead,
)
from app.schemas.sale_execution import (
    SaleArrivalCreate,
    SaleAuthorizationCreate,
    SaleAuthorizationRead,
    SaleAuthorizationResolve,
    SaleBoardRead,
    SaleDeliveryAccept,
    SaleDeliveryConfirm,
    SaleDeliveryCreate,
    SaleWarrantyReturnCreate,
    SaleUnitResolution,
)
from app.services.auth import get_current_user, require_permission
from app.services.capture_packages import (
    list_capture_files,
    package_summary,
    service_order_package,
    upload_capture_files,
    work_order_package,
)
from app.services.certificates import (
    bulk_upload_certificate_pdfs,
    release_authenticated_certificates_for_service_order,
)
from app.services.service_orders import (
    authorize_service_order_exception,
    change_status,
    close_service_order,
    confirm_signature_cycle,
    create_service_order,
    deactivate_service_order,
    delete_service_work_order,
    execute_service_order_exception,
    get_service_order,
    list_service_orders,
    request_service_order_exception,
    update_service_order,
)
from app.services.service_execution import (
    add_service_stage,
    create_service_units,
    create_technical_request,
    execution_board,
    update_service_stage,
)
from app.services.sale_execution import (
    accept_technician_delivery,
    add_later_calibration,
    close_sale,
    confirm_delivery,
    create_delivery,
    delivery_note_pdf,
    dispatch_delivery,
    individualize_sale_item,
    initialize_existing_sale_execution,
    mark_warranty_return,
    register_arrival,
    report_courier_delivery,
    request_authorization,
    resolve_authorization,
    resolve_warranty_return,
    sale_board,
)
from app.services.work_order_pdfs import (
    generate_service_order_work_orders_pdf,
    generate_service_work_order_pdf,
    generate_work_order_pdf,
)


router = APIRouter(prefix="/service-orders", tags=["service-orders"])


@router.get("/{service_order_id}/sale", response_model=SaleBoardRead)
def get_sale_board(
    service_order_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("service_orders.read")),
):
    return sale_board(db, service_order_id)


@router.post("/{service_order_id}/sale/initialize", response_model=SaleBoardRead)
def post_sale_initialization(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.manage")),
):
    return initialize_existing_sale_execution(db, service_order_id, actor=current_user)


@router.post("/{service_order_id}/sale/items/{sale_item_id}/arrivals", response_model=SaleBoardRead)
def post_sale_arrival(
    service_order_id: int, sale_item_id: int, payload: SaleArrivalCreate,
    unit_state_id: int | None = Query(default=None), db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.manage")),
):
    return register_arrival(db, service_order_id, sale_item_id, payload,
                            actor=current_user, sale_unit_state_id=unit_state_id)


@router.post("/{service_order_id}/sale/units/{unit_state_id}/warranty", response_model=SaleBoardRead)
def post_sale_warranty(
    service_order_id: int, unit_state_id: int, payload: SaleWarrantyReturnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.manage")),
):
    return mark_warranty_return(db, service_order_id, unit_state_id, payload.reason, actor=current_user)


@router.post("/{service_order_id}/sale/units/{unit_state_id}/warranty/resolve", response_model=SaleBoardRead)
def post_sale_warranty_resolution(
    service_order_id: int, unit_state_id: int, payload: SaleUnitResolution,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.authorize")),
):
    return resolve_warranty_return(
        db, service_order_id, unit_state_id, payload.resolution, payload.reason, actor=current_user,
    )


@router.post("/{service_order_id}/sale/authorizations", response_model=SaleAuthorizationRead, status_code=201)
def post_sale_authorization(
    service_order_id: int, payload: SaleAuthorizationCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.manage")),
):
    return request_authorization(db, service_order_id, payload, actor=current_user)


@router.post("/{service_order_id}/sale/authorizations/{authorization_id}/resolve", response_model=SaleAuthorizationRead)
def post_sale_authorization_resolution(
    service_order_id: int, authorization_id: int, payload: SaleAuthorizationResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.authorize")),
):
    return resolve_authorization(db, service_order_id, authorization_id, payload, actor=current_user)


@router.post("/{service_order_id}/sale/items/{sale_item_id}/individualize", response_model=SaleBoardRead)
def post_sale_individualization(
    service_order_id: int, sale_item_id: int, authorization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.manage")),
):
    return individualize_sale_item(db, service_order_id, sale_item_id, authorization_id, actor=current_user)


@router.post("/{service_order_id}/sale/units/{unit_state_id}/calibration", response_model=SaleBoardRead)
def post_sale_calibration(
    service_order_id: int, unit_state_id: int, quotation_item_id: int | None = None,
    authorization_id: int | None = None, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.manage")),
):
    return add_later_calibration(db, service_order_id, unit_state_id, actor=current_user,
                                 quotation_item_id=quotation_item_id, authorization_id=authorization_id)


@router.post("/{service_order_id}/sale/deliveries", response_model=SaleBoardRead, status_code=201)
def post_sale_delivery(
    service_order_id: int, payload: SaleDeliveryCreate, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.manage")),
):
    return create_delivery(db, service_order_id, payload, actor=current_user)


@router.post("/{service_order_id}/sale/deliveries/{delivery_id}/dispatch", response_model=SaleBoardRead)
def post_sale_delivery_dispatch(
    service_order_id: int, delivery_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.manage")),
):
    return dispatch_delivery(db, service_order_id, delivery_id, actor=current_user)


@router.post("/{service_order_id}/sale/deliveries/{delivery_id}/accept", response_model=SaleBoardRead)
def post_sale_delivery_accept(
    service_order_id: int, delivery_id: int, payload: SaleDeliveryAccept,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.deliver")),
):
    return accept_technician_delivery(db, service_order_id, delivery_id, payload, actor=current_user)


@router.post("/{service_order_id}/sale/deliveries/{delivery_id}/courier-confirm", response_model=SaleBoardRead)
def post_sale_courier_confirmation(
    service_order_id: int, delivery_id: int, db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sales.manage")),
):
    return report_courier_delivery(db, service_order_id, delivery_id, actor=current_user)


@router.post("/{service_order_id}/sale/deliveries/{delivery_id}/receive", response_model=SaleBoardRead)
def post_sale_delivery_receipt(
    service_order_id: int, delivery_id: int, payload: SaleDeliveryConfirm,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return confirm_delivery(db, service_order_id, delivery_id, payload, actor=current_user)


@router.get("/{service_order_id}/sale/deliveries/{delivery_id}/note.pdf")
def get_sale_delivery_note(service_order_id: int, delivery_id: int, db: Session = Depends(get_db),
                           _current_user: User = Depends(require_permission("service_orders.read"))):
    content, filename = delivery_note_pdf(db, service_order_id, delivery_id)
    return StreamingResponse(BytesIO(content), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/{service_order_id}/sale/close", response_model=SaleBoardRead)
def post_sale_close(service_order_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(require_permission("service_orders.sales.manage"))):
    return close_sale(db, service_order_id, actor=current_user)


@router.get("/{service_order_id}/execution-board", response_model=ServiceExecutionBoardRead)
def get_service_execution_board(
    service_order_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_permission("service_orders.read")),
) -> ServiceExecutionBoardRead:
    return execution_board(db, service_order_id)


@router.post(
    "/{service_order_id}/service-units",
    response_model=list[ServiceUnitRead],
    status_code=status.HTTP_201_CREATED,
)
def post_service_units(
    service_order_id: int,
    payload: ServiceUnitBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.update")),
) -> list[ServiceUnitRead]:
    return create_service_units(db, service_order_id, payload, user_id=current_user.id)


@router.post(
    "/service-units/{service_unit_id}/stages",
    response_model=ServiceStageRead,
    status_code=status.HTTP_201_CREATED,
)
def post_service_stage(
    service_unit_id: int,
    payload: ServiceStageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.update")),
) -> ServiceStageRead:
    return add_service_stage(db, service_unit_id, payload, user_id=current_user.id)


@router.patch(
    "/stages/{service_stage_id}",
    response_model=ServiceStageRead,
)
def patch_service_stage(
    service_stage_id: int,
    payload: ServiceStageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.update")),
) -> ServiceStageRead:
    return update_service_stage(db, service_stage_id, payload, user_id=current_user.id)


@router.post(
    "/stages/{service_stage_id}/technical-requests",
    response_model=TechnicalServiceRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def post_technical_service_request(
    service_stage_id: int,
    payload: TechnicalServiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.update")),
) -> TechnicalServiceRequestRead:
    return create_technical_request(db, service_stage_id, payload, user_id=current_user.id)


@router.get("/{service_order_id}/capture-package-summary")
def get_capture_package_summary(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.read")),
) -> dict:
    return package_summary(db, service_order_id)


@router.get("/{service_order_id}/capture-package")
def download_capture_package(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.read")),
) -> StreamingResponse:
    payload, filename = service_order_package(db, service_order_id)
    filename = filename or f"ETS-{service_order_id}.zip"
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{service_order_id}/work-orders/{work_order_id}/capture-package")
def download_work_order_capture_package(
    service_order_id: int,
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.read")),
) -> StreamingResponse:
    payload, filename, media_type = work_order_package(
        db, service_order_id, work_order_id
    )
    filename = filename or f"ETS-{service_order_id}-OT-{work_order_id}.zip"
    return StreamingResponse(
        BytesIO(payload),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{service_order_id}/capture-files")
def post_capture_files(
    service_order_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.upload_pdf")),
) -> dict:
    return upload_capture_files(db, service_order_id, files, user_id=current_user.id)


@router.get("/{service_order_id}/capture-files")
def get_capture_files(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.read")),
) -> list[dict]:
    return [
        {
            "id": item.id,
            "certificate_id": item.certificate_id,
            "filename": item.original_filename,
            "status": item.identification_status,
            "validation": item.validation_results,
            "created_at": item.created_at,
        }
        for item in list_capture_files(db, service_order_id)
    ]


@router.post("/{service_order_id}/confirm-signatures", response_model=ServiceOrderRead)
def confirm_service_order_signatures(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("service_orders.sign")),
) -> ServiceOrderRead:
    return confirm_signature_cycle(db, service_order_id, user_id=current_user.id)


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
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return create_service_order(db, payload, user_id=current_user.id)


@router.get("/{service_order_id}", response_model=ServiceOrderRead)
def get_service_order_by_id(
    service_order_id: int, db: Session = Depends(get_db)
) -> ServiceOrderRead:
    return get_service_order(db, service_order_id)


@router.get("/{service_order_id}/work-order-pdf")
def get_service_order_work_order_pdf(
    service_order_id: int, db: Session = Depends(get_db)
) -> StreamingResponse:
    pdf_bytes, filename = generate_work_order_pdf(db, service_order_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{service_order_id}/work-orders-pdf")
def get_service_order_work_orders_pdf(
    service_order_id: int, db: Session = Depends(get_db)
) -> StreamingResponse:
    pdf_bytes, filename = generate_service_order_work_orders_pdf(db, service_order_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/work-orders/{work_order_id}/pdf")
def get_service_work_order_pdf(
    work_order_id: int, db: Session = Depends(get_db)
) -> StreamingResponse:
    pdf_bytes, filename = generate_service_work_order_pdf(db, work_order_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post(
    "/{service_order_id}/certificate-pdfs",
    response_model=CertificateBulkUploadRead,
)
def upload_service_order_certificate_pdfs(
    service_order_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("certificates.upload_pdf")),
) -> CertificateBulkUploadRead:
    return bulk_upload_certificate_pdfs(
        db, service_order_id, files, user_id=current_user.id
    )


@router.post(
    "/{service_order_id}/certificates/release-authenticated",
    response_model=CertificateBatchActionRead,
)
def release_service_order_certificates(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("release.manage")),
) -> CertificateBatchActionRead:
    return release_authenticated_certificates_for_service_order(
        db, service_order_id, user_id=current_user.id
    )


@router.patch("/{service_order_id}", response_model=ServiceOrderRead)
def patch_service_order(
    service_order_id: int,
    payload: ServiceOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return update_service_order(
        db, service_order_id, payload, user_id=current_user.id
    )


def _status_change(
    db: Session,
    service_order_id: int,
    new_status: str,
    payload: ServiceOrderStatusChange | None,
    current_user: User,
) -> ServiceOrderRead:
    return change_status(
        db, service_order_id, new_status, payload, user_id=current_user.id
    )


@router.post("/{service_order_id}/confirm", response_model=ServiceOrderRead)
def confirm_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return _status_change(db, service_order_id, "confirmed", payload, current_user)


@router.post("/{service_order_id}/call", response_model=ServiceOrderRead)
def call_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return _status_change(db, service_order_id, "called", payload, current_user)


@router.post("/{service_order_id}/start", response_model=ServiceOrderRead)
def start_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return _status_change(db, service_order_id, "in_progress", payload, current_user)


@router.post("/{service_order_id}/capture", response_model=ServiceOrderRead)
def capture_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return _status_change(db, service_order_id, "capture", payload, current_user)


@router.post("/{service_order_id}/quality", response_model=ServiceOrderRead)
def quality_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return _status_change(db, service_order_id, "quality_review", payload, current_user)


@router.post(
    "/{service_order_id}/exceptions",
    response_model=ServiceOrderExceptionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_service_order_exception(
    service_order_id: int,
    payload: ServiceOrderExceptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderExceptionRead:
    return request_service_order_exception(
        db, service_order_id, payload, user_id=current_user.id
    )


@router.post(
    "/{service_order_id}/exceptions/{exception_id}/authorize",
    response_model=ServiceOrderExceptionRead,
)
def authorize_service_order_exception_route(
    service_order_id: int,
    exception_id: int,
    payload: ServiceOrderExceptionAuthorize | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderExceptionRead:
    return authorize_service_order_exception(
        db,
        service_order_id,
        exception_id,
        user_id=current_user.id,
        comment=payload.comment if payload else None,
    )


@router.post(
    "/{service_order_id}/exceptions/{exception_id}/execute",
    response_model=ServiceOrderExceptionRead,
)
def execute_service_order_exception_route(
    service_order_id: int,
    exception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderExceptionRead:
    return execute_service_order_exception(
        db, service_order_id, exception_id, user_id=current_user.id
    )


@router.post("/{service_order_id}/pending-payment", response_model=ServiceOrderRead)
def pending_payment_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return _status_change(db, service_order_id, "pending_payment", payload, current_user)


@router.post("/{service_order_id}/release", response_model=ServiceOrderRead)
def release_service_order(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return _status_change(db, service_order_id, "released", payload, current_user)


@router.post("/{service_order_id}/close", response_model=ServiceOrderRead)
def close_service_order_route(
    service_order_id: int,
    payload: ServiceOrderStatusChange | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ServiceOrderRead:
    return close_service_order(
        db, service_order_id, payload, user_id=current_user.id
    )


@router.delete("/{service_order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_order(
    service_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    deactivate_service_order(db, service_order_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/work-orders/{work_order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("service_orders.delete")
    ),
) -> Response:
    delete_service_work_order(db, work_order_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
