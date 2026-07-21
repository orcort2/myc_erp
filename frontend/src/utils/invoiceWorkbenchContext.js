function positiveInteger(value) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function normalizeInvoiceWorkbenchContext(context = {}) {
  const invoiceId = positiveInteger(context.invoice_id ?? context.invoiceId);
  const serviceOrderId = positiveInteger(
    context.service_order_id ?? context.serviceOrderId
  );

  if (invoiceId) return { invoice_id: invoiceId };
  if (serviceOrderId) return { service_order_id: serviceOrderId };
  return null;
}

export function readInvoiceWorkbenchContext(locationLike) {
  const search = locationLike?.search || '';
  const params = new URLSearchParams(search);
  return normalizeInvoiceWorkbenchContext({
    invoice_id: params.get('invoice_id'),
    service_order_id: params.get('service_order_id'),
  });
}

export function buildInvoiceWorkbenchPath(context) {
  const normalized = normalizeInvoiceWorkbenchContext(context);
  if (!normalized) return '/dashboard#facturacion';

  const params = new URLSearchParams();
  if (normalized.invoice_id) {
    params.set('invoice_id', String(normalized.invoice_id));
  } else {
    params.set('service_order_id', String(normalized.service_order_id));
  }
  return `/dashboard?${params.toString()}#facturacion`;
}

export function clearInvoiceWorkbenchContext() {
  const url = new URL(window.location.href);
  url.searchParams.delete('invoice_id');
  url.searchParams.delete('service_order_id');
  window.history.replaceState(
    {},
    '',
    `${url.pathname}${url.search}${url.hash}`
  );
}
