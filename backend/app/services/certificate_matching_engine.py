from __future__ import annotations

import re
import unicodedata

from app.models.certificate import Certificate


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value)
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", normalized.lower())


def _check(field: str, expected: str | None, haystack: str, weight: int) -> tuple[dict, int]:
    expected_normalized = _normalize(expected)
    if not expected_normalized:
        return {
            "field": field,
            "expected": expected,
            "found": None,
            "status": "pending",
            "weight": weight,
        }, 0
    matched = expected_normalized in haystack
    return {
        "field": field,
        "expected": expected,
        "found": expected if matched else None,
        "status": "matched" if matched else "mismatch",
        "weight": weight,
    }, weight if matched else 0


def validate_certificate_pdf_match(certificate: Certificate, filename: str | None = None) -> dict:
    source_name = filename or certificate.final_pdf_original_filename or ""
    haystack = _normalize(source_name)
    equipment = certificate.equipment
    service_order = certificate.service_order
    folio = certificate.expected_folio or certificate.folio
    checks = []
    score = 0
    max_score = 0

    for field, expected, weight in [
        ("folio", folio, 45),
        ("serial_number", equipment.serial_number if equipment else None, 20),
        ("internal_id", equipment.internal_id if equipment else None, 15),
        ("equipment_name", equipment.name if equipment else None, 10),
        ("work_order_number", str(service_order.work_order_number) if service_order else None, 10),
    ]:
        check, value = _check(field, expected, haystack, weight)
        checks.append(check)
        score += value
        if expected:
            max_score += weight

    normalized_score = round((score / max_score) * 100) if max_score else 0
    warnings = []
    errors = []
    if not source_name:
        status = "pending"
        warnings.append("No hay nombre de archivo para validar.")
    elif normalized_score >= 70:
        status = "matched"
    elif normalized_score >= 35:
        status = "warning"
        warnings.append("Coincidencia parcial; requiere revision.")
    else:
        status = "mismatch"
        errors.append("El archivo no coincide con el folio/equipo esperado.")

    return {
        "status": status,
        "score": normalized_score,
        "filename": source_name,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }
