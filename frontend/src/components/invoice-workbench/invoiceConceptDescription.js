export function resolveInvoiceConceptDescription(
  quotationItem,
  persistedInvoiceItem = null
) {
  const persisted = String(persistedInvoiceItem?.description || '').trim();
  if (persisted) return persisted;

  const serviceName = String(quotationItem?.service_name || '').trim();
  const description = String(quotationItem?.description || '').trim();
  const legend = String(quotationItem?.quotation_legend || '').trim();

  return [
    serviceName,
    description && description !== serviceName ? description : '',
    legend,
  ].filter(Boolean).join('\\n') || 'Servicio';
}
