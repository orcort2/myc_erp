from __future__ import annotations

import re
from enum import StrEnum


class ServiceType(StrEnum):
    ACCREDITED = "accredited"
    TRACEABLE = "traceable"
    LINKED = "linked"


SERVICE_TYPE_LABELS = {
    ServiceType.ACCREDITED: "Acreditado",
    ServiceType.TRACEABLE: "Trazable",
    ServiceType.LINKED: "Vinculado",
}

SERVICE_TYPE_TO_CALIBRATION_SCOPE = {
    ServiceType.ACCREDITED: "accredited_iso_17025",
    ServiceType.TRACEABLE: "traceable",
    ServiceType.LINKED: "accredited_linked_lab",
}

SERVICE_TYPE_ALIASES = {
    "acreditado": ServiceType.ACCREDITED,
    "accredited": ServiceType.ACCREDITED,
    "accredited_iso_17025": ServiceType.ACCREDITED,
    "trazable": ServiceType.TRACEABLE,
    "traceable": ServiceType.TRACEABLE,
    "vinculado": ServiceType.LINKED,
    "linked": ServiceType.LINKED,
    "linked_lab": ServiceType.LINKED,
    "accredited_linked_lab": ServiceType.LINKED,
}

CERTIFICATE_PREFIX_PATTERN = re.compile(r"^[A-Z0-9]{2,12}$")


def normalize_service_type(
    value: str | ServiceType | None,
    *,
    calibration_scope: str | None = None,
) -> ServiceType | None:
    candidate = str(value or calibration_scope or "").strip().lower()
    if not candidate:
        return None
    return SERVICE_TYPE_ALIASES.get(candidate)


def calibration_scope_for_service_type(value: str | ServiceType) -> str:
    normalized = normalize_service_type(value)
    if normalized is None:
        raise ValueError("Tipo de servicio no reconocido")
    return SERVICE_TYPE_TO_CALIBRATION_SCOPE[normalized]


def normalize_certificate_prefix(value: str | None) -> str | None:
    normalized = (value or "").strip().upper()
    if not normalized:
        return None
    if not CERTIFICATE_PREFIX_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Las iniciales deben contener entre 2 y 12 caracteres alfanuméricos, sin espacios"
        )
    return normalized
