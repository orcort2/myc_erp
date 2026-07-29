"""API administrativa interna del Centro de Resoluciones v1."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.user import User
from app.resolution_center.query import (
    ResolutionCenterCursorError,
    ResolutionCenterNotFoundError,
    ResolutionOperationsQueryService,
)
from app.resolution_center.schemas import (
    AuthorizationRequest,
    CenterCapabilities,
    CreateAdministrativeResolutionRequest,
    OperationAccepted,
    ResolutionCenterIndicators,
    ResolutionCollection,
    ResolutionDefinitionResource,
    ResolutionDetail,
    TimelineEntry,
)
from app.resolution_center.workflow import (
    ResolutionCenterWorkflowError,
    ResolutionCenterWorkflowService,
)
from app.services.auth import require_permission, user_has_permission


router = APIRouter(
    prefix="/resolution-center/v1",
    tags=["resolution-center"],
)


def _can_read_all(user: User) -> bool:
    return user_has_permission(user, "resolution_center.read_all")


def _technical(user: User) -> bool:
    return user_has_permission(user, "resolution_center.infrastructure")


def _actor_id(user: User) -> str:
    return f"user:{user.id}"


def _workflow_error(exc: ResolutionCenterWorkflowError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    )


@router.get("/capabilities", response_model=CenterCapabilities)
def capabilities(
    current_user: User = Depends(require_permission("resolution_center.read")),
) -> CenterCapabilities:
    check = lambda permission: user_has_permission(current_user, permission)
    return CenterCapabilities(
        can_read=True,
        can_create=(
            check("resolution_center.create")
            or check("service_orders.additional_equipment.propose")
        ),
        can_prepare=check("resolution_center.prepare"),
        can_analyze=check("resolution_center.analyze"),
        can_plan=check("resolution_center.plan"),
        can_simulate=check("resolution_center.simulate"),
        can_authorize=(
            check("resolution_center.authorize")
            or check("service_orders.additional_equipment.authorize")
        ),
        can_execute=(
            check("resolution_center.execute")
            or check("service_orders.additional_equipment.execute")
        ),
        can_audit=check("resolution_center.audit"),
        can_view_infrastructure=check("resolution_center.infrastructure"),
    )


@router.get(
    "/definitions",
    response_model=tuple[ResolutionDefinitionResource, ...],
)
def definitions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resolution_center.read")),
):
    del current_user
    return ResolutionCenterWorkflowService(db).definitions()


@router.get("/resolutions", response_model=ResolutionCollection)
def list_resolutions(
    search: str | None = Query(default=None, max_length=240),
    requester: str | None = Query(default=None, max_length=160),
    authorizer: str | None = Query(default=None, max_length=160),
    resolution_type: str | None = Query(default=None, max_length=160),
    subject_type: str | None = Query(default=None, max_length=100),
    subject_id: str | None = Query(default=None, max_length=160),
    lifecycle_status: str | None = Query(default=None, max_length=40),
    distributed_status: str | None = Query(default=None, max_length=24),
    result: str | None = Query(default=None, max_length=32),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    has_retries: bool | None = None,
    blocked: bool | None = None,
    compensated: bool | None = None,
    cursor: str | None = Query(default=None, max_length=1000),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resolution_center.read")),
) -> ResolutionCollection:
    try:
        return ResolutionOperationsQueryService(db).list(
            organization_id=settings.resolution_center_organization_id,
            actor_id=_actor_id(current_user),
            can_read_all=_can_read_all(current_user),
            search=search,
            requester=requester,
            authorizer=authorizer,
            resolution_type=resolution_type,
            subject_type=subject_type,
            subject_id=subject_id,
            lifecycle_status=lifecycle_status,
            distributed_status=distributed_status,
            result=result,
            created_from=created_from,
            created_to=created_to,
            has_retries=has_retries,
            blocked=blocked,
            compensated=compensated,
            cursor=cursor,
            limit=limit,
        )
    except ResolutionCenterCursorError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_cursor", "message": str(exc)},
        ) from None


@router.get("/indicators", response_model=ResolutionCenterIndicators)
def indicators(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resolution_center.read")),
) -> ResolutionCenterIndicators:
    return ResolutionOperationsQueryService(db).indicators(
        organization_id=settings.resolution_center_organization_id,
        actor_id=_actor_id(current_user),
        can_read_all=_can_read_all(current_user),
    )


@router.get(
    "/resolutions/{public_id}",
    response_model=ResolutionDetail,
)
def get_resolution(
    public_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resolution_center.read")),
) -> ResolutionDetail:
    try:
        return ResolutionOperationsQueryService(db).get(
            public_id,
            organization_id=settings.resolution_center_organization_id,
            actor_id=_actor_id(current_user),
            can_read_all=_can_read_all(current_user),
            include_technical=_technical(current_user),
            include_audit=user_has_permission(
                current_user, "resolution_center.audit"
            ),
        )
    except ResolutionCenterNotFoundError:
        raise HTTPException(status_code=404, detail="Resolución no encontrada") from None


@router.get(
    "/resolutions/{public_id}/timeline",
    response_model=tuple[TimelineEntry, ...],
)
def get_timeline(
    public_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resolution_center.read")),
) -> tuple[TimelineEntry, ...]:
    return get_resolution(public_id, db, current_user).lifecycle


@router.post(
    "/resolutions",
    response_model=OperationAccepted,
    status_code=201,
)
def create_resolution(
    payload: CreateAdministrativeResolutionRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resolution_center.read")),
) -> OperationAccepted:
    if not idempotency_key or len(idempotency_key) > 120:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key es obligatorio",
        )
    try:
        return ResolutionCenterWorkflowService(db).create(
            payload,
            user=current_user,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    except ResolutionCenterWorkflowError as exc:
        db.rollback()
        raise _workflow_error(exc) from None


def _stage(
    method: str,
    public_id: str,
    db: Session,
    current_user: User,
    correlation_id: str | None,
) -> OperationAccepted:
    try:
        return getattr(ResolutionCenterWorkflowService(db), method)(
            public_id,
            user=current_user,
            correlation_id=correlation_id,
        )
    except ResolutionCenterWorkflowError as exc:
        db.rollback()
        raise _workflow_error(exc) from None


@router.post(
    "/resolutions/{public_id}/prepare-context",
    response_model=OperationAccepted,
)
def prepare_context(
    public_id: str,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("resolution_center.prepare")
    ),
):
    return _stage("prepare_context", public_id, db, current_user, correlation_id)


@router.post(
    "/resolutions/{public_id}/analyze",
    response_model=OperationAccepted,
)
def analyze(
    public_id: str,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("resolution_center.analyze")
    ),
):
    return _stage("analyze", public_id, db, current_user, correlation_id)


@router.post(
    "/resolutions/{public_id}/build-plan",
    response_model=OperationAccepted,
)
def build_plan(
    public_id: str,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("resolution_center.plan")
    ),
):
    return _stage("build_plan", public_id, db, current_user, correlation_id)


@router.post(
    "/resolutions/{public_id}/simulate",
    response_model=OperationAccepted,
)
def simulate(
    public_id: str,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("resolution_center.simulate")
    ),
):
    return _stage("simulate", public_id, db, current_user, correlation_id)


@router.post(
    "/resolutions/{public_id}/authorize",
    response_model=OperationAccepted,
)
def authorize(
    public_id: str,
    payload: AuthorizationRequest,
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resolution_center.read")),
):
    try:
        return ResolutionCenterWorkflowService(db).authorize(
            public_id,
            payload,
            user=current_user,
            correlation_id=correlation_id,
        )
    except ResolutionCenterWorkflowError as exc:
        db.rollback()
        raise _workflow_error(exc) from None


@router.post(
    "/resolutions/{public_id}/execute",
    response_model=OperationAccepted,
    status_code=202,
)
def execute(
    public_id: str,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("resolution_center.read")),
):
    if not idempotency_key or len(idempotency_key) > 120:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key es obligatorio",
        )
    try:
        return ResolutionCenterWorkflowService(db).execute(
            public_id,
            user=current_user,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    except ResolutionCenterWorkflowError as exc:
        db.rollback()
        raise _workflow_error(exc) from None
