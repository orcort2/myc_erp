export function resolveInvoiceConceptDescription(
  quotationItem,
  persistedInvoiceItem = null
) {
  const persisted = String(persistedInvoiceItem?.description || '').trim();
  if (persisted) return persisted;

  const serviceName = String(quotationItem?.service_name || '').trim();
  if (serviceName) return serviceName;

  const description = String(quotationItem?.description || '').trim();
  if (description) return description;

  return 'Servicio';
}
