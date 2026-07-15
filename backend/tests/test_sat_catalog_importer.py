import tempfile
import unittest
from pathlib import Path
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.sat_catalog import SatCatalog, SatCatalogRecord
from app.models.user import User
from app.schemas.sat_catalog import SatCatalogRead
from app.services.sat_catalogs.importer import import_catalog_file, import_catalog_records
from app.services.sat_catalogs.service import activate_catalog_version, add_alias, add_favorite, get_catalog, latest_version, list_catalogs, remove_favorite, search_records
from app.services.sat_catalogs.sqlite_source import SatSqliteSourceError, extract_catalog_rows


class SatCatalogImporterTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.session.add(SatCatalog(code="currencies", name="Monedas", description="c_Moneda"))
        self.session.add(SatCatalog(code="products_services", name="Productos", description="c_ClaveProdServ"))
        self.session.add(SatCatalog(code="voucher_types", name="Tipos de comprobante", description="c_TipoDeComprobante"))
        self.session.add(User(email="sat@example.test", full_name="SAT Test", hashed_password="not-used"))
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def test_imports_csv_and_queries_latest_version(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "c_moneda.csv"
            source.write_text("Clave,Descripción,Fecha inicio vigencia\nMXN,Peso mexicano,2022-01-01\nUSD,Dólar americano,2022-01-01\n", encoding="utf-8")
            report = import_catalog_file(self.session, catalog_code="currencies", path=source, version="2026-01-01")
            skipped = import_catalog_file(self.session, catalog_code="currencies", path=source, version="otra-version")

        self.assertEqual(report.status, "imported")
        self.assertEqual(report.record_count, 2)
        self.assertEqual(skipped.status, "skipped")
        version, total, records = search_records(self.session, "currencies", search="peso", active_only=True, offset=0, limit=50)
        self.assertEqual(version.version, "2026-01-01")
        self.assertEqual(total, 1)
        self.assertEqual(records[0].code, "MXN")
        self.assertEqual(self.session.query(SatCatalogRecord).count(), 2)
        catalog = list_catalogs(self.session)[0]
        self.assertEqual(SatCatalogRead.model_validate(catalog).installed_version.version, "2026-01-01")

    def test_rejects_duplicate_codes_without_writing_records(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "duplicado.csv"
            source.write_text("code,name\nMXN,Peso\nMXN,Peso mexicano\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                import_catalog_file(self.session, catalog_code="currencies", path=source, version="2026-01-01")

        self.assertEqual(self.session.query(SatCatalogRecord).count(), 0)

    def test_sqlite_adapter_uses_the_common_importer_and_rejects_incompatible_tables(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "catalogs.db"
            connection = sqlite3.connect(source)
            connection.execute("CREATE TABLE cfdi_40_monedas (id TEXT, texto TEXT, vigencia_desde TEXT, vigencia_hasta TEXT)")
            connection.execute("INSERT INTO cfdi_40_monedas VALUES ('MXN', 'Peso mexicano', '2022-01-01', '')")
            connection.commit()
            connection.close()
            table, rows = extract_catalog_rows(source, "currencies")
            report = import_catalog_records(self.session, catalog_code="currencies", rows=rows, source_filename=f"{source.name}:{table}", checksum="sqlite-test-checksum", version="v1")
            self.assertEqual(report.record_count, 1)
            connection = sqlite3.connect(source)
            connection.execute("CREATE TABLE cfdi_40_productos_servicios (texto TEXT)")
            connection.commit()
            connection.close()
            with self.assertRaises(SatSqliteSourceError):
                extract_catalog_rows(source, "products_services")

    def test_normalized_search_aliases_favorites_and_validity(self):
        report = import_catalog_records(
            self.session,
            catalog_code="products_services",
            rows=[
                {"id": "81141504", "texto": "Calibración de termómetro", "vigencia_desde": "2022-01-01", "vigencia_hasta": ""},
                {"id": "00000000", "texto": "Histórico", "vigencia_desde": "2010-01-01", "vigencia_hasta": "2020-01-01"},
            ],
            source_filename="test.sqlite:cfdi_40_productos_servicios",
            checksum="product-test-checksum",
            version="v1",
        )
        self.assertEqual(report.status, "imported")
        user = self.session.query(User).filter_by(email="sat@example.test").one()
        _, _, records = search_records(self.session, "products_services", search="TERMOMETRO", active_only=True, user_id=user.id)
        self.assertEqual(len(records), 1)
        record = records[0]
        add_alias(self.session, record, alias="temperatura", user_id=user.id)
        with self.assertRaises(ValueError):
            add_alias(self.session, record, alias="Temperatúra", user_id=user.id)
        add_favorite(self.session, record, user_id=user.id)
        _, total, records = search_records(self.session, "products_services", search="temperatura", active_only=True, favorites_only=True, user_id=user.id)
        self.assertEqual(total, 1)
        self.assertTrue(records[0].is_favorite)
        self.assertIn("alias", records[0].matched_on)
        _, total, records = search_records(self.session, "products_services", search=None, active_only=False, user_id=user.id)
        self.assertEqual(total, 2)
        self.assertFalse(next(item for item in records if item.code == "00000000").is_current)
        self.assertTrue(remove_favorite(self.session, record, user_id=user.id))

    def test_staged_version_only_becomes_operational_on_explicit_activation(self):
        with self.session.begin():
            report = import_catalog_records(
                self.session,
                catalog_code="voucher_types",
                rows=[{"code": "I", "name": "Ingreso", "valid_from": "2022-01-01"}],
                source_filename="official.xlsx",
                checksum="official-voucher-checksum",
                version="20260703",
                status="staged",
                commit=False,
            )
            self.assertEqual(report.status, "imported")
            self.assertIsNone(latest_version(self.session, get_catalog(self.session, "voucher_types")))
            activate_catalog_version(self.session, catalog_code="voucher_types", version="20260703")
        version, total, records = search_records(self.session, "voucher_types", search="I", active_only=True)
        self.assertEqual(version.version, "20260703")
        self.assertEqual(total, 1)
        self.assertEqual(records[0].name, "Ingreso")
