"""Invalidaciones de recursos originadas por triggers PostgreSQL."""

from __future__ import annotations

import json
from dataclasses import dataclass

RESOURCE_CHANGE_CHANNEL = "myc_erp_resource_changes_v1"

RESOURCE_READ_PERMISSIONS = {
    "users": "users.read",
    "clients": "clients.read",
    "quotations": "quotations.read",
    "service_orders": "service_orders.read",
    "invoices": "invoices.read",
    "lab_work_orders": "lab_work_orders.use",
}


INTERNAL_RESOURCE_EVENTS = frozenset({
    "communication_authority",
    "portal_authority",
})


@dataclass(frozen=True)
class ResourceChange:
    resource: str


def parse_resource_change(raw: str) -> ResourceChange:
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid resource change JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("Invalid resource change payload")

    if set(payload) != {"version", "resource"}:
        raise ValueError("Unexpected resource change fields")

    if type(payload["version"]) is not int or payload["version"] != 1:
        raise ValueError("Unsupported resource change version")

    resource = payload["resource"]

    if not isinstance(resource, str) or (
        resource not in RESOURCE_READ_PERMISSIONS
        and resource not in INTERNAL_RESOURCE_EVENTS
    ):
        raise ValueError("Unknown resource")

    return ResourceChange(resource=resource)
