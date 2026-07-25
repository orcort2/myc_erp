from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.schemas.auth import UserRegister
from app.services.auth import get_current_user, get_optional_current_user


def test_access_and_refresh_tokens_have_distinct_explicit_types():
    assert decode_token(create_access_token("7"))["token_type"] == "access"
    assert decode_token(create_refresh_token("7"))["token_type"] == "refresh"


def test_refresh_token_cannot_be_used_as_access_bearer():
    db = Mock()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=create_refresh_token("7"), db=db)

    assert exc_info.value.status_code == 401
    db.scalar.assert_not_called()


def test_optional_authentication_ignores_refresh_bearer():
    db = Mock()

    result = get_optional_current_user(
        token=create_refresh_token("7"),
        db=db,
    )

    assert result is None
    db.scalar.assert_not_called()


def test_public_registration_rejects_requested_roles():
    with pytest.raises(ValidationError):
        UserRegister(
            email="attacker@example.test",
            full_name="Attacker",
            password="strong-password",
            role_names=["Administrador"],
        )
