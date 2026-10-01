from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    RefreshTokenRequest,
    TokenPair,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.services.password_reset import (
    REQUEST_MESSAGE,
    RESET_DONE_MESSAGE,
    request_password_reset,
    reset_password,
    send_password_reset_email,
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


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """Always answers the same message: no account enumeration."""
    pending = request_password_reset(db, payload.email)
    if pending is not None:
        background_tasks.add_task(send_password_reset_email, pending)
    return ForgotPasswordResponse(message=REQUEST_MESSAGE)


@router.post("/reset-password", response_model=ResetPasswordResponse)
def reset_password_route(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> ResetPasswordResponse:
    reset_password(db, payload.token, payload.new_password)
    return ResetPasswordResponse(message=RESET_DONE_MESSAGE)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return current_user
