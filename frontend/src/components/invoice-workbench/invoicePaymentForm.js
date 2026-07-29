export function createInvoicePaymentDraft(invoice, today = new Date()) {
  const balance = Math.max(Number(invoice?.balance_due || 0), 0);

  return {
    paid_on: today.toISOString().slice(0, 10),
    amount: balance ? balance.toFixed(2) : '',
    bank_name: '',
    bank_account: '',
    reference: '',
    payment_method: invoice?.payment_method || '',
    payment_form: invoice?.payment_form || '',
    notes: '',
  };
}

export function validateInvoicePaymentDraft(draft, balanceDue) {
  const amount = Number(draft.amount);
  const balance = Number(balanceDue || 0);

  if (!draft.paid_on) return 'Indica la fecha del pago.';
  if (!Number.isFinite(amount) || amount <= 0) {
    return 'El importe debe ser mayor que cero.';
  }
  if (amount > balance + 0.000001) {
    return 'El importe no puede ser mayor que el saldo pendiente.';
  }
  return '';
}

export function toInvoicePaymentPayload(draft) {
  const optional = (value) => String(value || '').trim() || null;

  return {
    paid_on: draft.paid_on,
    amount: Number(draft.amount),
    bank_name: optional(draft.bank_name),
    bank_account: optional(draft.bank_account),
    reference: optional(draft.reference),
    payment_method: optional(draft.payment_method),
    payment_form: optional(draft.payment_form),
    notes: optional(draft.notes),
  };
}

export function canIssueInvoiceAfterPayment(invoice) {
  if (!invoice || invoice.cfdi_uuid || invoice.facturama_id) return false;
  return new Set([
    'draft',
    'issue_failed',
    'issue_rejected',
    'partially_paid',
    'paid',
  ]).has(invoice.status);
}
