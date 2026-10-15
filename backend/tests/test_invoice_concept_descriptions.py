from types import SimpleNamespace

from app.models.invoice import Invoice
from app.services.invoices import _sync_invoice_items_from_quotation


def quotation_item(item_id, service_name, description):
    return SimpleNamespace(
        id=item_id,
        service_name=service_name,
        description=description,
        quantity=1,
        unit="Servicio",
        sat_unit="E48",
        sat_key="81141504",
        unit_price=100,
        discount_total=0,
        tax_rate=16,
        quotation_legend=None,
        is_active=True,
    )


def test_new_invoice_uses_service_names_instead_of_delivery_terms():
    invoice = Invoice()
    invoice.items = []
    invoice.payments = []
    invoice.credit_notes = []

    quotation = SimpleNamespace(
        items=[
            quotation_item(
                101,
                "Calibración de manómetro",
                "Tiempo de entrega de 3 a 5 dias habiles",
            ),
            quotation_item(
                102,
                "Calibración de termómetro",
                "Tiempo de entrega de 3 a 5 dias habiles",
            ),
        ]
    )

    _sync_invoice_items_from_quotation(invoice, quotation)

    assert [item.description for item in invoice.items] == [
        "Calibración de manómetro",
        "Calibración de termómetro",
    ]


def test_resync_preserves_custom_fiscal_description():
    invoice = Invoice()
    invoice.items = []
    invoice.payments = []
    invoice.credit_notes = []

    quotation = SimpleNamespace(
        items=[quotation_item(101, "Calibración de manómetro", "Entrega 5 días")]
    )

    _sync_invoice_items_from_quotation(invoice, quotation)
    invoice.items[0].description = "Calibración de manómetro digital"

    _sync_invoice_items_from_quotation(invoice, quotation)

    assert invoice.items[0].description == "Calibración de manómetro digital"


def test_resync_adds_new_item_without_overwriting_existing_description():
    invoice = Invoice()
    invoice.items = []
    invoice.payments = []
    invoice.credit_notes = []

    quotation = SimpleNamespace(
        items=[quotation_item(101, "Calibración de báscula", "Entrega 5 días")]
    )

    _sync_invoice_items_from_quotation(invoice, quotation)
    invoice.items[0].description = "Calibración de báscula analítica"

    quotation.items.append(
        quotation_item(102, "Calibración de termómetro", "Entrega 5 días")
    )

    _sync_invoice_items_from_quotation(invoice, quotation)

    assert [item.description for item in invoice.items] == [
        "Calibración de báscula analítica",
        "Calibración de termómetro",
    ]


def test_resync_preserves_fiscal_fields_and_item_identity():
    invoice = Invoice()
    invoice.items = []
    invoice.payments = []
    invoice.credit_notes = []

    quotation = SimpleNamespace(
        items=[
            quotation_item(
                101,
                "Calibración de manómetro",
                "Tiempo de entrega de 3 a 5 días hábiles",
            )
        ]
    )

    _sync_invoice_items_from_quotation(invoice, quotation)

    original = invoice.items[0]
    original.description = "Calibración acreditada de manómetro"
    original.sat_key = "81141504"
    original.sat_unit = "E48"
    original.tax_rate = 8
    original.discount_total = 10
    original.certificate_id = 501
    original.equipment_id = 601

    quotation.items[0].quantity = 2
    quotation.items[0].unit_price = 150

    _sync_invoice_items_from_quotation(invoice, quotation)

    updated = invoice.items[0]

    assert updated is original
    assert updated.description == "Calibración acreditada de manómetro"
    assert updated.sat_key == "81141504"
    assert updated.sat_unit == "E48"
    assert updated.tax_rate == 8
    assert updated.discount_total == 10
    assert updated.certificate_id == 501
    assert updated.equipment_id == 601
    assert updated.quantity == 2
    assert updated.unit_price == 150
