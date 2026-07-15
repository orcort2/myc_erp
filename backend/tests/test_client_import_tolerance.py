import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base
from app.models.sat_catalog import SatCatalog
from app.models.client import Client
from app.schemas.client import ClientImportConfirm
from app.services.clients import _resolve_sat_import_value, confirm_client_import
from app.services.sat_catalogs.importer import import_catalog_records


class ClientImportToleranceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        for code, name in (("fiscal_regimes", "Régimen"), ("cfdi_uses", "Uso CFDI"), ("postal_codes", "CP")):
            self.db.add(SatCatalog(code=code, name=name, description=name))
        self.db.commit()
        import_catalog_records(self.db, catalog_code="fiscal_regimes", rows=[{"code": "601", "name": "General de Ley Personas Morales"}], source_filename="test.csv", checksum="regime", version="v1")
        import_catalog_records(self.db, catalog_code="cfdi_uses", rows=[{"code": "G03", "name": "Gastos en general"}], source_filename="test.csv", checksum="use", version="v1")
        import_catalog_records(self.db, catalog_code="postal_codes", rows=[{"code": "01000", "name": "Álvaro Obregón"}], source_filename="test.csv", checksum="postal", version="v1")

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_resolves_regime_code_and_description_variants(self):
        for value in ("601", "General de Ley Personas Morales", "General de Ley de Personas Morales", "general de ley de personas morales"):
            self.assertEqual(_resolve_sat_import_value(self.db, "fiscal_regimes", value), "601")

    def test_unknown_fiscal_data_imports_with_warning_but_missing_name_fails(self):
        result = confirm_client_import(self.db, ClientImportConfirm(rows=[
            {"nombre_comercial": "Cliente tolerante", "regimen_fiscal": "Régimen inventado"},
            {"regimen_fiscal": "601"},
        ]))
        self.assertEqual(result.total_rows, 2)
        self.assertEqual(result.imported_count, 1)
        self.assertEqual(result.imported_with_warnings_count, 1)
        self.assertEqual(result.error_count, 1)
        self.assertTrue(result.warnings)

    def test_archived_rfc_is_restored_and_generic_rfc_is_ambiguous(self):
        archived = Client(
            client_type="persona_moral",
            legal_name="Archivado",
            commercial_name="Archivado",
            rfc="ABC010101ABC",
            is_active=False,
        )
        generic = Client(
            client_type="persona_moral",
            legal_name="Genérico archivado",
            commercial_name="Genérico archivado",
            rfc="XAXX010101000",
            is_active=False,
        )
        self.db.add_all([archived, generic])
        self.db.commit()
        result = confirm_client_import(self.db, ClientImportConfirm(rows=[
            {"nombre_comercial": "Actualizado", "rfc": "ABC010101ABC"},
            {"nombre_comercial": "Otro genérico", "rfc": "XAXX010101000"},
        ]))
        self.assertIn(archived.id, result.imported_ids)
        self.assertTrue(self.db.get(Client, archived.id).is_active)
        self.assertEqual(self.db.query(Client).filter_by(rfc="ABC010101ABC").count(), 1)
        self.assertEqual(self.db.query(Client).filter_by(rfc="XAXX010101000").count(), 1)
