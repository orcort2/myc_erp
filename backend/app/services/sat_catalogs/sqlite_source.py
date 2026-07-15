"""Read the bundled SAT SQLite release without executing or modifying it."""

import sqlite3
from functools import lru_cache
from hashlib import sha256
from pathlib import Path


SQLITE_TABLE_BY_CATALOG = {
    "products_services": "cfdi_40_productos_servicios",
    "units": "cfdi_40_claves_unidades",
    "fiscal_regimes": "cfdi_40_regimenes_fiscales",
    "cfdi_uses": "cfdi_40_usos_cfdi",
    "payment_forms": "cfdi_40_formas_pago",
    "payment_methods": "cfdi_40_metodos_pago",
    "currencies": "cfdi_40_monedas",
    "countries": "cfdi_40_paises",
    "postal_codes": "cfdi_40_codigos_postales",
    "tax_objects": "cfdi_40_objetos_impuestos",
    "relation_types": "cfdi_40_tipos_relaciones",
    "exports": "cfdi_40_exportaciones",
    "taxes": "cfdi_40_impuestos",
    "factor_types": "cfdi_40_tipos_factores",
}


class SatSqliteSourceError(ValueError):
    pass


@lru_cache(maxsize=4)
def _database_checksum(path: str) -> bytes:
    return sha256(Path(path).read_bytes()).digest()


def source_checksum(path: str | Path, table: str) -> str:
    digest = sha256(_database_checksum(str(Path(path).expanduser().resolve())))
    digest.update(table.encode("utf-8"))
    return digest.hexdigest()


def list_tables(path: str | Path) -> set[str]:
    source = Path(path).expanduser()
    if not source.is_file():
        raise SatSqliteSourceError(f"Fuente SQLite no encontrada: {source}")
    connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    try:
        return {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    finally:
        connection.close()


def extract_catalog_rows(path: str | Path, catalog_code: str) -> tuple[str, list[dict[str, object]]]:
    table = SQLITE_TABLE_BY_CATALOG.get(catalog_code)
    if table is None:
        raise SatSqliteSourceError(f"No hay mapeo SQLite para el catálogo {catalog_code}.")
    source = Path(path).expanduser()
    connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        available = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if table not in available:
            raise SatSqliteSourceError(f"La tabla requerida no existe: {table}")
        columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
        if "id" not in columns:
            raise SatSqliteSourceError(f"La tabla {table} no contiene la columna id requerida.")
        return table, [dict(row) for row in connection.execute(f'SELECT * FROM "{table}"')]
    finally:
        connection.close()
