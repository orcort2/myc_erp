from __future__ import annotations

from math import sqrt


def _ensure_non_empty(values: list[float], label: str = "values") -> list[float]:
    if not values:
        raise ValueError(f"{label} no puede estar vacio")
    try:
        return [float(value) for value in values]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} contiene valores invalidos") from exc


def average(values: list[float]) -> float:
    normalized = _ensure_non_empty(values)
    return sum(normalized) / len(normalized)


def standard_deviation(values: list[float]) -> float:
    normalized = _ensure_non_empty(values)
    if len(normalized) == 1:
        return 0.0
    mean = average(normalized)
    variance = sum((value - mean) ** 2 for value in normalized) / (len(normalized) - 1)
    return sqrt(variance)


def repeatability_uncertainty(values: list[float]) -> float:
    normalized = _ensure_non_empty(values)
    if len(normalized) == 1:
        return 0.0
    return standard_deviation(normalized) / sqrt(len(normalized))


def resolution_uncertainty(resolution: float) -> float:
    try:
        normalized = float(resolution)
    except (TypeError, ValueError) as exc:
        raise ValueError("resolution es invalido") from exc
    if normalized <= 0:
        raise ValueError("resolution debe ser mayor a cero")
    return normalized / sqrt(12)


def combined_uncertainty(components: list[float]) -> float:
    normalized = _ensure_non_empty(components, "components")
    if any(value < 0 for value in normalized):
        raise ValueError("components no puede contener valores negativos")
    return sqrt(sum(value**2 for value in normalized))


def expanded_uncertainty(combined: float, k: float) -> float:
    try:
        combined_value = float(combined)
        k_value = float(k)
    except (TypeError, ValueError) as exc:
        raise ValueError("combined o k son invalidos") from exc
    if combined_value < 0:
        raise ValueError("combined no puede ser negativo")
    if k_value <= 0:
        raise ValueError("k debe ser mayor a cero")
    return combined_value * k_value


def absolute_error(indication: float, reference: float) -> float:
    try:
        return float(indication) - float(reference)
    except (TypeError, ValueError) as exc:
        raise ValueError("indication o reference son invalidos") from exc


def relative_error(error: float, reference: float) -> float:
    try:
        error_value = float(error)
        reference_value = float(reference)
    except (TypeError, ValueError) as exc:
        raise ValueError("error o reference son invalidos") from exc
    if reference_value == 0:
        raise ValueError("reference no puede ser cero para error relativo")
    return error_value / reference_value


def select_uncertainty_for_value(uncertainty_ranges: list[dict], value: float) -> dict:
    try:
        target = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("value es invalido") from exc
    if not uncertainty_ranges:
        raise ValueError("uncertainty_ranges no puede estar vacio")

    sorted_ranges = sorted(
        uncertainty_ranges,
        key=lambda item: (
            float(item.get("range_min")) if item.get("range_min") is not None else float("-inf"),
            float(item.get("range_max")) if item.get("range_max") is not None else float("inf"),
        ),
    )
    for item in sorted_ranges:
        range_min = float(item.get("range_min")) if item.get("range_min") is not None else None
        range_max = float(item.get("range_max")) if item.get("range_max") is not None else None
        if range_min is not None and target < range_min:
            continue
        if range_max is not None and target > range_max:
            continue
        return item
    raise ValueError("No existe una incertidumbre aplicable para el valor indicado")
