from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from app.models.service_order import ServiceOrderItem


CALIBRATION_SCOPE_TO_CERTIFICATE_TYPE = {
    "traceable": "trazable",
    "Certificado / Certificate: L25-313": "acreditado",
    "accredited_linked_lab": "vinculado",
}

CERTIFICATE_TYPE_TO_CALIBRATION_SCOPE = {
    value: key for key, value in CALIBRATION_SCOPE_TO_CERTIFICATE_TYPE.items()
}

CALIBRATION_SCOPE_LABELS = {
    "traceable": "trazables",
    "Certificado / Certificate: L25-313": "acreditados",
    "accredited_linked_lab": "vinculados",
}

SUPPORTED_CALIBRATION_SCOPES = tuple(CALIBRATION_SCOPE_TO_CERTIFICATE_TYPE.keys())


@dataclass(frozen=True)
class ScopeCapacity:
    scope: str
    quoted: int
    used: int

    @property
    def available(self) -> int:
        return max(self.quoted - self.used, 0)


def certificate_type_from_scope(calibration_scope: str | None) -> str | None:
    if calibration_scope is None:
        return None
    return CALIBRATION_SCOPE_TO_CERTIFICATE_TYPE.get(calibration_scope)


def calibration_scope_from_certificate_type(certificate_type: str | None) -> str | None:
    if certificate_type is None:
        return None
    return CERTIFICATE_TYPE_TO_CALIBRATION_SCOPE.get(certificate_type)


def get_service_order_certificate_capacity(
    db: Session,
    service_order_id: int,
) -> dict[str, ScopeCapacity]:
    quoted_rows = db.execute(
        select(
            ServiceOrderItem.calibration_scope,
            func.coalesce(func.sum(ServiceOrderItem.quantity), 0),
        )
        .where(
            ServiceOrderItem.service_order_id == service_order_id,
            ServiceOrderItem.is_active.is_(True),
            ServiceOrderItem.calibration_scope.in_(SUPPORTED_CALIBRATION_SCOPES),
        )
        .group_by(ServiceOrderItem.calibration_scope)
    ).all()
    quoted_by_scope = {scope: int(total or 0) for scope, total in quoted_rows if scope}

    used_rows = db.execute(
        select(
            Certificate.certificate_type,
            func.count(Certificate.id),
        )
        .where(
            Certificate.service_order_id == service_order_id,
            Certificate.is_active.is_(True),
            Certificate.certificate_type.in_(tuple(CERTIFICATE_TYPE_TO_CALIBRATION_SCOPE.keys())),
        )
        .group_by(Certificate.certificate_type)
    ).all()
    used_by_scope: dict[str, int] = {}
    for certificate_type, total in used_rows:
        scope = calibration_scope_from_certificate_type(certificate_type)
        if scope:
            used_by_scope[scope] = int(total or 0)

    capacity: dict[str, ScopeCapacity] = {}
    for scope in SUPPORTED_CALIBRATION_SCOPES:
        quoted = quoted_by_scope.get(scope, 0)
        used = used_by_scope.get(scope, 0)
        capacity[scope] = ScopeCapacity(scope=scope, quoted=quoted, used=used)
    return capacity


def resolve_equipment_calibration_scope(
    db: Session,
    service_order_id: int,
    requested_scope: str | None,
) -> str:
    capacity = get_service_order_certificate_capacity(db, service_order_id)
    available_scopes = [scope for scope, item in capacity.items() if item.available > 0]

    if requested_scope:
        if requested_scope not in SUPPORTED_CALIBRATION_SCOPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de certificado no soportado para esta Orden de Trabajo",
            )
        if capacity[requested_scope].available <= 0:
            label = CALIBRATION_SCOPE_LABELS.get(requested_scope, requested_scope)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"No hay cupos disponibles para certificados {label} en esta Orden de Trabajo. "
                    "Actualiza la cotización o solicita autorización administrativa."
                ),
            )
        return requested_scope

    if len(available_scopes) == 1:
        return available_scopes[0]

    if not available_scopes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No hay cupos disponibles para certificados trazables, acreditados o vinculados "
                "en esta Orden de Trabajo. Actualiza la cotización o solicita autorización administrativa."
            ),
        )

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
            "Esta Orden de Trabajo tiene cupos disponibles en más de un tipo de certificado. "
            "Indica si el equipo requiere certificado trazable, acreditado ISO/IEC 17025 o vinculado."
        ),
    )


def auto_service_order_item_id_for_scope(
    db: Session,
    service_order_id: int,
    calibration_scope: str | None,
) -> int | None:
    if calibration_scope is None:
        return None
    item_ids = list(
        db.scalars(
            select(ServiceOrderItem.id)
            .where(
                ServiceOrderItem.service_order_id == service_order_id,
                ServiceOrderItem.is_active.is_(True),
                ServiceOrderItem.calibration_scope == calibration_scope,
            )
            .order_by(ServiceOrderItem.id.asc())
        ).all()
    )
    return item_ids[0] if item_ids else None
