from unittest.mock import Mock

from app.realtime.invalidation import (
    INVALIDATION_CHANNEL,
    parse_invalidation_payload,
)
from app.realtime.postgres_bus import notify_resources


def test_notify_resources_uses_current_transaction_without_commit():
    db = Mock()

    notify_resources(
        db,
        ["users", "quotations"],
        user_ids=[1, 3],
    )

    db.execute.assert_called_once()
    db.commit.assert_not_called()

    statement, parameters = db.execute.call_args.args

    assert "pg_notify" in str(statement)
    assert parameters["channel"] == INVALIDATION_CHANNEL

    event = parse_invalidation_payload(parameters["payload"])

    assert event.resources == ("quotations", "users")
    assert event.user_ids == (1, 3)


def test_invalid_notification_does_not_execute_sql():
    db = Mock()

    try:
        notify_resources(db, ["*"], user_ids=[1])
    except ValueError:
        pass
    else:
        raise AssertionError("La invalidación debía rechazarse")

    db.execute.assert_not_called()
