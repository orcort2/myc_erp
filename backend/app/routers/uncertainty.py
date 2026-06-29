from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.uncertainty import (
    UncertaintyComponentCreate,
    UncertaintyComponentRead,
    UncertaintyComponentUpdate,
    UncertaintyFormulaCreate,
    UncertaintyFormulaRead,
    UncertaintyFormulaUpdate,
    UncertaintyModelCreate,
    UncertaintyModelExceptionCreate,
    UncertaintyModelExceptionRead,
    UncertaintyModelRead,
    UncertaintyModelUpdate,
    UncertaintyModelVersionCreate,
    UncertaintyModelVersionRead,
    UncertaintyModelVersionUpdate,
    UncertaintyPreview,
)
from app.services.auth import require_permission
from app.services.uncertainty_engine import (
    add_uncertainty_component,
    add_uncertainty_formula,
    change_uncertainty_model_version_status,
    clone_uncertainty_model_version,
    create_uncertainty_exception,
    create_uncertainty_model,
    create_uncertainty_model_version,
    delete_uncertainty_component,
    delete_uncertainty_formula,
    get_uncertainty_model,
    get_uncertainty_model_version,
    list_uncertainty_exceptions,
    list_uncertainty_model_versions,
    list_uncertainty_models,
    preview_uncertainty_calculation,
    update_uncertainty_component,
    update_uncertainty_formula,
    update_uncertainty_model,
    update_uncertainty_model_version,
)


router = APIRouter(prefix="/uncertainty", tags=["uncertainty"])


@router.get("/models", response_model=list[UncertaintyModelRead])
def get_uncertainty_models(
    include_inactive: bool = Query(default=False),
    magnitude: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.read")),
) -> list[UncertaintyModelRead]:
    return list_uncertainty_models(
        db,
        include_inactive=include_inactive,
        magnitude=magnitude,
        status_value=status_value,
    )


@router.post("/models", response_model=UncertaintyModelRead, status_code=status.HTTP_201_CREATED)
def post_uncertainty_model(
    payload: UncertaintyModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.create")),
) -> UncertaintyModelRead:
    return create_uncertainty_model(db, payload, user_id=current_user.id)


@router.get("/models/{model_id}", response_model=UncertaintyModelRead)
def get_uncertainty_model_by_id(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.read")),
) -> UncertaintyModelRead:
    return get_uncertainty_model(db, model_id)


@router.patch("/models/{model_id}", response_model=UncertaintyModelRead)
def patch_uncertainty_model(
    model_id: int,
    payload: UncertaintyModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.update")),
) -> UncertaintyModelRead:
    return update_uncertainty_model(db, model_id, payload, user_id=current_user.id)


@router.get("/models/{model_id}/versions", response_model=list[UncertaintyModelVersionRead])
def get_uncertainty_model_versions(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.read")),
) -> list[UncertaintyModelVersionRead]:
    return list_uncertainty_model_versions(db, model_id)


@router.post(
    "/models/{model_id}/versions",
    response_model=UncertaintyModelVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def post_uncertainty_model_version(
    model_id: int,
    payload: UncertaintyModelVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.create")),
) -> UncertaintyModelVersionRead:
    return create_uncertainty_model_version(db, model_id, payload, user_id=current_user.id)


@router.get("/model-versions/{version_id}", response_model=UncertaintyModelVersionRead)
def get_uncertainty_model_version_by_id(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.read")),
) -> UncertaintyModelVersionRead:
    return get_uncertainty_model_version(db, version_id)


@router.patch("/model-versions/{version_id}", response_model=UncertaintyModelVersionRead)
def patch_uncertainty_model_version(
    version_id: int,
    payload: UncertaintyModelVersionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.update")),
) -> UncertaintyModelVersionRead:
    return update_uncertainty_model_version(db, version_id, payload, user_id=current_user.id)


@router.post("/model-versions/{version_id}/submit-review", response_model=UncertaintyModelVersionRead)
def submit_uncertainty_model_version_review(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.update")),
) -> UncertaintyModelVersionRead:
    return change_uncertainty_model_version_status(
        db, version_id, "submit-review", user_id=current_user.id
    )


@router.post("/model-versions/{version_id}/approve", response_model=UncertaintyModelVersionRead)
def approve_uncertainty_model_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.approve")),
) -> UncertaintyModelVersionRead:
    return change_uncertainty_model_version_status(db, version_id, "approve", user_id=current_user.id)


@router.post("/model-versions/{version_id}/obsolete", response_model=UncertaintyModelVersionRead)
def obsolete_uncertainty_model_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.approve")),
) -> UncertaintyModelVersionRead:
    return change_uncertainty_model_version_status(db, version_id, "obsolete", user_id=current_user.id)


@router.post("/model-versions/{version_id}/archive", response_model=UncertaintyModelVersionRead)
def archive_uncertainty_model_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.approve")),
) -> UncertaintyModelVersionRead:
    return change_uncertainty_model_version_status(db, version_id, "archive", user_id=current_user.id)


@router.post("/model-versions/{version_id}/clone", response_model=UncertaintyModelVersionRead)
def clone_uncertainty_model_version_route(
    version_id: int,
    payload: UncertaintyModelVersionCreate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.create")),
) -> UncertaintyModelVersionRead:
    return clone_uncertainty_model_version(db, version_id, payload, user_id=current_user.id)


@router.post(
    "/model-versions/{version_id}/components",
    response_model=UncertaintyModelVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def post_uncertainty_component(
    version_id: int,
    payload: UncertaintyComponentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.update")),
) -> UncertaintyModelVersionRead:
    return add_uncertainty_component(db, version_id, payload, user_id=current_user.id)


@router.patch("/components/{component_id}", response_model=UncertaintyComponentRead)
def patch_uncertainty_component(
    component_id: int,
    payload: UncertaintyComponentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.update")),
) -> UncertaintyComponentRead:
    return update_uncertainty_component(db, component_id, payload, user_id=current_user.id)


@router.delete("/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_uncertainty_component_route(
    component_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.update")),
) -> Response:
    delete_uncertainty_component(db, component_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/model-versions/{version_id}/formulas",
    response_model=UncertaintyModelVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def post_uncertainty_formula(
    version_id: int,
    payload: UncertaintyFormulaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.update")),
) -> UncertaintyModelVersionRead:
    return add_uncertainty_formula(db, version_id, payload, user_id=current_user.id)


@router.patch("/formulas/{formula_id}", response_model=UncertaintyFormulaRead)
def patch_uncertainty_formula(
    formula_id: int,
    payload: UncertaintyFormulaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.update")),
) -> UncertaintyFormulaRead:
    return update_uncertainty_formula(db, formula_id, payload, user_id=current_user.id)


@router.delete("/formulas/{formula_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_uncertainty_formula_route(
    formula_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.update")),
) -> Response:
    delete_uncertainty_formula(db, formula_id, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/exceptions", response_model=list[UncertaintyModelExceptionRead])
def get_uncertainty_exceptions(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.read")),
) -> list[UncertaintyModelExceptionRead]:
    return list_uncertainty_exceptions(db, include_inactive=include_inactive)


@router.post(
    "/exceptions",
    response_model=UncertaintyModelExceptionRead,
    status_code=status.HTTP_201_CREATED,
)
def post_uncertainty_exception(
    payload: UncertaintyModelExceptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty_models.exception")),
) -> UncertaintyModelExceptionRead:
    return create_uncertainty_exception(db, payload, user_id=current_user.id)


@router.get("/field-sheets/{field_sheet_id}/preview", response_model=UncertaintyPreview)
def get_uncertainty_preview(
    field_sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("uncertainty.execute")),
) -> UncertaintyPreview:
    return preview_uncertainty_calculation(db, field_sheet_id)
