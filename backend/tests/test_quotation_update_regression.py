"""Regresiones de actualización de cotizaciones y enlaces de firmado."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.quotation import QuotationUpdate
from app.services.quotations import update_quotation


def _quotation():
    return SimpleNamespace(
        id=48,
        status="sent",
        client_id=295,
        contact_id=None,
        valid_until=None,
        payment_terms=None,
        notes=None,
    )


def _db():
    db = MagicMock()
    db.expire = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    return db


@pytest.mark.parametrize(
    "status",
    ["draft", "sent", "waiting"],
)
def test_patch_without_changes_preserves_signing_link(status):
    quotation = _quotation()
    quotation.status = status
    db = _db()

    payload = QuotationUpdate(
        client_id=295,
        contact_id=None,
        valid_until=None,
        payment_terms=None,
        notes=None,
    )

    with (
        patch(
            "app.services.quotations.get_quotation",
            return_value=quotation,
        ),
        patch(
            "app.services.quotations._ensure_client_exists",
        ),
        patch(
            "app.services.quotations._contact_belongs_to_client",
            return_value=True,
        ),
        patch(
            "app.services.quotations.invalidate_document_links",
        ) as invalidate,
        patch(
            "app.services.quotations._write_snapshot",
        ) as snapshot,
        patch(
            "app.services.quotations.write_audit_log",
        ),
    ):
        result = update_quotation(db, 48, payload, user_id=2)

    assert result is quotation
    assert quotation.status == status
    invalidate.assert_not_called()
    snapshot.assert_not_called()
    db.commit.assert_called_once()


@pytest.mark.parametrize(
    "status",
    ["draft", "sent", "waiting"],
)
def test_real_change_invalidates_old_signing_link(status):
    quotation = _quotation()
    quotation.status = status
    db = _db()

    payload = QuotationUpdate(
        notes="Nueva condición comercial",
    )

    with (
        patch(
            "app.services.quotations.get_quotation",
            return_value=quotation,
        ),
        patch(
            "app.services.quotations.invalidate_document_links",
        ) as invalidate,
        patch(
            "app.services.quotations._write_snapshot",
        ) as snapshot,
        patch(
            "app.services.quotations.write_audit_log",
        ),
    ):
        result = update_quotation(db, 48, payload, user_id=2)

    assert result.notes == "Nueva condición comercial"
    assert result.status == status
    invalidate.assert_called_once_with(db, quotation_id=48)
    snapshot.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.parametrize(
    "commercial_components",
    [None, []],
)
def test_simple_quotation_item_accepts_no_components(commercial_components):
    from app.schemas.quotation import QuotationItemUpdate
    from app.services.quotations import _quotation_item_values

    data = {
        "service_name": "Calibración a flujómetro",
        "description": "Descripción comercial actualizada",
        "quantity": 2,
        "unit_price": "1600.00",
    }

    if commercial_components is not None:
        data["commercial_components"] = commercial_components

    payload = QuotationItemUpdate(**data)

    existing_item = SimpleNamespace(
        operational_snapshot=None,
    )

    values = _quotation_item_values(
        MagicMock(),
        payload,
        existing_item=existing_item,
    )

    assert values["service_name"] == "Calibración a flujómetro"
    assert values["description"] == "Descripción comercial actualizada"
    assert values["quantity"] == 2
    assert values["unit_price"] == 1600
    assert "commercial_components" not in values


def test_simple_quotation_item_rejects_real_components():
    from fastapi import HTTPException

    from app.schemas.quotation import QuotationItemUpdate
    from app.services.quotations import _quotation_item_values

    payload = QuotationItemUpdate(
        service_name="Calibración a flujómetro",
        commercial_components=[
            {
                "catalog_item_id": 12,
                "description": "Componente no permitido",
            }
        ],
    )

    existing_item = SimpleNamespace(
        operational_snapshot=None,
    )

    with pytest.raises(HTTPException) as exc:
        _quotation_item_values(
            MagicMock(),
            payload,
            existing_item=existing_item,
        )

    assert exc.value.status_code == 422
    assert "servicio compuesto" in exc.value.detail
