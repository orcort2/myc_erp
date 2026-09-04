import unittest

from app.schemas.field_sheet import FieldSheetSignatureUpdate
from app.services.field_sheet_template_engine import (
    AMBIGUOUS_LEGACY_FAMILIES,
    LEGACY_FAMILY_ALIASES,
    OFFICIAL_MYC_TEMPLATE_KEYS,
    OFFICIAL_PILOT_TEMPLATES,
    OFFICIAL_TABLE_FAMILIES,
    get_official_pilot_template,
    resolve_table_family,
)
from app.services.field_sheet_templates import (
    build_default_result_rows,
    build_fallback_template_definition,
)


class FieldSheetTemplateEngineTests(unittest.TestCase):
    def test_exposes_exactly_the_eight_approved_families(self):
        self.assertEqual(
            set(OFFICIAL_TABLE_FAMILIES),
            {
                "replicated_comparison",
                "direction_cycle",
                "before_after",
                "mass_balance_composite",
                "paired_multichannel",
                "threshold_event",
                "verification_compliance",
                "cup_specialized",
            },
        )

    def test_pilot_geometry_matches_the_approved_reference(self):
        expected = {
            "anemometro": [("measurements", 10, 4)],
            "calibradores": [("exterior", 7, 4), ("interior", 5, 4), ("depth", 3, 4)],
            "temperatura": [("temperature_measurements", 10, 4)],
            "presion": [("pressure_cycle", 11, 4)],
            "bascula": [("eccentricity", 6, 5), ("repeatability_50", 5, 1), ("repeatability_100", 5, 1)],
        }
        for key, geometry in expected.items():
            definition = build_fallback_template_definition(key)
            self.assertEqual(
                [(section["key"], section["rows"], len(section["columns"])) for section in definition["result_sections"]],
                geometry,
            )
            self.assertEqual(definition["pdf_template"], "field_sheet_engine_pdf.html")
            self.assertEqual(definition["automation"], {"mode": "manual_only", "calculations": []})

    def test_phase_6a1_templates_preserve_the_inspected_fca30_contract(self):
        expected = {
            "temperatura": {
                "version": 2,
                "revision": "R-1",
                "family": "replicated_comparison",
                "magnitude": ("temperatura", "Temperatura"),
                "supported_equipment": [],
                "search_aliases": ["temperatura", "Temperatura"],
                "source_document": "FCA-30 R1 HOJA DE CAMPO TEMPERATURA.pdf",
                "section": "temperature_measurements",
                "rows": 10,
                "columns": ["ibc_value", "pattern_1", "pattern_2", "pattern_3"],
                "first_header": [("DATOS DE MEDICION", 5, 1)],
                "last_header": ["1", "2", "3"],
            },
            "presion": {
                "version": 3,
                "revision": "R1",
                "family": "direction_cycle",
                "magnitude": ("presion", "Presión"),
                "supported_equipment": ["manómetro", "vacuómetro", "diferencial de presión"],
                "search_aliases": ["presion", "Presión", "manómetro", "vacuómetro", "diferencial de presión"],
                "source_document": "FCA-30 R1 HOJA DE CAMPO PRESIÓN (manometro, vacuometro, diferencial de presion).pdf",
                "section": "pressure_cycle",
                "rows": 11,
                "columns": ["ibc_value_1", "pattern_value", "ibc_value_2", "ibc_value_3"],
                "first_header": [("DATOS DE MEDICION", 5, 1)],
                "last_header": ["Acendente", "Descendente", "Ascendente"],
            },
        }

        for key, contract in expected.items():
            definition = build_fallback_template_definition(key)
            metadata = definition["metadata"]
            section = definition["result_sections"][0]
            self.assertEqual(definition["version"], contract["version"])
            self.assertEqual(definition["document_code"], "FCA-30")
            self.assertEqual(definition["document_revision"], contract["revision"])
            self.assertEqual(definition["table_family"], contract["family"])
            self.assertEqual(
                (metadata["magnitude_key"], metadata["magnitude_label"]),
                contract["magnitude"],
            )
            self.assertIsNone(metadata["document_variant_key"])
            self.assertIsNone(metadata["document_variant_label"])
            self.assertEqual(metadata["supported_equipment"], contract["supported_equipment"])
            self.assertEqual(metadata["search_aliases"], contract["search_aliases"])
            self.assertEqual(metadata["source_document"], contract["source_document"])
            self.assertEqual(section["key"], contract["section"])
            self.assertEqual(section["rows"], contract["rows"])
            self.assertEqual([column["key"] for column in section["columns"]], contract["columns"])
            self.assertEqual(
                [
                    (cell["label"], cell["colspan"], cell["rowspan"])
                    for cell in section["header_rows"][0]["cells"]
                ],
                contract["first_header"],
            )
            self.assertEqual(
                [cell["label"] for cell in section["header_rows"][-1]["cells"]],
                contract["last_header"],
            )
            self.assertEqual(definition["signature_layout"]["columns"], 1)
            self.assertEqual(definition["signature_layout"]["direction"], "vertical")
            self.assertEqual(
                definition["signature_layout"]["trailing_fields"],
                ["purchase_order_or_quotation"],
            )
            self.assertEqual(definition["print_layout"]["page"]["size"], "letter")
            self.assertEqual(definition["print_layout"]["document"]["grid_columns"], 4)
            table_block = next(
                block for block in definition["blocks"] if block["sections"]
            )
            signatures_block = next(
                block
                for block in definition["blocks"]
                if block["block_type"] == "SignaturesBlock"
            )
            self.assertEqual(table_block["print_layout"]["column_span"], 3)
            self.assertEqual(signatures_block["print_layout"]["column_span"], 1)

    def test_default_rows_remain_compatible_with_results_rows(self):
        for key in OFFICIAL_PILOT_TEMPLATES:
            definition = build_fallback_template_definition(key)
            rows = build_default_result_rows(definition)
            expected_count = sum(section["rows"] for section in definition["result_sections"])
            self.assertEqual(len(rows), expected_count)
            self.assertTrue(all(row.row_data == {} for row in rows))

    def test_new_scale_snapshot_has_no_position_column(self):
        template = build_fallback_template_definition("bascula")
        eccentricity = next(section for section in template["result_sections"] if section["key"] == "eccentricity")
        self.assertEqual(template["version"], 4)
        self.assertNotIn("position", [column["key"] for column in eccentricity["columns"]])

    def test_catalog_contains_exactly_the_23_official_myc_keys(self):
        self.assertEqual(set(OFFICIAL_PILOT_TEMPLATES), set(OFFICIAL_MYC_TEMPLATE_KEYS))
        self.assertEqual(len(OFFICIAL_MYC_TEMPLATE_KEYS), 23)

    def test_all_official_templates_are_vector_v2_and_normalized(self):
        for key in OFFICIAL_MYC_TEMPLATE_KEYS:
            definition = build_fallback_template_definition(key)
            self.assertEqual(definition["metadata"]["organization_key"], "myc")
            self.assertEqual(definition["pdf_renderer_key"], "field_sheet_vector")
            self.assertEqual(definition["pdf_renderer_version"], 2)
            self.assertIn(definition["table_family"], OFFICIAL_TABLE_FAMILIES)
            self.assertTrue(definition["metadata"]["source_document"])
            self.assertTrue(definition["result_sections"])

    def test_template_accessor_returns_a_deep_copy(self):
        first = get_official_pilot_template("presion")
        first["blocks"][0]["title"] = "changed"
        second = get_official_pilot_template("presion")
        self.assertNotEqual(second["blocks"][0]["title"], "changed")

    def test_engine_is_the_single_canonical_authority_of_table_families(self):
        """Fase 3 (2026-09, test obligatorio 1): field_sheet_templates.py ya
        no mantiene un segundo catalogo de familias -- TABLE_FAMILY_DEFINITIONS
        (el segundo diccionario paralelo) fue eliminado por completo, y el
        unico resolver (resolve_table_family) vive en este motor."""
        import app.services.field_sheet_templates as templates_module

        self.assertFalse(hasattr(templates_module, "TABLE_FAMILY_DEFINITIONS"))
        self.assertFalse(hasattr(templates_module, "TEMPLATE_TABLE_FAMILY"))
        self.assertIs(templates_module.resolve_table_family, resolve_table_family)
        self.assertIs(templates_module.OFFICIAL_TABLE_FAMILIES, OFFICIAL_TABLE_FAMILIES)
        self.assertNotIn("temperatura", templates_module.LEGACY_TEMPLATE_FAMILY)

    def test_legacy_family_aliases_are_exactly_the_three_semantically_safe_ones(self):
        self.assertEqual(
            LEGACY_FAMILY_ALIASES,
            {
                "direct_comparison": "replicated_comparison",
                "pressure": "direction_cycle",
                "mass": "mass_balance_composite",
            },
        )
        self.assertTrue(AMBIGUOUS_LEGACY_FAMILIES.isdisjoint(OFFICIAL_TABLE_FAMILIES))
        self.assertTrue(AMBIGUOUS_LEGACY_FAMILIES.isdisjoint(LEGACY_FAMILY_ALIASES))

    def test_signature_contract_accepts_erp_user_and_signature_data(self):
        signature = FieldSheetSignatureUpdate(
            role="calibrated_by",
            display_label="Calibró",
            name="Técnico MYC",
            signature_data="data:image/png;base64,AA==",
            signed_at="2026-07-13T12:00:00Z",
            user_id=7,
            position=0,
        )
        self.assertEqual(signature.user_id, 7)
        self.assertEqual(signature.role, "calibrated_by")


if __name__ == "__main__":
    unittest.main()
