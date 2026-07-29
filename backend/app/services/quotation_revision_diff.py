from __future__ import annotations

from collections import Counter
from decimal import Decimal


def _money(value) -> str:
    return f"{Decimal(str(value or 0)):.2f}"


def _normalized_item(item: dict) -> dict:
    snapshot = item.get("operational_snapshot") or {}
    service = snapshot.get("commercial_service_snapshot") or {}
    return {
        "service_key": service.get("service_key") or item.get("service_key"),
        "service_name": service.get("service_name_snapshot") or item.get("service_name"),
        "service_type": service.get("service_type_snapshot") or item.get("service_type"),
        "linked_company": service.get("linked_company_name_snapshot"),
        "certificate_prefix": service.get("certificate_prefix_snapshot"),
        "quantity": int(item.get("quantity") or 1),
        "unit_price": _money(item.get("unit_price") or service.get("price_snapshot")),
        "discount_percent": _money(item.get("discount_percent")),
        "description": item.get("description"),
    }


def _fingerprint(item: dict) -> tuple:
    normalized = _normalized_item(item)
    return tuple(normalized[key] for key in normalized)


def compare_quotation_revisions(before: list[dict], after: list[dict]) -> dict:
    before_by_key = {_fingerprint(item): _normalized_item(item) for item in before}
    after_by_key = {_fingerprint(item): _normalized_item(item) for item in after}
    before_counts = Counter(_fingerprint(item) for item in before)
    after_counts = Counter(_fingerprint(item) for item in after)
    removed = [
        before_by_key[key]
        for key, count in (before_counts - after_counts).items()
        for _ in range(count)
    ]
    added = [
        after_by_key[key]
        for key, count in (after_counts - before_counts).items()
        for _ in range(count)
    ]
    return {
        "removed": removed,
        "added": added,
        "has_changes": bool(removed or added),
    }
