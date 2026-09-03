import unittest

from app.schemas.field_sheet import FieldSheetSignatureUpdate
from app.services.field_sheet_template_engine import (
    AMBIGUOUS_LEGACY_FAMILIES,
    LEGACY_FAMILY_ALIASES,
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
            "presion": [("pressure_cycle", 11, 4)],
            "bascula": [("eccentricity_cycle", 6, 4), ("repeatability_50", 5, 2), ("repeatability_100", 5, 2)],
        }
        for key, geometry in expected.items():
            definition = build_fallback_template_definition(key)
            self.assertEqual(
                [(section["key"], section["rows"], len(section["columns"])) for section in definition["result_sections"]],
                geometry,
            )
            self.assertEqual(definition["pdf_template"], "field_sheet_engine_pdf.html")
            self.assertEqual(definition["automation"], {"mode": "manual_only", "calculations": []})

    def test_default_rows_remain_compatible_with_results_rows(self):
        for key in OFFICIAL_PILOT_TEMPLATES:
            definition = build_fallback_template_definition(key)
            rows = build_default_result_rows(definition)
            expected_count = sum(section["rows"] for section in definition["result_sections"])
            self.assertEqual(len(rows), expected_count)
            self.assertTrue(all(row.row_data == {} for row in rows))

    def test_new_scale_snapshot_has_no_position_column(self):
        template = build_fallback_template_definition("bascula")
        eccentricity = next(section for section in template["result_sections"] if section["key"] == "eccentricity_cycle")
        self.assertEqual(template["version"], 3)
        self.assertNotIn("position", [column["key"] for column in eccentricity["columns"]])

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
