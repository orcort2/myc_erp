const STAMPED_STATUSES = new Set([
  'issued',
  'partially_paid',
  'paid',
  'overdue',
]);

const STATUS_LABELS = {
  draft: 'Borrador',
  pending: 'Pendiente',
  issuing: 'Emitiendo',
  issued: 'Timbrada',
  partially_paid: 'Pago parcial',
  paid: 'Pagada',
  overdue: 'Vencida',
  issue_failed: 'Error de emisión',
  cancelled: 'Cancelada',
  credit_note: 'Nota de crédito',
};

export function getEtsInvoicePresentation(invoice) {
  if (!invoice) {
    return {
      kind: 'empty',
      statusLabel: 'Sin factura',
      primaryActionLabel: 'Crear factura',
      canDownload: false,
    };
  }

  const status = String(invoice.status || '').trim().toLowerCase();
  const isCancelled = status === 'cancelled';
  const canDownload = STAMPED_STATUSES.has(status);

  return {
    kind: isCancelled ? 'cancelled' : canDownload ? 'stamped' : 'draft',
    statusLabel: STATUS_LABELS[status] || invoice.status || 'Sin estado',
    primaryActionLabel: isCancelled
      ? 'Ver detalle'
      : canDownload
        ? 'Ver factura'
        : 'Continuar factura',
    canDownload,
  };
}

export function getEtsInvoiceContextView({ contextResolved, invoice }) {
  if (!contextResolved) {
    return {
      phase: 'loading',
      presentation: null,
    };
  }

  return {
    phase: invoice ? 'invoice' : 'empty',
    presentation: getEtsInvoicePresentation(invoice),
  };
}

export function formatInvoiceInternalFolio(invoice) {
  return [invoice?.series, invoice?.folio].filter(Boolean).join('-');
}
