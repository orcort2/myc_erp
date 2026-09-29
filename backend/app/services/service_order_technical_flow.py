"""Technical-execution policy for ETS during the 2026 MYC Mobile phase.

A NEW ETS whose active operational composition is exclusively ``calibration``
is executed technically in LAB/MYC Mobile. The ERP does not reserve an OT
folio for it, does not create ``ServiceWorkOrder`` rows and must not create
productive technical reality (Equipment, FieldSheet, ERP technical signatures
or folio-reserving Certificates). The ERP resumes authority in Capture,
Quality, Certificates and Billing.

There is no persisted execution mode: the structural reality is the authority.

- calibration-only composition (``ServiceOrderItem.operational_category``);
- ``ServiceOrder.work_order_number IS NULL``;
- no ``ServiceWorkOrder`` rows.

Historical ETS always carry a ``work_order_number`` (the column was NOT NULL
until this phase), so they are never reinterpreted. Mixed ETS keep the
productive flow until their other categories get a Mobile execution.
"""

from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException, status


CALIBRATION_CATEGORY = "calibration"
MOBILE_CALIBRATION_FLOW_CODE = "CALIBRATION_TECHNICAL_FLOW_MANAGED_BY_MOBILE"


def is_calibration_only(items: Iterable[Any]) -> bool:
    """At least one active item and every active item is calibration."""
    active = [item for item in items if item.is_active]
    return bool(active) and all(
        item.operational_category == CALIBRATION_CATEGORY for item in active
    )


def is_mobile_calibration_service_order(service_order: Any) -> bool:
    """True for a new calibration-only ETS whose technical flow lives in LAB."""
    return (
        service_order.work_order_number is None
        and not service_order.work_orders
        and is_calibration_only(service_order.items)
    )


def mobile_calibration_conflict(service_order_id: int, action: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": MOBILE_CALIBRATION_FLOW_CODE,
            "message": (
                "La ejecución técnica de este ETS de calibración corresponde a "
                "MYC Mobile. El ERP no crea equipos, hojas de campo, firmas "
                "técnicas, OT ni certificados con folio propio para este ETS."
            ),
            "service_order_id": service_order_id,
            "action": action,
        },
    )


def ensure_productive_technical_flow_allowed(
    db, service_order_id: int, *, action: str
) -> None:
    """Raise 409 when ``action`` would create ERP technical reality for a Mobile ETS."""
    from app.models.service_order import ServiceOrder

    service_order = db.get(ServiceOrder, service_order_id)
    if service_order is not None and is_mobile_calibration_service_order(service_order):
        raise mobile_calibration_conflict(service_order_id, action)
