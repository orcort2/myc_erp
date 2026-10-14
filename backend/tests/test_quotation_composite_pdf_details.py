from types import SimpleNamespace

from app.services.quotation_pdfs import _line_from_item


def make_item(components, commercial_components=None, description=None):
    return SimpleNamespace(
        quantity=1,
        unit_price=1000,
        discount_percent=0,
        total=1000,
        tax_total=160,
        operational_snapshot={
            "service_kind": "composite",
            "operational_items": components,
            "commercial_components": commercial_components or [],
        },
        service_name="Servicio compuesto",
        description=description,
        quotation_legend=None,
        unit="service",
        internal_unit=None,
        sat_unit="E48",
        sat_key="81141504",
    )


def component(item_id, name, category, scope=None,
              service_type=None, maintenance_type=None,
              description=None):
    return {
        "catalog_item_id": item_id,
        "service_name": name,
        "service_snapshot": {
            "service_name_snapshot": name,
            "service_description_snapshot": description,
            "operational_category": category,
            "calibration_scope_snapshot": scope,
            "service_type_snapshot": service_type,
            "maintenance_configuration_snapshot": {
                "maintenance_type": maintenance_type,
            },
            "accreditation_snapshot": (
                {"scope": scope}
                if service_type == "accredited"
                else None
            ),
        },
    }


def test_preventive_maintenance_component():
    item = make_item([
        component(
            95, "Mantenimiento para agitador",
            "maintenance",
            maintenance_type="preventive",
        )
    ])

    result = _line_from_item(item).components[0]

    assert result["legend"] == "Mantenimiento preventivo"


def test_accredited_calibration_component():
    item = make_item([
        component(
            63, "Calibración de cronómetro",
            "calibration",
            scope="accredited_iso_17025",
            service_type="accredited",
        )
    ])

    result = _line_from_item(item).components[0]

    assert result["legend"] == (
        "Servicio acreditado ISO/IEC 17025:2017"
    )


def test_catalog_description_is_used_when_no_override():
    item = make_item([
        component(
            95, "Mantenimiento",
            "maintenance",
            description="Servicio preventivo especializado",
        )
    ])

    result = _line_from_item(item).components[0]

    assert result["description"] == (
        "Servicio preventivo especializado"
    )


def test_commercial_description_overrides_catalog_description():
    item = make_item(
        [
            component(
                95, "Mantenimiento",
                "maintenance",
                description="Descripción del catálogo",
            )
        ],
        commercial_components=[
            {
                "catalog_item_id": 95,
                "description": "Descripción específica de cotización",
            }
        ],
    )

    result = _line_from_item(item).components[0]

    assert result["description"] == (
        "Descripción específica de cotización"
    )


def test_legend_not_duplicated_in_description():
    item = make_item([
        component(
            95, "Mantenimiento",
            "maintenance",
            maintenance_type="preventive",
            description="Mantenimiento preventivo",
        )
    ])

    result = _line_from_item(item).components[0]

    assert result["description"] == "Mantenimiento preventivo"
    assert result["legend"] == ""
