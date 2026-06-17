from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.services.clients import (
    create_client,
    deactivate_client,
    get_client,
    list_clients,
    update_client,
)


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
def get_clients(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> list[ClientRead]:
    return list_clients(db, include_inactive=include_inactive)


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def post_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
) -> ClientRead:
    return create_client(db, payload)


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


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)) -> Response:
    deactivate_client(db, client_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

