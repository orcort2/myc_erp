from decimal import Decimal

import pytest

from app.services.quotation_signing_snapshot import (
    canonical_snapshot_bytes,
    snapshot_digest,
)


def test_key_order_does_not_change_fingerprint():
    a = {"folio": "MYC-10-26-0001", "total": "11890.00"}
    b = {"total": "11890.00", "folio": "MYC-10-26-0001"}
    assert snapshot_digest(a) == snapshot_digest(b)


def test_commercial_change_changes_fingerprint():
    a = {"quantity": 1, "total": "11890.00"}
    b = {"quantity": 2, "total": "23780.00"}
    assert snapshot_digest(a) != snapshot_digest(b)


def test_nested_data_is_fingerprinted():
    a = {"items": [{"name": "Calibración", "quantity": 1}]}
    b = {"items": [{"name": "Calibración", "quantity": 2}]}
    assert snapshot_digest(a) != snapshot_digest(b)


def test_decimal_representation():
    result = canonical_snapshot_bytes({"total": Decimal("11890.00")})
    assert b'"11890.00"' in result


def test_nonfinite_values_rejected():
    with pytest.raises(ValueError):
        snapshot_digest({"total": float("nan")})


def test_unsupported_objects_rejected():
    with pytest.raises(ValueError):
        snapshot_digest({"value": object()})
