// Contrato de apertura directa de una cotización: /dashboard?quotation_id=ID#cotizaciones
// (también quotation_folio, usado por las notificaciones del desbloqueo EXV).

export function readQuotationDeepLink(search) {
  const params = new URLSearchParams(search || '');
  const rawId = params.get('quotation_id');
  const id = rawId && /^\d+$/.test(rawId) ? Number(rawId) : null;
  const folio = params.get('quotation_folio') || null;
  return id || folio ? { id, folio } : null;
}

export function findDeepLinkedQuotation(quotations, link) {
  if (!link) return null;
  return quotations.find((item) => (
    (link.id != null && item.id === link.id) || (link.id == null && item.folio === link.folio)
  )) ?? null;
}

export function clearQuotationDeepLink(url) {
  const next = new URL(url, 'http://local');
  ['quotation_id', 'quotation_folio', 'exception_folio', 'acceptance_id'].forEach((key) => next.searchParams.delete(key));
  const query = next.searchParams.toString();
  return `${next.pathname}${query ? `?${query}` : ''}${next.hash}`;
}
