from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from jose import jwt
from pydantic import ValidationError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.schemas.auth import UserRegister
from app.core.config import Settings
from app.core.config import settings
from app.core.security import ALGORITHM
from app.services.auth import get_current_user, refresh_tokens


def test_access_and_refresh_tokens_have_distinct_explicit_types():
    assert decode_token(create_access_token("7"))["token_type"] == "access"
    assert decode_token(create_refresh_token("7"))["token_type"] == "refresh"


def test_access_token_type_is_mandatory():
    token = jwt.encode({"sub": "7"}, settings.secret_key, algorithm=ALGORITHM)
    db = Mock()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db)

    assert exc_info.value.status_code == 401
    db.scalar.assert_not_called()


def test_expired_or_invalidly_signed_tokens_are_rejected():
    expired = jwt.encode(
        {
            "sub": "7",
            "token_type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    wrong_signature = jwt.encode(
        {
            "sub": "7",
            "token_type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "a-different-signing-key-that-is-not-the-configured-secret",
        algorithm=ALGORITHM,
    )

    with pytest.raises(ValueError):
        decode_token(expired)
    with pytest.raises(ValueError):
        decode_token(wrong_signature)


def test_refresh_token_cannot_be_used_as_access_bearer():
    db = Mock()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=create_refresh_token("7"), db=db)

    assert exc_info.value.status_code == 401
    db.scalar.assert_not_called()


def test_access_token_cannot_be_used_as_refresh_token():
    db = Mock()

    with pytest.raises(HTTPException) as exc_info:
        refresh_tokens(db=db, refresh_token=create_access_token("7"))

    assert exc_info.value.status_code == 401
    db.scalar.assert_not_called()


def test_public_registration_rejects_requested_roles():
    with pytest.raises(ValidationError):
        UserRegister(
            email="attacker@example.test",
            full_name="Attacker",
            password="strong-password",
            role_names=["Administrador"],
        )


@pytest.mark.parametrize(
    "secret",
    ["", "change-this-secret-key", "development-only-change-me", "weak-secret"],
)
def test_production_rejects_missing_default_or_weak_jwt_secret(secret):
    with pytest.raises(ValidationError, match="SECRET_KEY inseguro"):
        Settings(_env_file=None, environment="production", secret_key=secret)


def test_production_without_explicit_jwt_secret_is_rejected():
    with pytest.raises(ValidationError, match="SECRET_KEY inseguro"):
        Settings(_env_file=None, environment="production")


def test_production_accepts_high_entropy_jwt_secret():
    configured = Settings(
        _env_file=None,
        environment="production",
        secret_key="V4!mQ9#xL2@pR7$zT5&kN8*eC3%wS6^hJ1+u",
    )

    assert configured.environment == "production"


def test_development_allows_explicit_local_jwt_secret():
    configured = Settings(
        _env_file=None,
        environment="development",
        secret_key="development-only-change-me",
    )

    assert configured.uses_development_secret is True
