"""Unit tests for the quotation signing orchestration service."""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services import quotation_signing as service
from app.services.quotation_signing_otp import code_digest


NOW = datetime.now(timezone.utc)


def settings(**overrides):
    values = {
        "quotation_signing_enabled": True,
        "secret_key": "test-signing-secret-with-sufficient-randomness-12345",
        "quotation_signing_otp_expire_minutes": 10,
        "quotation_signing_otp_max_attempts": 5,
        "quotation_signing_otp_cooldown_seconds": 60,
    }
    values.update(overrides)
    return Settings(**values)


def quotation():
    contact = SimpleNamespace(
        id=3,
        client_id=7,
        email="cliente@example.com",
    )
    return SimpleNamespace(
        id=11,
        folio="MYC-10-26-TEST",
        client_id=7,
        status="sent",
        valid_until=date.today() + timedelta(days=7),
        contact=contact,
    )


def snapshot():
    return SimpleNamespace(
        id=22,
        quotation_id=11,
        snapshot_number=3,
    )


def challenge(
    *,
    code="123456",
    attempts=0,
    expires_at=None,
    verified_at=None,
    revoked_at=None,
    consumed_at=None,
    snapshot_id=22,
):
    nonce = "test-nonce"
    return SimpleNamespace(
        id=33,
        quotation_id=11,
        snapshot_id=snapshot_id,
        signing_link_id=None,
        recipient_email="cliente@example.com",
        code_hash=code_digest(
            code,
            nonce=nonce,
            secret_key=settings().secret_key,
        ),
        nonce=nonce,
        attempts=attempts,
        expires_at=expires_at or NOW + timedelta(minutes=10),
        verified_at=verified_at,
        revoked_at=revoked_at,
        consumed_at=consumed_at,
    )


def test_signing_disabled():
    db = MagicMock()

    with pytest.raises(HTTPException) as error:
        service.request_signing_code(
            db,
            11,
            settings=settings(quotation_signing_enabled=False),
        )

    assert error.value.status_code == 503
    db.commit.assert_not_called()


def test_request_creates_challenge_before_email():
    db = MagicMock()
    db.scalars.return_value.all.return_value = []

    q = quotation()
    snap = snapshot()

    events = []

    def commit():
        events.append("commit")

    def send(*args, **kwargs):
        events.append("send")
        assert events.index("commit") < events.index("send")
        assert kwargs["template_key"] == "quotation_signing_otp"
        assert kwargs["to"] == ["cliente@example.com"]
        assert len(kwargs["context"]["otp_code"]) == 6

        return SimpleNamespace(
            sent=True,
            delivery_id=99,
        )

    db.commit.side_effect = commit

    with (
        patch.object(service, "_quotation", return_value=q),
        patch.object(service, "_snapshot", return_value=snap),
        patch.object(service, "send_email", side_effect=send),
        patch.object(service, "write_audit_log"),
    ):
        def flush():
            created = db.add.call_args.args[0]
            created.id = 33

        db.flush.side_effect = flush

        result = service.request_signing_code(
            db,
            11,
            settings=settings(),
        )

    assert result["challenge_id"] == 33
    assert result["snapshot_id"] == 22
    assert result["expires_in_minutes"] == 10
    assert events == ["commit", "send"]


def test_request_revokes_previous_challenge():
    db = MagicMock()

    previous = challenge()
    previous.created_at = NOW - timedelta(minutes=5)

    db.scalars.return_value.all.return_value = [previous]

    with (
        patch.object(service, "_quotation", return_value=quotation()),
        patch.object(service, "_snapshot", return_value=snapshot()),
        patch.object(
            service,
            "send_email",
            return_value=SimpleNamespace(sent=True, delivery_id=99),
        ),
        patch.object(service, "write_audit_log"),
    ):
        def flush():
            db.add.call_args.args[0].id = 44

        db.flush.side_effect = flush

        service.request_signing_code(
            db,
            11,
            settings=settings(),
        )

    assert previous.revoked_at is not None


def test_request_respects_cooldown():
    db = MagicMock()

    previous = challenge()
    previous.created_at = NOW

    db.scalars.return_value.all.return_value = [previous]

    with (
        patch.object(service, "_quotation", return_value=quotation()),
        patch.object(service, "_snapshot", return_value=snapshot()),
        patch.object(service, "_now", return_value=NOW),
    ):
        with pytest.raises(HTTPException) as error:
            service.request_signing_code(
                db,
                11,
                settings=settings(),
            )

    assert error.value.status_code == 429
    db.commit.assert_not_called()


def test_request_revokes_challenge_when_smtp_fails():
    db = MagicMock()
    db.scalars.return_value.all.return_value = []

    created = None

    def flush():
        nonlocal created
        created = db.add.call_args.args[0]
        created.id = 33

    db.flush.side_effect = flush
    db.scalar.return_value = None

    with (
        patch.object(service, "_quotation", return_value=quotation()),
        patch.object(service, "_snapshot", return_value=snapshot()),
        patch.object(
            service,
            "send_email",
            return_value=SimpleNamespace(sent=False, delivery_id=99),
        ),
        patch.object(service, "_revoke") as revoke,
        patch.object(service, "write_audit_log"),
    ):
        with pytest.raises(HTTPException) as error:
            service.request_signing_code(
                db,
                11,
                settings=settings(),
            )

    assert error.value.status_code == 503
    assert created is not None
    revoke.assert_called_once_with(db, 33)


def verify(db, record, code, snap=None):
    db.scalar.return_value = record

    with (
        patch.object(service, "_quotation", return_value=quotation()),
        patch.object(
            service,
            "_snapshot",
            return_value=snap or snapshot(),
        ),
        patch.object(service, "write_audit_log"),
    ):
        return service.verify_signing_code(
            db,
            11,
            33,
            code,
            settings=settings(),
        )


def test_correct_code_verifies_once():
    db = MagicMock()
    record = challenge()

    assert verify(db, record, "123456") is True
    assert record.verified_at is not None
    assert record.attempts == 1

    with pytest.raises(HTTPException) as error:
        verify(db, record, "123456")

    assert error.value.status_code == 409


def test_incorrect_code_counts_attempt():
    db = MagicMock()
    record = challenge()

    assert verify(db, record, "000000") is False
    assert record.attempts == 1
    assert record.verified_at is None
    db.commit.assert_called_once()


def test_expired_code_is_rejected():
    db = MagicMock()
    record = challenge(
        expires_at=NOW - timedelta(seconds=1),
    )

    with pytest.raises(HTTPException) as error:
        verify(db, record, "123456")

    assert error.value.status_code == 409
    assert record.verified_at is None


def test_maximum_attempts_are_enforced():
    db = MagicMock()
    record = challenge(attempts=5)

    with pytest.raises(HTTPException) as error:
        verify(db, record, "123456")

    assert error.value.status_code == 409
    assert record.verified_at is None


def test_old_snapshot_is_rejected():
    db = MagicMock()
    record = challenge(snapshot_id=21)

    with pytest.raises(HTTPException) as error:
        verify(db, record, "123456")

    assert error.value.status_code == 409
    assert record.verified_at is None


def test_revoked_code_is_rejected():
    db = MagicMock()
    record = challenge(revoked_at=NOW)

    with pytest.raises(HTTPException) as error:
        verify(db, record, "123456")

    assert error.value.status_code == 409


def test_consumed_code_is_rejected():
    db = MagicMock()
    record = challenge(consumed_at=NOW)

    with pytest.raises(HTTPException) as error:
        verify(db, record, "123456")

    assert error.value.status_code == 409

def test_link_bound_code_requires_signing_token():
    db = MagicMock()
    record = challenge()
    record.signing_link_id = 81

    with (
        patch.object(service, "_quotation", return_value=quotation()),
        patch.object(service, "_snapshot", return_value=snapshot()),
    ):
        with pytest.raises(HTTPException) as error:
            service.verify_signing_code(
                db, 11, 33, "123456", settings=settings()
            )

    assert error.value.status_code == 409
    assert record.verified_at is None
    assert record.attempts == 0
    db.commit.assert_not_called()


def test_link_bound_code_rejects_another_link():
    db = MagicMock()
    record = challenge()
    record.signing_link_id = 81
    document = SimpleNamespace(quotation_id=11, snapshot_id=22)
    other_link = SimpleNamespace(id=82, recipient_email="cliente@example.com")

    with (
        patch.object(service, "_quotation", return_value=quotation()),
        patch.object(service, "_snapshot", return_value=snapshot()),
        patch.object(
            service, "authorize_document_link",
            return_value=(document, other_link),
        ),
    ):
        with pytest.raises(HTTPException) as error:
            service.verify_signing_code(
                db, 11, 33, "123456",
                settings=settings(), signing_token="other-valid-token",
            )

    assert error.value.status_code == 409
    assert record.verified_at is None
    assert record.attempts == 0
    db.commit.assert_not_called()
