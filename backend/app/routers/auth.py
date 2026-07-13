from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.auth import (
    RefreshTokenRequest,
    TokenPair,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.services.auth import (
    authenticate_user,
    get_current_user,
    registration_status,
    refresh_tokens,
    register_user,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/registration-status")
def get_registration_status(db: Session = Depends(get_db)) -> dict[str, bool]:
    return registration_status(db)


@router.post("/register", response_model=TokenPair)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> TokenPair:
    return register_user(db, payload)


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenPair:
    return authenticate_user(db, payload)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenPair:
    return refresh_tokens(db, payload.refresh_token)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user
