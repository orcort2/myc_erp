import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { CreditCard, X } from 'lucide-react';

import {
  createInvoicePaymentDraft,
  toInvoicePaymentPayload,
  validateInvoicePaymentDraft,
} from './invoicePaymentForm.js';

function formatMoney(value, currency = 'MXN') {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(Number(value || 0));
}

export default function InvoicePaymentModal({
  invoice,
  open,
  isSaving = false,
  onClose,
  onSubmit,
}) {
  const [draft, setDraft] = useState(() => createInvoicePaymentDraft(invoice));
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDraft(createInvoicePaymentDraft(invoice));
    setError('');
    setSubmitting(false);
  }, [invoice?.id, invoice?.balance_due, open]);

  if (!open || !invoice) return null;

  const currency = invoice.currency || 'MXN';
  const blocked = submitting || isSaving;

  function update(field, value) {
    setDraft((current) => ({ ...current, [field]: value }));
    setError('');
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (blocked) return;

    const validationError = validateInvoicePaymentDraft(
      draft,
      invoice.balance_due
    );
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      await onSubmit?.(toInvoicePaymentPayload(draft));
      onClose?.();
    } catch (requestError) {
      setError(requestError.message || 'No fue posible registrar el pago.');
    } finally {
      setSubmitting(false);
    }
  }

  return createPortal(
    <div className="invoice-payment-modal-layer">
      <section
        aria-labelledby="invoice-payment-modal-title"
        aria-modal="true"
        className="invoice-payment-modal"
        role="dialog"
      >
        <header>
          <div>
            <p>Resumen financiero</p>
            <h3 id="invoice-payment-modal-title">Registrar pago</h3>
          </div>
          <button
            aria-label="Cerrar registro de pago"
            disabled={blocked}
            onClick={onClose}
            type="button"
          >
            <X size={19} />
          </button>
        </header>

        <div className="invoice-payment-modal__summary">
          <article><span>Total</span><strong>{formatMoney(invoice.total, currency)}</strong></article>
          <article><span>Pagado</span><strong>{formatMoney(invoice.amount_paid, currency)}</strong></article>
          <article><span>Saldo</span><strong>{formatMoney(invoice.balance_due, currency)}</strong></article>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="invoice-payment-modal__fields">
            <label>
              <span>Fecha del pago</span>
              <input
                onChange={(event) => update('paid_on', event.target.value)}
                required
                type="date"
                value={draft.paid_on}
              />
            </label>
            <label>
              <span>Importe</span>
              <input
                inputMode="decimal"
                max={Number(invoice.balance_due || 0)}
                min="0.01"
                onChange={(event) => update('amount', event.target.value)}
                required
                step="0.01"
                type="number"
                value={draft.amount}
              />
              <small>Máximo: {formatMoney(invoice.balance_due, currency)}</small>
            </label>
            <label>
              <span>Banco</span>
              <input
                maxLength={120}
                onChange={(event) => update('bank_name', event.target.value)}
                value={draft.bank_name}
              />
            </label>
            <label>
              <span>Cuenta bancaria</span>
              <input
                maxLength={120}
                onChange={(event) => update('bank_account', event.target.value)}
                value={draft.bank_account}
              />
            </label>
            <label>
              <span>Referencia</span>
              <input
                maxLength={120}
                onChange={(event) => update('reference', event.target.value)}
                value={draft.reference}
              />
            </label>
            <label>
              <span>Forma de pago</span>
              <input
                maxLength={80}
                onChange={(event) => update('payment_form', event.target.value)}
                value={draft.payment_form}
              />
            </label>
            <label>
              <span>Método de pago</span>
              <input
                maxLength={80}
                onChange={(event) => update('payment_method', event.target.value)}
                value={draft.payment_method}
              />
            </label>
            <label className="is-wide">
              <span>Notas</span>
              <textarea
                onChange={(event) => update('notes', event.target.value)}
                rows={3}
                value={draft.notes}
              />
            </label>
          </div>

          {error ? <div className="form-error">{error}</div> : null}

          <footer>
            <button
              className="table-button"
              disabled={blocked}
              onClick={onClose}
              type="button"
            >
              Cancelar
            </button>
            <button className="primary-button" disabled={blocked} type="submit">
              <CreditCard size={17} />
              {blocked ? 'Registrando…' : 'Registrar pago'}
            </button>
          </footer>
        </form>
      </section>
    </div>,
    document.body
  );
}
