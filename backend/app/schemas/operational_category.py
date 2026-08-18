import unicodedata
from typing import Literal


OperationalCategory = Literal[
    "calibration",
    "maintenance",
    "repair",
    "verification",
    "qualification",
    "validation",
    "training",
    "consulting",
    "general_service",
    "sale",
    "other",
]

OPERATIONAL_CATEGORY_VALUES = (
    "calibration",
    "maintenance",
    "repair",
    "verification",
    "qualification",
    "validation",
    "training",
    "consulting",
    "general_service",
    "sale",
    "other",
)

_CATEGORY_KEYS = {
    "calibracion": "calibration",
    "mantenimiento": "maintenance",
    "reparacion": "repair",
    "verificacion": "verification",
    "calificacion": "qualification",
    "validacion": "validation",
    "capacitacion": "training",
    "consultoria": "consulting",
    "servicio general": "general_service",
    "venta": "sale",
    "patrones": "sale",
    "equipos": "sale",
    "accesorios": "sale",
    "consumibles": "sale",
    "otro": "other",
    "otra": "other",
}

_COMMODITY_KEYS = {
    value: value
    for value in OPERATIONAL_CATEGORY_VALUES
}


def _key(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        normalized.encode("ascii", "ignore").decode().lower().replace("_", " ").split()
    )


def operational_category_from_structured_fields(
    *,
    category: str | None,
    commodity: str | None,
) -> str | None:
    """Resolve legacy structured fields exactly; never inspect names/descriptions."""
    category_value = _CATEGORY_KEYS.get(_key(category))
    if category_value is not None:
        return category_value
    return _COMMODITY_KEYS.get(_key(commodity).replace(" ", "_"))
