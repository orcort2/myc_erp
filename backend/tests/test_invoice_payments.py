from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.auth import RoleRead, UserRead
from app.schemas.invoice import InvoicePaymentCreate
from app.services.facturama.invoices import _mark_issued
from app.services.invoices import list_accounts_receivable, register_invoice_payment


def _invoice(*, status="draft", balance="100.00", paid="0.00"):
    return SimpleNamespace(
        id=11,
        status=status,
        total=Decimal("100.00"),
        subtotal=Decimal("100.00"),
        tax_total=Decimal("0.00"),
        withholding_total=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        balance_due=Decimal(balance),
        amount_paid=Decimal(paid),
        due_on=None,
        last_payment_on=None,
        payments=[],
        credit_notes=[],
        items=[
            SimpleNamespace(
                quantity=Decimal("1.00"),
                unit_price=Decimal("100.00"),
                discount_total=Decimal("0.00"),
                tax_rate=Decimal("0.00"),
                tax_total=Decimal("0.00"),
                line_total=Decimal("100.00"),
            )
        ],
    )


def _payment(amount):
    return InvoicePaymentCreate(
        paid_on=date(2026, 7, 29),
        amount=Decimal(amount),
        reference="REF-1",
    )


def test_partial_and_remaining_payment_update_financial_state():
    invoice = _invoice()
    db = MagicMock()

    with (
        patch("app.services.invoices.get_invoice", return_value=invoice),
        patch("app.services.invoices.write_audit_log"),
    ):
        register_invoice_payment(db, invoice.id, _payment("40.00"), user_id=7)
        assert invoice.amount_paid == Decimal("40.00")
        assert invoice.balance_due == Decimal("60.00")
        assert invoice.status == "partially_paid"

        register_invoice_payment(db, invoice.id, _payment("60.00"), user_id=7)
        assert invoice.amount_paid == Decimal("100.00")
        assert invoice.balance_due == Decimal("0.00")
        assert invoice.status == "paid"
        assert invoice.last_payment_on == date(2026, 7, 29)


@pytest.mark.parametrize("status,balance,amount", [
    ("cancelled", "100.00", "10.00"),
    ("paid", "0.00", "10.00"),
    ("draft", "100.00", "100.01"),
])
def test_payment_rejects_cancelled_settled_and_overpayment(status, balance, amount):
    invoice = _invoice(status=status, balance=balance, paid="100.00" if balance == "0.00" else "0.00")
    with patch("app.services.invoices.get_invoice", return_value=invoice):
        with pytest.raises(HTTPException):
            register_invoice_payment(MagicMock(), invoice.id, _payment(amount), user_id=7)


@pytest.mark.parametrize("paid,balance,expected", [
    ("0.00", "100.00", "issued"),
    ("40.00", "60.00", "partially_paid"),
    ("100.00", "0.00", "paid"),
])
def test_stamping_preserves_financial_status(paid, balance, expected):
    invoice = _invoice(status="issuing", balance=balance, paid=paid)
    attempt = SimpleNamespace(
        status="issuing",
        response_json=None,
        http_status=None,
        error_message=None,
        completed_at=None,
    )
    db = MagicMock()

    with patch("app.services.facturama.invoices.write_audit_log"):
        _mark_issued(
            db,
            invoice,
            attempt,
            provider_payload={"Id": "pac-1", "Uuid": "uuid-1"},
            http_status=200,
            user_id=7,
        )

    assert invoice.status == expected
    assert invoice.cfdi_uuid == "uuid-1"
    assert invoice.amount_paid == Decimal(paid)
    assert invoice.balance_due == Decimal(balance)


def test_accounts_receivable_exposes_paid_amount_and_excludes_settled():
    pending = _invoice(status="partially_paid", balance="60.00", paid="40.00")
    pending.client_id = 4
    pending.client = SimpleNamespace(commercial_name="Cliente MYC", legal_name="Cliente")
    pending.service_order_id = 8
    pending.folio = "F-11"
    settled = _invoice(status="paid", balance="0.00", paid="100.00")

    with patch("app.services.invoices.list_invoices", return_value=[pending, settled]):
        rows = list_accounts_receivable(MagicMock())

    assert len(rows) == 1
    assert rows[0]["amount_paid"] == Decimal("40.00")
    assert rows[0]["balance_due"] == Decimal("60.00")


def test_session_schema_exposes_effective_payment_permissions():
    user = UserRead(
        id=1,
        email="finanzas@example.com",
        full_name="Finanzas",
        is_active=True,
        created_at="2026-07-29T00:00:00Z",
        updated_at="2026-07-29T00:00:00Z",
        roles=[RoleRead(id=2, name="Finanzas", description=None)],
    )

    assert "payments.manage" in user.permissions
