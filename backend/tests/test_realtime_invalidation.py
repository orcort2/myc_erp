import json

import pytest

from app.realtime.invalidation import (
    INVALIDATION_VERSION,
    build_invalidation_payload,
    parse_invalidation_payload,
)


def test_build_and_parse_invalidation():
    raw = build_invalidation_payload(
        ["users", "quotations", "users"],
        user_ids=[3, 1, 3],
    )

    parsed = parse_invalidation_payload(raw)

    assert parsed.resources == ("quotations", "users")
    assert parsed.user_ids == (1, 3)
    assert parsed.event_id
    assert json.loads(raw)["version"] == INVALIDATION_VERSION


@pytest.mark.parametrize(
    "resources,user_ids",
    [
        ([], [1]),
        (["users"], []),
        (["users"], [0]),
        (["users"], [True]),
        (["users;DROP TABLE users"], [1]),
        (["*"], [1]),
    ],
)
def test_rejects_invalid_invalidation(resources, user_ids):
    with pytest.raises(ValueError):
        build_invalidation_payload(
            resources,
            user_ids=user_ids,
        )


def test_rejects_unsupported_version():
    raw = build_invalidation_payload(["users"], user_ids=[1])
    payload = json.loads(raw)
    payload["version"] = 999

    with pytest.raises(ValueError):
        parse_invalidation_payload(json.dumps(payload))


@pytest.mark.parametrize(
    "mutation",
    [
        {"event_id": "invalid"},
        {"version": True},
        {"resources": ["users", "users"]},
        {"user_ids": [1, 1]},
        {"user_ids": [True]},
        {"resources": ["*"]},
        {"unexpected": "field"},
    ],
)
def test_rejects_malformed_incoming_events(mutation):
    payload = json.loads(
        build_invalidation_payload(["users"], user_ids=[1])
    )
    payload.update(mutation)

    with pytest.raises(ValueError):
        parse_invalidation_payload(json.dumps(payload))


def test_rejects_oversized_incoming_event():
    raw = build_invalidation_payload(["users"], user_ids=[1])
    payload = json.loads(raw)
    payload["event_id"] = payload["event_id"] + ("x" * 8000)

    with pytest.raises(ValueError):
        parse_invalidation_payload(json.dumps(payload))
