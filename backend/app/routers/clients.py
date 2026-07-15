from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.client import (
    ClientCertificateProfileCreate,
    ClientCertificateProfileRead,
    ClientCertificateProfileUpdate,
    ClientCreate,
    ClientDeleteEligibilityRead,
    ClientDeleteResultRead,
    ClientImportConfirm,
    ClientImportPreviewRead,
    ClientImportResultRead,
    ClientRead,
    ClientRestoreResultRead,
    ClientTaxConstancyPreviewRead,
    ClientUpdate,
)
from app.services.clients import (
    confirm_client_import,
    create_client_certificate_profile,
    create_client,
    archive_client,
    delete_client_permanently,
    deactivate_client_certificate_profile,
    export_clients_workbook,
    get_client,
    get_client_delete_eligibility,
    list_clients,
    list_client_certificate_profiles,
    preview_client_import,
    preview_tax_constancy,
    restore_client,
    upload_tax_constancy,
    update_client,
    update_client_certificate_profile,
)
from app.services.auth import require_permission


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
def get_clients(
    include_inactive: bool = Query(default=False),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[ClientRead]:
    return list_clients(db, include_inactive=include_inactive, search=search, status_filter=status_filter)


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def post_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
) -> ClientRead:
    return create_client(db, payload)


@router.get("/export")
def export_clients(
    include_inactive: bool = Query(default=True),
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    file_bytes, filename = export_clients_workbook(
        db,
        include_inactive=include_inactive,
        search=search,
        status_filter=status_filter,
    )
    return StreamingResponse(
        iter([file_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import/preview", response_model=ClientImportPreviewRead)
def preview_import(file: UploadFile = File(...), db: Session = Depends(get_db)) -> ClientImportPreviewRead:
    return preview_client_import(db, file)


@router.post("/import/confirm", response_model=ClientImportResultRead)
def confirm_import(payload: ClientImportConfirm, db: Session = Depends(get_db)) -> ClientImportResultRead:
    return confirm_client_import(db, payload)


@router.post("/tax-constancy/preview", response_model=ClientTaxConstancyPreviewRead)
def preview_constancy(file: UploadFile = File(...)) -> ClientTaxConstancyPreviewRead:
    return preview_tax_constancy(file)


@router.get("/{client_id}", response_model=ClientRead)
def get_client_by_id(client_id: int, db: Session = Depends(get_db)) -> ClientRead:
    return get_client(db, client_id)


@router.patch("/{client_id}", response_model=ClientRead)
def patch_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
) -> ClientRead:
    return update_client(db, client_id, payload)


@router.post("/{client_id}/tax-constancy", response_model=ClientRead)
def post_tax_constancy(
    client_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ClientRead:
    return upload_tax_constancy(db, client_id, file)


@router.get("/{client_id}/certificate-profiles", response_model=list[ClientCertificateProfileRead])
def get_certificate_profiles(client_id: int, db: Session = Depends(get_db)) -> list[ClientCertificateProfileRead]:
    return list_client_certificate_profiles(db, client_id)


@router.post(
    "/{client_id}/certificate-profiles",
    response_model=ClientCertificateProfileRead,
    status_code=status.HTTP_201_CREATED,
)
def post_certificate_profile(
    client_id: int, payload: ClientCertificateProfileCreate, db: Session = Depends(get_db)
) -> ClientCertificateProfileRead:
    return create_client_certificate_profile(db, client_id, payload)


@router.patch(
    "/{client_id}/certificate-profiles/{profile_id}", response_model=ClientCertificateProfileRead
)
def patch_certificate_profile(
    client_id: int,
    profile_id: int,
    payload: ClientCertificateProfileUpdate,
    db: Session = Depends(get_db),
) -> ClientCertificateProfileRead:
    return update_client_certificate_profile(db, client_id, profile_id, payload)


@router.delete("/{client_id}/certificate-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_certificate_profile(client_id: int, profile_id: int, db: Session = Depends(get_db)) -> Response:
    deactivate_client_certificate_profile(db, client_id, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{client_id}/delete-eligibility", response_model=ClientDeleteEligibilityRead)
def get_delete_eligibility(client_id: int, db: Session = Depends(get_db)) -> ClientDeleteEligibilityRead:
    return get_client_delete_eligibility(db, client_id)


@router.post("/{client_id}/archive", response_model=ClientDeleteResultRead)
def archive_client_by_id(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.update")),
) -> ClientDeleteResultRead:
    was_active = get_client(db, client_id, include_inactive=True).is_active
    client = archive_client(db, client_id, user_id=current_user.id)
    eligibility = get_client_delete_eligibility(db, client_id)
    return ClientDeleteResultRead(
        status="archived" if was_active else "already_archived",
        delete_mode="archive",
        client_id=client_id,
        message="El cliente fue archivado." if was_active else "El cliente ya estaba archivado.",
        blocking_dependencies=eligibility.blocking_dependencies,
    )


@router.post("/{client_id}/restore", response_model=ClientRestoreResultRead)
def restore_client_by_id(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.update")),
) -> ClientRestoreResultRead:
    was_active = get_client(db, client_id, include_inactive=True).is_active
    client = restore_client(db, client_id, user_id=current_user.id)
    return ClientRestoreResultRead(
        status="already_active" if was_active else "restored",
        client_id=client_id,
        message="El cliente ya estaba activo." if was_active else "El cliente fue restaurado.",
    )


@router.delete("/{client_id}", response_model=ClientDeleteResultRead)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.update")),
) -> ClientDeleteResultRead:
    return delete_client_permanently(db, client_id, user_id=current_user.id)
