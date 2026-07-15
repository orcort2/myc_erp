from app.services.sat_catalogs.normalizers import normalize_row
from app.services.sat_catalogs.normalizers import normalize_search


class SatCatalogValidationError(ValueError):
    pass


CODE_ALIASES = ("code", "clave", "clave_sat", "c_clave", "id")
NAME_ALIASES = ("name", "nombre", "descripcion", "description", "texto")
VALID_FROM_ALIASES = ("valid_from", "fecha_inicio_vigencia", "vigencia_desde", "fecha_inicial_de_vigencia")
VALID_UNTIL_ALIASES = ("valid_until", "fecha_fin_vigencia", "vigencia_hasta", "fecha_final_de_vigencia")


def _first(row: dict[str, str | None], aliases: tuple[str, ...]) -> str | None:
    return next((row.get(alias) for alias in aliases if row.get(alias)), None)


def validate_rows(rows: list[dict[str, object]]) -> list[dict[str, str | None]]:
    if not rows:
        raise SatCatalogValidationError("El archivo no contiene registros.")
    normalized = [normalize_row(row) for row in rows]
    if not any(alias in normalized[0] for alias in CODE_ALIASES):
        raise SatCatalogValidationError("Falta la columna requerida de clave/código (code, clave o clave_sat).")
    seen: set[str] = set()
    errors: list[str] = []
    for index, row in enumerate(normalized, start=2):
        code = _first(row, CODE_ALIASES)
        if not code:
            errors.append(f"Fila {index}: clave vacía")
        elif code in seen:
            errors.append(f"Fila {index}: clave duplicada {code}")
        else:
            seen.add(code)
    if errors:
        raise SatCatalogValidationError("; ".join(errors[:20]))
    return normalized


def canonical_record(row: dict[str, str | None]) -> dict[str, object]:
    data = {key: value for key, value in row.items() if value is not None}
    code = _first(row, CODE_ALIASES)
    name = _first(row, NAME_ALIASES)
    return {
        "code": code,
        "name": name,
        "normalized_code": normalize_search(code),
        "normalized_name": normalize_search(name),
        "search_text": normalize_search(" ".join(str(value) for value in data.values())),
        "valid_from": _first(row, VALID_FROM_ALIASES),
        "valid_until": _first(row, VALID_UNTIL_ALIASES),
        "data": data,
    }
