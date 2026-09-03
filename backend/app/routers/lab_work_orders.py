from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.auth import require_permission
from app.core.mobile.scope import ensure_lab_work_order_scope
from app.core.mobile.security import MobileSecurityContext, require_mobile_permission
from app.schemas.lab_work_order import (
    LabEquipmentCertificateClientWrite,
    LabEquipmentConfiguredCreate,
    LabEquipmentWrite,
    LabEquipmentServiceWrite,
    LabCancellationWrite,
    LabDirectReopenWrite,
    LabFieldSheetCreate,
    LabSignatureGroupWrite,
    LabWorkOrderCreate,
    LabWorkOrderGroupCreate,
    LabWorkOrderGroupDecision,
    LabWorkOrderGroupRequestRead,
    LabWorkOrderListItem,
    LabWorkOrderRead,
    LabReceptionDateUpdate,
    LabWorkOrderUpdate,
)
from app.schemas.field_sheet import FieldSheetRead, FieldSheetUpdate
from app.schemas.field_sheet_template import FieldSheetTemplateRead
from app.schemas.operational_ticket import LabRevisionRead
from app.services.lab_work_orders import (
    add_equipment,
    assign_equipment_service,
    cancel_work_order,
    restore_work_order,
    complete_group,
    complete_individual,
    create_additional_work_order,
    create_configured_equipment,
    create_work_order,
    create_work_order_group,
    create_group_request,
    list_group_requests,
    claim_group_request,
    approve_group_request,
    reject_group_request,
    delete_work_order,
    delete_equipment,
    export_all,
    get_pdf,
    get_work_order,
    list_work_orders,
    set_equipment_certificate_client,
    sign_group,
    sign_individual,
    update_configured_equipment,
    update_equipment,
    update_work_order,
    update_reception_date,
)
from app.services.field_sheet_pdfs import generate_field_sheet_pdf
from app.services.field_sheet_templates import list_field_sheet_templates
from app.services.lab_field_sheets import (
    complete_lab_field_sheet,
    create_lab_field_sheet,
    discard_lab_field_sheet,
    read_lab_field_sheet,
    update_lab_field_sheet,
)
from app.services.lab_packages import generate_lab_package
from app.models.linked_company import LinkedCompany
from sqlalchemy import select
from app.services.operational_tickets import get_revision_pdf, list_revisions, reopen_work_order_directly


router = APIRouter(
    prefix="/mobile/v1/technician/lab-work-orders",
    tags=["mobile-lab-work-orders"],
)
staff_router = APIRouter(prefix="/lab-work-order-groups", tags=["lab-work-order-groups"])


@router.post("/group-requests", response_model=LabWorkOrderGroupRequestRead, status_code=201)
def request_lab_work_order_group(
    payload: LabWorkOrderGroupCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.group.request")
    ),
) -> LabWorkOrderGroupRequestRead:
    if context.actor_type != "client" or context.client_id is None:
        raise HTTPException(
            status_code=403,
            detail="La solicitud anticipada está disponible únicamente para actores externos",
        )
    return create_group_request(
        db, payload, context.user, operator_client_id=context.client_id
    )


@router.get("/group-requests", response_model=list[LabWorkOrderGroupRequestRead])
def get_mobile_group_requests(
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.group.request")
    ),
) -> list[LabWorkOrderGroupRequestRead]:
    if context.actor_type != "client" or context.client_id is None:
        raise HTTPException(
            status_code=403,
            detail="La consulta externa requiere una organización vinculada",
        )
    return list_group_requests(db, operator_client_id=context.client_id)


@router.post("/groups", response_model=LabWorkOrderRead, status_code=201)
def create_mobile_staff_group(
    payload: LabWorkOrderGroupCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_work_order_groups.create")
    ),
) -> LabWorkOrderRead:
    if context.actor_type != "internal":
        raise HTTPException(
            status_code=403,
            detail="La creación directa de grupos está reservada a staff MYC",
        )
    return create_work_order_group(db, payload, context.user, operator_client_id=None)


@router.get("/group-requests/review", response_model=list[LabWorkOrderGroupRequestRead])
def get_mobile_staff_group_requests(
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_work_order_groups.requests.read")
    ),
) -> list[LabWorkOrderGroupRequestRead]:
    if context.actor_type != "internal":
        raise HTTPException(status_code=403, detail="La bandeja de revisión es exclusiva de staff MYC")
    return list_group_requests(db)


@router.post("/group-requests/{request_id}/claim", response_model=LabWorkOrderGroupRequestRead)
def claim_mobile_staff_group_request(
    request_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_work_order_groups.requests.claim")
    ),
) -> LabWorkOrderGroupRequestRead:
    if context.actor_type != "internal":
        raise HTTPException(status_code=403, detail="La atención de solicitudes es exclusiva de staff MYC")
    return claim_group_request(db, request_id, context.user)


@router.post("/group-requests/{request_id}/approve", response_model=LabWorkOrderGroupRequestRead)
def approve_mobile_staff_group_request(
    request_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_work_order_groups.requests.decide")
    ),
) -> LabWorkOrderGroupRequestRead:
    if context.actor_type != "internal":
        raise HTTPException(status_code=403, detail="La decisión de solicitudes es exclusiva de staff MYC")
    return approve_group_request(db, request_id, context.user)


@router.post("/group-requests/{request_id}/reject", response_model=LabWorkOrderGroupRequestRead)
def reject_mobile_staff_group_request(
    request_id: int,
    payload: LabWorkOrderGroupDecision,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_work_order_groups.requests.decide")
    ),
) -> LabWorkOrderGroupRequestRead:
    if context.actor_type != "internal":
        raise HTTPException(status_code=403, detail="La decisión de solicitudes es exclusiva de staff MYC")
    return reject_group_request(db, request_id, context.user, payload.reason)


@staff_router.post("", response_model=LabWorkOrderRead, status_code=201)
def create_staff_group(
    payload: LabWorkOrderGroupCreate,
    operator_client_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(require_permission("lab_work_order_groups.create")),
) -> LabWorkOrderRead:
    return create_work_order_group(
        db, payload, user, operator_client_id=operator_client_id
    )


@staff_router.get("/requests", response_model=list[LabWorkOrderGroupRequestRead])
def get_staff_group_requests(
    db: Session = Depends(get_db),
    _user=Depends(require_permission("lab_work_order_groups.requests.read")),
) -> list[LabWorkOrderGroupRequestRead]:
    return list_group_requests(db)


@staff_router.post("/requests/{request_id}/claim", response_model=LabWorkOrderGroupRequestRead)
def claim_staff_group_request(
    request_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("lab_work_order_groups.requests.claim")),
) -> LabWorkOrderGroupRequestRead:
    return claim_group_request(db, request_id, user)


@staff_router.post("/requests/{request_id}/approve", response_model=LabWorkOrderGroupRequestRead)
def approve_staff_group_request(
    request_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_permission("lab_work_order_groups.requests.decide")),
) -> LabWorkOrderGroupRequestRead:
    return approve_group_request(db, request_id, user)


@staff_router.post("/requests/{request_id}/reject", response_model=LabWorkOrderGroupRequestRead)
def reject_staff_group_request(
    request_id: int,
    payload: LabWorkOrderGroupDecision,
    db: Session = Depends(get_db),
    user=Depends(require_permission("lab_work_order_groups.requests.decide")),
) -> LabWorkOrderGroupRequestRead:
    return reject_group_request(db, request_id, user, payload.reason)


@router.post("", response_model=LabWorkOrderRead, status_code=201)
def create_lab_work_order(
    payload: LabWorkOrderCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.create", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    if context.actor_type == "client":
        raise HTTPException(
            status_code=403,
            detail="Los actores externos deben solicitar un grupo de OT",
        )
    return create_work_order(
        db,
        payload,
        context.user,
        operator_client_id=context.client_id,
    )


@router.get("", response_model=list[LabWorkOrderListItem])
def list_lab_work_orders(
    folio: str | None = Query(default=None, max_length=20),
    client: str | None = Query(default=None, max_length=255),
    status: Literal["all", "open", "completed"] = "all",
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.read_organization", "lab_work_orders.use")
    ),
) -> list[LabWorkOrderListItem]:
    return list_work_orders(
        db,
        folio=folio,
        client=client,
        work_order_status=status,
        offset=offset,
        limit=limit,
        operator_client_id=context.client_id,
    )


@router.get("/export")
def export_lab_work_orders(
    db: Session = Depends(get_db),
    _context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_work_orders.export")
    ),
) -> Response:
    content, filename = export_all(db)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/field-sheet-templates", response_model=list[FieldSheetTemplateRead])
def get_lab_field_sheet_templates(
    db: Session = Depends(get_db),
    _context: MobileSecurityContext = Depends(
        require_mobile_permission("field_sheet_templates.read")
    ),
) -> list[FieldSheetTemplateRead]:
    return list_field_sheet_templates(db, include_all=False)


@router.get("/linked-companies")
def get_lab_linked_companies(
    db: Session = Depends(get_db),
    _context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.read_organization", "lab_work_orders.use")
    ),
) -> list[dict]:
    rows = db.scalars(
        select(LinkedCompany)
        .where(LinkedCompany.is_active.is_(True))
        .order_by(LinkedCompany.name)
    ).all()
    return [
        {"id": item.id, "name": item.name, "default_certificate_prefix": item.default_certificate_prefix}
        for item in rows
    ]


@router.get("/{work_order_id}", response_model=LabWorkOrderRead)
def get_lab_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.read_organization", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return get_work_order(db, work_order_id)


@router.delete("/{work_order_id}", status_code=204)
def remove_lab_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_work_orders.delete")
    ),
) -> None:
    ensure_lab_work_order_scope(db, work_order_id, context)
    delete_work_order(db, work_order_id, context.user)


@router.patch("/{work_order_id}", response_model=LabWorkOrderRead)
def patch_lab_work_order(
    work_order_id: int,
    payload: LabWorkOrderUpdate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.execute", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return update_work_order(
        db,
        work_order_id,
        payload,
        context.user,
        operator_client_id=context.client_id,
    )


@router.patch("/{work_order_id}/reception-date", response_model=LabWorkOrderRead)
def patch_lab_reception_date(
    work_order_id: int,
    payload: LabReceptionDateUpdate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.create", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    if context.actor_type != "internal":
        raise HTTPException(status_code=403, detail="Esta capacidad es exclusiva de staff MYC")
    ensure_lab_work_order_scope(db, work_order_id, context)
    return update_reception_date(db, work_order_id, payload, context.user)


@router.post("/{work_order_id}/equipment", response_model=LabWorkOrderRead, status_code=201)
def create_lab_equipment(
    work_order_id: int,
    payload: LabEquipmentWrite,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("equipment.write", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return add_equipment(db, work_order_id, payload, context.user)


@router.put("/{work_order_id}/equipment/{equipment_id}/service", response_model=LabWorkOrderRead)
def put_lab_equipment_service(
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentServiceWrite,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("field_sheets.capture", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return assign_equipment_service(
        db,
        work_order_id,
        equipment_id,
        payload,
        context.user,
        external=context.actor_type == "client",
    )


@router.post(
    "/{work_order_id}/equipment/configured", response_model=LabWorkOrderRead, status_code=201
)
def post_lab_equipment_configured(
    work_order_id: int,
    payload: LabEquipmentConfiguredCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("equipment.write", "field_sheets.capture", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    """Fase 2F: alta integrada -- equipo + cliente documental + servicio/folio
    en una sola operación atómica. Equivalente funcional a encadenar POST
    equipment + PATCH certificate-client + PUT service, pero con una única
    transacción (ver create_configured_equipment). Los tres endpoints
    anteriores se conservan intactos para compatibilidad."""
    ensure_lab_work_order_scope(db, work_order_id, context)
    return create_configured_equipment(
        db,
        work_order_id,
        payload,
        context.user,
        operator_client_id=context.client_id,
        external=context.actor_type == "client",
    )


@router.patch(
    "/{work_order_id}/equipment/{equipment_id}/configured", response_model=LabWorkOrderRead
)
def patch_lab_equipment_configured(
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentConfiguredCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("equipment.write", "field_sheets.capture", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    """Fase 2 hardening: edición integrada -- datos del equipo + cliente
    documental + servicio/folio de un equipo YA EXISTENTE, en una sola
    transacción (ver update_configured_equipment). El botón único "Guardar"
    de la edición Mobile ahora corresponde a UNA sola llamada: si el 409 de
    folio ya reservado ocurre, ningún otro cambio de la edición persiste. Los
    endpoints PATCH equipo / PATCH certificate-client / PUT service se
    conservan intactos para compatibilidad."""
    ensure_lab_work_order_scope(db, work_order_id, context)
    return update_configured_equipment(
        db,
        work_order_id,
        equipment_id,
        payload,
        context.user,
        operator_client_id=context.client_id,
        external=context.actor_type == "client",
    )


@router.patch(
    "/{work_order_id}/equipment/{equipment_id}/certificate-client", response_model=LabWorkOrderRead
)
def patch_lab_equipment_certificate_client(
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentCertificateClientWrite,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("equipment.write", "field_sheets.capture", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    """Fase 2C/2G: editar el cliente documental de un equipo ya existente,
    mientras la OT siga editable. La FK es procedencia; el snapshot es la
    autoridad histórica (set_equipment_certificate_client, Fase 1A)."""
    ensure_lab_work_order_scope(db, work_order_id, context)
    return set_equipment_certificate_client(
        db,
        work_order_id,
        equipment_id,
        payload,
        context.user,
        operator_client_id=context.client_id,
    )


@router.post("/{work_order_id}/equipment/{equipment_id}/field-sheet", response_model=FieldSheetRead, status_code=201)
def post_lab_field_sheet(
    work_order_id: int,
    equipment_id: int,
    payload: LabFieldSheetCreate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission(
            "field_sheets.capture", "lab_work_orders.use", "lab_field_sheets.capture"
        )
    ),
) -> FieldSheetRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return create_lab_field_sheet(
        db, work_order_id, equipment_id, payload, context.user,
        external=context.actor_type == "client",
    )


@router.get("/{work_order_id}/equipment/{equipment_id}/field-sheet", response_model=FieldSheetRead)
def get_lab_field_sheet(
    work_order_id: int,
    equipment_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission(
            "work_orders.read_organization", "lab_work_orders.use", "lab_field_sheets.capture"
        )
    ),
) -> FieldSheetRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return read_lab_field_sheet(db, work_order_id, equipment_id)


@router.get("/{work_order_id}/equipment/{equipment_id}/field-sheet/pdf")
def get_lab_field_sheet_pdf(
    work_order_id: int,
    equipment_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission(
            "work_orders.read_organization", "lab_work_orders.use", "lab_field_sheets.capture"
        )
    ),
) -> Response:
    """Expone vía auth Mobile el PDF institucional que ya genera
    generate_field_sheet_pdf (mismo backend/documento que usa el router
    productivo field_sheets.py) -- sin renderer ni PDF paralelo."""
    ensure_lab_work_order_scope(db, work_order_id, context)
    sheet = read_lab_field_sheet(db, work_order_id, equipment_id)
    content, filename = generate_field_sheet_pdf(db, sheet.id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.patch("/{work_order_id}/equipment/{equipment_id}/field-sheet", response_model=FieldSheetRead)
def patch_lab_field_sheet(
    work_order_id: int,
    equipment_id: int,
    payload: FieldSheetUpdate,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission(
            "field_sheets.capture", "lab_work_orders.use", "lab_field_sheets.capture"
        )
    ),
) -> FieldSheetRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return update_lab_field_sheet(db, work_order_id, equipment_id, payload, context.user)


@router.delete("/{work_order_id}/equipment/{equipment_id}/field-sheet", status_code=204)
def delete_lab_field_sheet(
    work_order_id: int,
    equipment_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission(
            "field_sheets.capture", "lab_work_orders.use", "lab_field_sheets.capture"
        )
    ),
) -> None:
    ensure_lab_work_order_scope(db, work_order_id, context)
    discard_lab_field_sheet(db, work_order_id, equipment_id, context.user)


@router.post("/{work_order_id}/equipment/{equipment_id}/field-sheet/complete", response_model=FieldSheetRead)
def post_complete_lab_field_sheet(
    work_order_id: int,
    equipment_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission(
            "field_sheets.capture", "lab_work_orders.use", "lab_field_sheets.capture"
        )
    ),
) -> FieldSheetRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return complete_lab_field_sheet(db, work_order_id, equipment_id, context.user)


@router.patch("/{work_order_id}/equipment/{equipment_id}", response_model=LabWorkOrderRead)
def patch_lab_equipment(
    work_order_id: int,
    equipment_id: int,
    payload: LabEquipmentWrite,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("equipment.write", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return update_equipment(db, work_order_id, equipment_id, payload, context.user)


@router.delete("/{work_order_id}/equipment/{equipment_id}", response_model=LabWorkOrderRead)
def remove_lab_equipment(
    work_order_id: int,
    equipment_id: int,
    expected_edit_version: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("equipment.write", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return delete_equipment(
        db,
        work_order_id,
        equipment_id,
        context.user,
        expected_edit_version=expected_edit_version,
    )


@router.post("/{work_order_id}/additional", response_model=LabWorkOrderRead, status_code=201)
def create_lab_additional_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.execute", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    if context.actor_type == "client":
        raise HTTPException(
            status_code=403,
            detail="Los actores externos no pueden materializar OT adicionales",
        )
    return create_additional_work_order(db, work_order_id, context.user)


@router.post("/{work_order_id}/signatures", response_model=LabWorkOrderRead)
def create_lab_group_signatures(
    work_order_id: int,
    payload: LabSignatureGroupWrite,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("signatures.capture", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    """Fase 3: firma de RECEPCIÓN (equipos y condiciones recibidos), no de
    cierre técnico. Produce draft -> received_signed cuando ambas firmas son
    válidas y la cohorte cumple los prerrequisitos de recepción (ver
    sign_group/_ensure_reception_prerequisites)."""
    ensure_lab_work_order_scope(db, work_order_id, context)
    return sign_group(db, work_order_id, payload, context.user)


@router.post("/{work_order_id}/signatures/individual", response_model=LabWorkOrderRead)
def create_lab_individual_signatures(
    work_order_id: int,
    payload: LabSignatureGroupWrite,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("signatures.capture", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return sign_individual(db, work_order_id, payload, context.user)


@router.post("/{work_order_id}/complete", response_model=LabWorkOrderRead)
def complete_lab_group(
    work_order_id: int,
    confirm_draft_completion: bool = Query(default=False),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        # Fase 5 (corregido post-auditoría): cierre técnico es autoridad
        # exclusivamente interna de MYC -- ningún actor externo/portal
        # (external_operator_jr/sr) recibe work_orders.close (ver
        # app/services/portal/permission_service.py). Hoy sólo staff interno
        # con lab_work_orders.use puede cerrar; work_orders.close queda
        # definido para asignarse a un rol interno "Operativo Sr" cuando el
        # catálogo interno lo formalice.
        require_mobile_permission("work_orders.close", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return complete_group(
        db, work_order_id, context.user,
        require_completed_sheets=context.actor_type == "internal",
        confirm_draft_completion=confirm_draft_completion,
    )


@router.post("/{work_order_id}/complete/individual", response_model=LabWorkOrderRead)
def complete_lab_individual(
    work_order_id: int,
    confirm_draft_completion: bool = Query(default=False),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.close", "lab_work_orders.use")
    ),
) -> LabWorkOrderRead:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return complete_individual(
        db, work_order_id, context.user,
        require_completed_sheets=context.actor_type == "internal",
        confirm_draft_completion=confirm_draft_completion,
    )


@router.get("/{work_order_id}/pdf")
def get_lab_pdf(
    work_order_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.read_organization", "lab_work_orders.use")
    ),
) -> Response:
    ensure_lab_work_order_scope(db, work_order_id, context)
    content, filename = get_pdf(db, work_order_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/{work_order_id}/package")
def get_lab_package(
    work_order_id: int,
    group: bool = Query(default=False),
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_packages.download", "work_orders.read_organization")
    ),
) -> Response:
    ensure_lab_work_order_scope(db, work_order_id, context)
    content, filename = generate_lab_package(
        db, work_order_id, context.user, group=group
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/{work_order_id}/cancel", response_model=LabWorkOrderRead)
def post_cancel_lab_work_order(
    work_order_id: int,
    payload: LabCancellationWrite,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_work_orders.cancel")
    ),
) -> LabWorkOrderRead:
    if context.actor_type != "internal":
        raise HTTPException(status_code=403, detail="La cancelación está reservada a Admin")
    return cancel_work_order(db, work_order_id, context.user, payload.reason)


@router.post("/{work_order_id}/restore", response_model=LabWorkOrderRead)
def post_restore_lab_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("lab_work_orders.cancel")
    ),
) -> LabWorkOrderRead:
    if context.actor_type != "internal":
        raise HTTPException(status_code=403, detail="La restauración está reservada a Admin")
    return restore_work_order(db, work_order_id, context.user)


@router.post("/{work_order_id}/reopen", response_model=LabWorkOrderRead)
def post_reopen_lab_work_order_directly(
    work_order_id: int,
    payload: LabDirectReopenWrite,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.reopen")
    ),
) -> LabWorkOrderRead:
    """Reapertura administrativa directa -- exclusiva de quien YA tiene
    work_orders.reopen + la política correspondiente (verificado de nuevo
    dentro del servicio). No pasa por tickets; ver reopen_work_order_directly."""
    if context.actor_type != "internal":
        raise HTTPException(status_code=403, detail="La reapertura directa está reservada a Admin")
    return reopen_work_order_directly(
        db, work_order_id, context.user,
        signature_policy=payload.requested_signature_policy,
        reason=payload.reason,
    )


@router.get("/{work_order_id}/revisions", response_model=list[LabRevisionRead])
def get_lab_revisions(
    work_order_id: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.read_organization", "lab_work_orders.use")
    ),
) -> list[LabRevisionRead]:
    ensure_lab_work_order_scope(db, work_order_id, context)
    return list_revisions(db, work_order_id)


@router.get("/{work_order_id}/revisions/{revision_number}/pdf")
def get_lab_revision_pdf(
    work_order_id: int,
    revision_number: int,
    db: Session = Depends(get_db),
    context: MobileSecurityContext = Depends(
        require_mobile_permission("work_orders.read_organization", "lab_work_orders.use")
    ),
) -> Response:
    ensure_lab_work_order_scope(db, work_order_id, context)
    content, filename = get_revision_pdf(db, work_order_id, revision_number)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
