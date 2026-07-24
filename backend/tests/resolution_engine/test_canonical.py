from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.resolution_engine.domain.canonical import (
    canonical_json,
    canonical_sha256,
)
from app.resolution_engine.domain.exceptions import CanonicalizationError


@dataclass(frozen=True)
class Snapshot:
    amount: Decimal
    captured_at: datetime


def test_canonical_json_is_independent_of_mapping_and_set_order():
    left = {
        "tags": {"beta", "alpha"},
        "nested": {"z": 2, "a": 1},
    }
    right = {
        "nested": {"a": 1, "z": 2},
        "tags": {"alpha", "beta"},
    }

    assert canonical_json(left) == canonical_json(right)
    assert canonical_sha256(left) == canonical_sha256(right)


def test_canonical_hash_normalizes_decimal_and_datetime_representation():
    mexico_offset = timezone(timedelta(hours=-6))
    left = Snapshot(
        amount=Decimal("10.5000"),
        captured_at=datetime(2026, 7, 24, 8, 30, tzinfo=mexico_offset),
    )
    right = Snapshot(
        amount=Decimal("10.5"),
        captured_at=datetime(2026, 7, 24, 14, 30, tzinfo=timezone.utc),
    )

    assert canonical_sha256(left) == canonical_sha256(right)


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 7, 24, 12, 0),
        float("nan"),
        float("inf"),
        {1: "non-string key"},
        object(),
    ],
)
def test_canonical_json_rejects_ambiguous_or_unsupported_values(value):
    with pytest.raises(CanonicalizationError):
        canonical_json(value)


def test_canonical_sha256_has_stable_lowercase_hex_format():
    digest = canonical_sha256({"resolution_type": "service_order.add_equipment"})

    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(character in "0123456789abcdef" for character in digest)
