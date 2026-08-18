const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api';
const ACCESS_TOKEN_KEY = 'myc_access_token';
const REFRESH_TOKEN_KEY = 'myc_refresh_token';
const PORTAL_ACCESS_TOKEN_KEY = 'myc_portal_access_token';
const PORTAL_REFRESH_TOKEN_KEY = 'myc_portal_refresh_token';

export function getAccessToken() {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function saveTokens({ access_token, refresh_token }) {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
}

export function clearTokens() {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getPortalAccessToken() {
  return window.localStorage.getItem(PORTAL_ACCESS_TOKEN_KEY);
}

export function savePortalTokens({ access_token, refresh_token }) {
  window.localStorage.setItem(PORTAL_ACCESS_TOKEN_KEY, access_token);
  window.localStorage.setItem(PORTAL_REFRESH_TOKEN_KEY, refresh_token);
}

export function clearPortalTokens() {
  window.localStorage.removeItem(PORTAL_ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(PORTAL_REFRESH_TOKEN_KEY);
}

async function request(path, options = {}) {
  const token = options.portal ? getPortalAccessToken() : getAccessToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {})
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error('No fue posible conectar con el ERP. Verifica la red e inténtalo de nuevo.');
  }

  if (!response.ok) {
    let message = response.status === 401
      ? 'Tu sesión no es válida o expiró. Inicia sesión nuevamente.'
      : response.status === 403
        ? 'No tienes permiso para realizar esta acción.'
        : 'No se pudo completar la solicitud';
    try {
      const payload = await response.json();
      if (typeof payload.detail === 'string') {
        message = payload.detail;
      } else if (payload.detail && typeof payload.detail.detail === 'string') {
        message = payload.detail.detail;
        if (Array.isArray(payload.detail.fields)) {
          message = `${message} ${payload.detail.fields.map((field) => field.message).join(' ')}`;
        }
      } else if (payload.detail && typeof payload.detail.message === 'string') {
        message = payload.detail.message;
      } else if (typeof payload.message === 'string') {
        message = payload.message;
      }
    } catch {
      // Keep default message when response is not JSON.
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function uploadRequest(path, formData, options = {}) {
  const token = getAccessToken();
  const headers = {
    ...(options.headers ?? {})
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      method: options.method ?? 'POST',
      headers,
      body: formData
    });
  } catch {
    throw new Error('No fue posible conectar con el ERP. Verifica la red e inténtalo de nuevo.');
  }
  if (!response.ok) {
    let message = response.status === 401
      ? 'Tu sesión no es válida o expiró. Inicia sesión nuevamente.'
      : response.status === 403
        ? 'No tienes permiso para realizar esta acción.'
        : 'No se pudo completar la solicitud';
    try {
      const payload = await response.json();
      message = typeof payload.detail === 'string' ? payload.detail : payload.detail?.message ?? payload.message ?? message;
    } catch {
      // Keep default message.
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

async function downloadRequest(path, options = {}) {
  const token = options.portal ? getPortalAccessToken() : getAccessToken();
  const headers = {
    ...(options.headers ?? {})
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error('No fue posible conectar con el ERP. Verifica la red e inténtalo de nuevo.');
  }
  if (!response.ok) {
    let message = response.status === 401
      ? 'Tu sesión no es válida o expiró. Inicia sesión nuevamente.'
      : response.status === 403
        ? 'No tienes permiso para realizar esta acción.'
        : 'No se pudo completar la solicitud';
    try {
      const payload = await response.json();
      message = typeof payload.detail === 'string' ? payload.detail : payload.detail?.message ?? payload.message ?? message;
    } catch {
      // Keep default message.
    }
    throw new Error(message);
  }
  return {
    blob: await response.blob(),
    filename: response.headers.get('content-disposition')?.match(/filename=\"?([^"]+)\"?/)?.[1] ?? null,
    contentType: response.headers.get('content-type') ?? ''
  };
}

export async function login(email, password) {
  const payload = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  });
  saveTokens(payload);
  return payload.user;
}

export async function register({ email, fullName, password }) {
  const payload = await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      full_name: fullName,
      password
    })
  });
  saveTokens(payload);
  return payload.user;
}

export async function getRegistrationStatus() {
  return request('/auth/registration-status');
}

export async function getCurrentUser() {
  return request('/auth/me');
}

export function getQuotationServiceExceptionContext(quotationFolio) {
  return request(
    `/quotation-service-exceptions/quotations/${encodeURIComponent(quotationFolio)}/context`
  );
}

export function listQuotationServiceExceptions(params = {}) {
  const query = new URLSearchParams();
  if (params.quotationFolio) query.set('quotation_folio', params.quotationFolio);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return request(`/quotation-service-exceptions${suffix}`);
}

export function requestQuotationServiceChange(quotationFolio, payload) {
  return request(
    `/quotation-service-exceptions/quotations/${encodeURIComponent(quotationFolio)}`,
    { method: 'POST', body: JSON.stringify(payload) }
  );
}

export function reviewQuotationServiceChange(exceptionFolio, payload) {
  return request(
    `/quotation-service-exceptions/${encodeURIComponent(exceptionFolio)}/review`,
    { method: 'POST', body: JSON.stringify(payload) }
  );
}

export function previewQuotationUnlock(exceptionFolio, payload) {
  return request(
    `/quotation-service-exceptions/${encodeURIComponent(exceptionFolio)}/preview`,
    { method: 'POST', body: JSON.stringify(payload) }
  );
}

export function applyQuotationServiceChange(exceptionFolio, payload) {
  return request(
    `/quotation-service-exceptions/${encodeURIComponent(exceptionFolio)}/apply`,
    { method: 'POST', body: JSON.stringify(payload) }
  );
}

export function listLinkedCompanies() {
  return request('/catalog-items/linked-companies');
}

export function createLinkedCompany(payload) {
  return request('/catalog-items/linked-companies', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function refreshSession() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error('Sesion expirada');
  }
  const payload = await request('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken })
  });
  saveTokens(payload);
  return payload.user;
}

function resolutionCenterQuery(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value));
    }
  });
  const value = query.toString();
  return value ? `?${value}` : '';
}

export function getResolutionCenterCapabilities() {
  return request('/resolution-center/v1/capabilities');
}

export function listResolutionDefinitions() {
  return request('/resolution-center/v1/definitions');
}

export function getResolutionCenterIndicators() {
  return request('/resolution-center/v1/indicators');
}

export function listCenterResolutions(params = {}) {
  return request(`/resolution-center/v1/resolutions${resolutionCenterQuery(params)}`);
}

export function getCenterResolution(publicId) {
  return request(`/resolution-center/v1/resolutions/${encodeURIComponent(publicId)}`);
}

export function createCenterResolution(payload, idempotencyKey) {
  return request('/resolution-center/v1/resolutions', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    body: JSON.stringify(payload)
  });
}

export function runCenterResolutionStage(publicId, stage, payload = null, idempotencyKey = null) {
  return request(`/resolution-center/v1/resolutions/${encodeURIComponent(publicId)}/${stage}`, {
    method: 'POST',
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
    body: payload === null ? undefined : JSON.stringify(payload)
  });
}

export async function getModules() {
  return request('/modules');
}

export async function listFieldSheetTemplates({ includeAll = false } = {}) {
  return request(`/field-sheet-templates${includeAll ? '?include_all=true' : ''}`);
}

export async function getFieldSheetTemplate(templateKey) {
  return request(`/field-sheet-templates/${templateKey}`);
}

export async function getFieldSheetTemplateCatalog() {
  return request('/field-sheet-templates/catalog');
}

export async function getInstitutionalConfiguration() {
  return request('/institutional-configuration');
}

export async function updateInstitutionalConfiguration(payload) {
  return request('/institutional-configuration', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function createFieldSheetTemplate(payload) {
  return request('/field-sheet-templates', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateFieldSheetTemplateDefinition(templateId, payload) {
  return request(`/field-sheet-templates/${templateId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function duplicateFieldSheetTemplate(templateId) {
  return request(`/field-sheet-templates/${templateId}/duplicate`, {
    method: 'POST',
  });
}

export async function activateFieldSheetTemplate(templateId) {
  return request(`/field-sheet-templates/${templateId}/activate`, {
    method: 'POST',
  });
}

export async function deleteFieldSheetTemplate(templateId) {
  return request(`/field-sheet-templates/${templateId}`, {
    method: 'DELETE',
  });
}

export async function getInvoiceDashboard() {
  return request('/invoices/dashboard');
}

export async function listInvoices(params = {}) {
  const query = new URLSearchParams();
  if (params.serviceOrderId != null) {
    query.set('service_order_id', String(params.serviceOrderId));
  }
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return request(`/invoices${suffix}`);
}

export async function getInvoice(invoiceId) {
  return request(`/invoices/${invoiceId}`);
}

export async function createInvoice(payload) {
  return request('/invoices', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateInvoice(invoiceId, payload) {
  return request(`/invoices/${invoiceId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function changeInvoiceStatus(invoiceId, payload) {
  return request(`/invoices/${invoiceId}/status`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function downloadInstitutionalInvoicePdf(invoiceId) {
  return downloadRequest(`/invoices/${invoiceId}/institutional-pdf`);
}

export function downloadInvoiceFiscalXml(invoiceId) {
  return downloadRequest(`/invoices/${invoiceId}/fiscal-xml`);
}

export async function listInvoicePayments() {
  return request('/invoice-payments');
}

export async function registerInvoicePayment(invoiceId, payload) {
  return request(`/invoices/${invoiceId}/payments`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function downloadInvoicePaymentReceiptPdf(paymentId) {
  return downloadRequest(`/invoice-payments/${paymentId}/receipt-pdf`);
}

export async function listAccountsReceivable() {
  return request('/invoices/accounts-receivable');
}

export async function listReleasedUninvoiced() {
  return request('/invoices/released-uninvoiced');
}

export async function createCreditNote(invoiceId, payload) {
  return request(`/invoices/${invoiceId}/credit-notes`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getInvoiceSettings() {
  return request('/invoice-settings');
}

export function getFacturamaStatus() { return request('/integrations/facturama/status'); }
export function issueInvoice(invoiceId) { return request(`/invoices/${invoiceId}/issue`, { method: 'POST' }); }
export function recoverFacturamaDocuments(invoiceId) { return request(`/invoices/${invoiceId}/facturama-documents/recover`, { method: 'POST' }); }
export function getFacturamaDocumentUrl(invoiceId, kind) { return `${API_URL}/invoices/${invoiceId}/facturama-documents/${kind}`; }

export async function updateInvoiceSettings(payload) {
  return request('/invoice-settings', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function markInvoiceSourceChanged(invoiceId, payload = {}) {
  return request(`/invoices/${invoiceId}/source-change`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function confirmInvoiceReview(invoiceId) {
  return request(`/invoices/${invoiceId}/confirm-review`, {
    method: 'POST',
  });
}

export async function exportFieldSheetTemplate(templateId) {
  return request(`/field-sheet-templates/${templateId}/export`);
}

export async function importFieldSheetTemplate(payload) {
  return request('/field-sheet-templates/import', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getDashboardCounts(user = null) {
  const endpoints = [
    ['clients', '/clients'],
    ['quotations', '/quotations'],
    ['equipment', '/equipment'],
    ['fieldSheets', '/field-sheets']
  ];

  const permissions = new Set(user?.permissions || []);
  const can = (permission) => permissions.has('*') || permissions.has(permission) || permissions.has(`${permission.split('.')[0]}.*`);
  const guardedEndpoints = endpoints.filter(([key]) => can({
    clients: 'clients.read',
    quotations: 'quotations.read',
    equipment: 'equipment.read',
    fieldSheets: 'field_sheets.read',
  }[key]));
  const results = await Promise.all(
    guardedEndpoints.map(async ([key, path]) => {
      const items = await request(path);
      return [key, Array.isArray(items) ? items.length : 0];
    })
  );

  const certificates = can('certificates.read') ? await request('/certificates') : [];
  const certificateItems = Array.isArray(certificates) ? certificates : [];
  const serviceOrders = can('service_orders.read') ? await request('/service-orders') : [];
  const serviceOrderItems = Array.isArray(serviceOrders) ? serviceOrders : [];
  const fieldSheets = can('field_sheets.read') ? await request('/field-sheets') : [];
  const fieldSheetItems = Array.isArray(fieldSheets) ? fieldSheets : [];
  const openServiceOrders = serviceOrderItems.filter((item) => !['closed', 'cancelled'].includes(item.status));
  const etsProgressValues = openServiceOrders.map((order) => {
    const stageChecks = [
      Boolean(order.quotation_id),
      Boolean(order.agenda_date),
      order.total_equipment > 0,
      certificateItems.some((certificate) => certificate.service_order_id === order.id),
      certificateItems.some((certificate) => certificate.service_order_id === order.id && ['quality_approved', 'approved', 'authenticated', 'released_to_client'].includes(certificate.status)),
      certificateItems.some((certificate) => certificate.service_order_id === order.id && certificate.authenticated_pdf_path),
      certificateItems.some((certificate) => certificate.service_order_id === order.id && ['authenticated', 'released_to_client'].includes(certificate.status)),
      !order.requires_payment || ['released', 'closed'].includes(order.status),
      order.status === 'closed'
    ];
    return Math.round((stageChecks.filter(Boolean).length / stageChecks.length) * 100);
  });
  const etsAverageProgress = etsProgressValues.length
    ? Math.round(etsProgressValues.reduce((sum, value) => sum + value, 0) / etsProgressValues.length)
    : 0;

  return {
    ...Object.fromEntries(results),
    serviceOrders: serviceOrderItems.length,
    servicesScheduled: serviceOrderItems.filter((item) => ['scheduled', 'confirmed', 'called'].includes(item.status)).length,
    servicesInProgress: serviceOrderItems.filter((item) => ['in_progress', 'technical_review', 'capture', 'quality_review'].includes(item.status)).length,
    servicesClosed: serviceOrderItems.filter((item) => item.status === 'closed').length,
    capturePending: certificateItems.filter((item) => ['expected', 'field_sheet_ready', 'capture_pending', 'capture_in_progress', 'quality_rejected'].includes(item.status)).length,
    quality: certificateItems.filter((item) => ['ready_for_quality', 'quality_review'].includes(item.status)).length,
    qualityPending: certificateItems.filter((item) => ['ready_for_quality', 'quality_review'].includes(item.status)).length,
    certificatesToRelease: certificateItems.filter((item) => item.status === 'authenticated' && Boolean(item.authenticated_pdf_path)).length,
    billingPending: serviceOrderItems.filter((item) => item.status === 'pending_payment' || item.requires_payment).length,
    certificates: certificateItems.length,
    certificatesReview: certificateItems.filter((item) => ['ready_for_quality', 'quality_review'].includes(item.status)).length,
    certificatesApproved: certificateItems.filter((item) => ['quality_approved', 'approved'].includes(item.status)).length,
    certificatesReleased: certificateItems.filter((item) => item.status === 'released_to_client').length,
    authenticationPending: certificateItems.filter((item) => ['quality_approved', 'approved'].includes(item.status)).length,
    authenticatedCertificates: certificateItems.filter((item) => item.authenticated_pdf_path).length,
    returnedToTechnician: fieldSheetItems.filter((item) => item.status === 'returned_to_technician').length,
    etsAverageProgress
  };
}

export async function listClients(params = {}) {
  const query = new URLSearchParams();
  if (typeof params.includeInactive === 'boolean') {
    query.set('include_inactive', params.includeInactive ? 'true' : 'false');
  }
  if (params.search) {
    query.set('search', params.search);
  }
  if (params.status && params.status !== 'all') {
    query.set('status', params.status);
  }
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return request(`/clients${suffix}`);
}

export async function getClient(clientId) {
  return request(`/clients/${clientId}`);
}

export async function createClient(payload) {
  return request('/clients', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateClient(clientId, payload) {
  return request(`/clients/${clientId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteClient(clientId) {
  return request(`/clients/${clientId}`, {
    method: 'DELETE'
  });
}

export async function getClientDeleteEligibility(clientId) {
  return request(`/clients/${clientId}/delete-eligibility`);
}

export async function archiveClient(clientId) {
  return request(`/clients/${clientId}/archive`, { method: 'POST' });
}

export async function restoreClient(clientId) {
  return request(`/clients/${clientId}/restore`, { method: 'POST' });
}

export async function createClientCertificateProfile(clientId, payload) {
  return request(`/clients/${clientId}/certificate-profiles`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateClientCertificateProfile(clientId, profileId, payload) {
  return request(`/clients/${clientId}/certificate-profiles/${profileId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteClientCertificateProfile(clientId, profileId) {
  return request(`/clients/${clientId}/certificate-profiles/${profileId}`, {
    method: 'DELETE'
  });
}

export async function previewClientImport(file) {
  const formData = new FormData();
  formData.append('file', file);
  return uploadRequest('/clients/import/preview', formData);
}

export async function confirmClientImport(rows) {
  return request('/clients/import/confirm', {
    method: 'POST',
    body: JSON.stringify({ rows })
  });
}

export async function exportClients(params = {}) {
  const query = new URLSearchParams();
  query.set('include_inactive', 'true');
  if (params.search) {
    query.set('search', params.search);
  }
  if (params.status && params.status !== 'all') {
    query.set('status', params.status);
  }
  return downloadRequest(`/clients/export?${query.toString()}`);
}

export async function uploadClientTaxConstancy(clientId, file) {
  const formData = new FormData();
  formData.append('file', file);
  return uploadRequest(`/clients/${clientId}/tax-constancy`, formData);
}

export async function previewClientTaxConstancy(file) {
  const formData = new FormData();
  formData.append('file', file);
  return uploadRequest('/clients/tax-constancy/preview', formData);
}

export async function createQuotation(payload) {
  return request('/quotations', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listQuotations() {
  return request('/quotations');
}

export async function listSatCatalogs() {
  return request('/sat-catalogs');
}

export async function listSatCatalogRecords(catalogCode, params = {}) {
  const searchParams = new URLSearchParams();
  if (params.search) searchParams.set('search', params.search);
  if (params.activeOnly !== false) searchParams.set('active_only', 'true');
  if (params.offset != null) searchParams.set('offset', String(params.offset));
  if (params.limit != null) searchParams.set('limit', String(params.limit));
  const query = searchParams.toString();
  return request(`/sat-catalogs/${catalogCode}/records${query ? `?${query}` : ''}`);
}

export async function getQuotation(quotationId) {
  return request(`/quotations/${quotationId}`);
}

export async function updateQuotation(quotationId, payload) {
  return request(`/quotations/${quotationId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function listQuotationSnapshots(quotationId) {
  return request(`/quotations/${quotationId}/snapshots`);
}

export async function restoreQuotationSnapshot(quotationId, snapshotId) {
  return request(`/quotations/${quotationId}/snapshots/restore`, {
    method: 'POST',
    body: JSON.stringify({ snapshot_id: snapshotId })
  });
}

export async function createQuotationItem(quotationId, payload) {
  return request(`/quotations/${quotationId}/items`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateQuotationItem(quotationId, itemId, payload) {
  return request(`/quotations/${quotationId}/items/${itemId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteQuotationItem(quotationId, itemId) {
  return request(`/quotations/${quotationId}/items/${itemId}`, {
    method: 'DELETE'
  });
}

export async function createServiceOrder(payload) {
  return request('/service-orders', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listServiceOrders() {
  return request('/service-orders');
}

export async function getServiceOrder(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}`);
}

export async function getServiceExecutionBoard(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}/execution-board`);
}

export async function getSaleBoard(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}/sale`);
}

export async function initializeSaleOrder(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}/sale/initialize`, { method: 'POST' });
}

export async function registerSaleArrival(serviceOrderId, saleItemId, payload, unitStateId = null) {
  const query = unitStateId ? `?unit_state_id=${unitStateId}` : '';
  return request(`/service-orders/${serviceOrderId}/sale/items/${saleItemId}/arrivals${query}`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function returnSaleWarranty(serviceOrderId, unitStateId, reason) {
  return request(`/service-orders/${serviceOrderId}/sale/units/${unitStateId}/warranty`, { method: 'POST', body: JSON.stringify({ reason }) });
}

export function requestSaleAuthorization(serviceOrderId, payload) {
  return request(`/service-orders/${serviceOrderId}/sale/authorizations`, { method: 'POST', body: JSON.stringify(payload) });
}

export function resolveSaleAuthorization(serviceOrderId, authorizationId, payload) {
  return request(`/service-orders/${serviceOrderId}/sale/authorizations/${authorizationId}/resolve`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function createSaleDelivery(serviceOrderId, payload) {
  return request(`/service-orders/${serviceOrderId}/sale/deliveries`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function dispatchSaleDelivery(serviceOrderId, deliveryId) {
  return request(`/service-orders/${serviceOrderId}/sale/deliveries/${deliveryId}/dispatch`, { method: 'POST' });
}

export async function reportSaleCourierDelivery(serviceOrderId, deliveryId) {
  return request(`/service-orders/${serviceOrderId}/sale/deliveries/${deliveryId}/courier-confirm`, { method: 'POST' });
}

export async function confirmSaleDelivery(serviceOrderId, deliveryId, payload) {
  return request(`/service-orders/${serviceOrderId}/sale/deliveries/${deliveryId}/receive`, { method: 'POST', body: JSON.stringify(payload) });
}

export async function closeSaleOrder(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}/sale/close`, { method: 'POST' });
}

export function downloadSaleDeliveryNote(serviceOrderId, deliveryId) {
  return downloadRequest(`/service-orders/${serviceOrderId}/sale/deliveries/${deliveryId}/note.pdf`);
}

export async function createServiceUnits(serviceOrderId, units) {
  return request(`/service-orders/${serviceOrderId}/service-units`, {
    method: 'POST',
    body: JSON.stringify({ units })
  });
}

export async function createServiceStage(serviceUnitId, payload) {
  return request(`/service-orders/service-units/${serviceUnitId}/stages`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateServiceStage(serviceStageId, payload) {
  return request(`/service-orders/stages/${serviceStageId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function createTechnicalServiceRequest(serviceStageId, payload) {
  return request(`/service-orders/stages/${serviceStageId}/technical-requests`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function decideQuotationItem(quotationId, itemId, payload) {
  return request(`/quotations/${quotationId}/items/${itemId}/decision`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateServiceOrder(serviceOrderId, payload) {
  return request(`/service-orders/${serviceOrderId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function confirmServiceOrderSignatures(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}/confirm-signatures`, {
    method: 'POST'
  });
}

export async function deleteServiceOrder(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}`, {
    method: 'DELETE'
  });
}

export async function deleteServiceWorkOrder(workOrderId) {
  return request(`/service-orders/work-orders/${workOrderId}`, {
    method: 'DELETE'
  });
}

export async function changeServiceOrderStatus(serviceOrderId, action, comment = null) {
  return request(`/service-orders/${serviceOrderId}/${action}`, {
    method: 'POST',
    body: JSON.stringify({ comment })
  });
}

export async function createServiceOrderException(serviceOrderId, payload) {
  return request(`/service-orders/${serviceOrderId}/exceptions`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listEquipment(params = {}) {
  return request(`/equipment${buildQuery(params)}`);
}

export async function createEquipment(payload) {
  return request('/equipment', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateEquipment(equipmentId, payload) {
  return request(`/equipment/${equipmentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteEquipment(equipmentId) {
  return request(`/equipment/${equipmentId}`, {
    method: 'DELETE'
  });
}

export async function changeEquipmentStatus(equipmentId, action, comment = null) {
  return request(`/equipment/${equipmentId}/${action}`, {
    method: 'POST',
    body: JSON.stringify({ comment })
  });
}

export async function listFieldSheets(params = {}) {
  return request(`/field-sheets${buildQuery(params)}`);
}

export async function getFieldSheet(fieldSheetId) {
  return request(`/field-sheets/${fieldSheetId}`);
}

export async function createFieldSheet(payload) {
  return request('/field-sheets', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateFieldSheet(fieldSheetId, payload) {
  return request(`/field-sheets/${fieldSheetId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function completeFieldSheet(fieldSheetId, comment = null) {
  return request(`/field-sheets/${fieldSheetId}/complete`, {
    method: 'POST',
    body: JSON.stringify({ comment })
  });
}

export async function reviewFieldSheet(fieldSheetId, comment = null) {
  return request(`/field-sheets/${fieldSheetId}/review`, {
    method: 'POST',
    body: JSON.stringify({ comment })
  });
}

export async function deleteFieldSheet(fieldSheetId) {
  return request(`/field-sheets/${fieldSheetId}`, {
    method: 'DELETE'
  });
}

export function getWorkOrderPdfUrl(serviceOrderId) {
  return `${API_URL}/service-orders/${serviceOrderId}/work-order-pdf`;
}

export function getServiceOrderWorkOrdersPdfUrl(serviceOrderId) {
  return `${API_URL}/service-orders/${serviceOrderId}/work-orders-pdf`;
}

export function getServiceWorkOrderPdfUrl(workOrderId) {
  return `${API_URL}/service-orders/work-orders/${workOrderId}/pdf`;
}


export async function downloadWorkOrderPdf(serviceOrderId, workOrderNumber = null, clientName = '', workOrderId = null, allWorkOrders = false) {
  const token = getAccessToken();
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(
    workOrderId
      ? getServiceWorkOrderPdfUrl(workOrderId)
      : allWorkOrders
        ? getServiceOrderWorkOrdersPdfUrl(serviceOrderId)
        : getWorkOrderPdfUrl(serviceOrderId),
    { headers }
  );
  if (!response.ok) {
    throw new Error('No se pudo generar el PDF de la orden de trabajo');
  }
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const filename =
    getFilenameFromDisposition(disposition) ??
    `Orden_Trabajo_${sanitizePdfFilenamePart(workOrderNumber ?? serviceOrderId)}_${sanitizePdfFilenamePart(clientName)}.pdf`;
  return { blob: await response.blob(), filename };
}

export function getFieldSheetPdfUrl(fieldSheetId) {
  return `${API_URL}/field-sheets/${fieldSheetId}/pdf`;
}

export async function downloadFieldSheetPdf(fieldSheetId, workOrderNumber = null, equipmentName = '') {
  const token = getAccessToken();
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(getFieldSheetPdfUrl(fieldSheetId), { headers });
  if (!response.ok) {
    throw new Error('No se pudo generar el PDF de la hoja de campo');
  }
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const filename =
    getFilenameFromDisposition(disposition) ??
    `Hoja_Campo_${sanitizePdfFilenamePart(workOrderNumber ?? fieldSheetId)}_${sanitizePdfFilenamePart(equipmentName)}.pdf`;
  return { blob: await response.blob(), filename };
}

export async function listCertificates(params = {}) {
  return request(`/certificates${buildQuery(params)}`);
}

export async function getCertificate(certificateId) {
  return request(`/certificates/${certificateId}`);
}

export async function getCertificateReleaseReadiness(serviceOrderId) {
  return request(`/certificates/release-readiness/${serviceOrderId}`);
}

export async function createCertificate(payload) {
  return request('/certificates', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateCertificate(certificateId, payload) {
  return request(`/certificates/${certificateId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function changeCertificateStatus(certificateId, action, comment = null) {
  return request(`/certificates/${certificateId}/${action}`, {
    method: 'POST',
    body: JSON.stringify({ comment })
  });
}

export async function uploadCertificatePdf(certificateId, file, comment = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (comment) formData.append('comment', comment);
  return uploadRequest(`/certificates/${certificateId}/upload-pdf`, formData);
}

export async function validateCertificatePdfMatch(certificateId) {
  return request(`/certificates/${certificateId}/validate-pdf-match`, {
    method: 'POST'
  });
}

export async function manualAcceptCertificateMatch(certificateId, comment = null) {
  return request(`/certificates/${certificateId}/manual-accept-match`, {
    method: 'POST',
    body: JSON.stringify({ comment })
  });
}

export async function authenticateCertificate(certificateId) {
  return request(`/certificates/${certificateId}/authenticate`, {
    method: 'POST'
  });
}

export function getAuthenticatedCertificatePdfUrl(certificateId) {
  return `${API_URL}/certificates/${certificateId}/authenticated-pdf`;
}

export function getOriginalCertificatePdfUrl(certificateId) {
  return `${API_URL}/certificates/${certificateId}/original-pdf`;
}

export async function downloadAuthenticatedCertificatePdf(certificateId, folio = null, authenticationCode = null) {
  const result = await downloadRequest(`/certificates/${certificateId}/authenticated-pdf`);
  const filename = result.filename ??
    `Certificado_${sanitizePdfFilenamePart(folio ?? certificateId)}_${sanitizePdfFilenamePart(authenticationCode ?? 'autenticado')}.pdf`;
  return { blob: result.blob, filename };
}

export async function downloadOriginalCertificatePdf(certificateId, filename = null) {
  const result = await downloadRequest(`/certificates/${certificateId}/original-pdf`);
  return {
    blob: result.blob,
    filename: result.filename ?? filename ?? `Certificado_${certificateId}_original.pdf`
  };
}

export async function bulkUploadCertificatePdfs(serviceOrderId, files) {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append('files', file));
  return uploadRequest(`/service-orders/${serviceOrderId}/certificate-pdfs`, formData);
}

export async function releaseAuthenticatedCertificates(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}/certificates/release-authenticated`, {
    method: 'POST'
  });
}

export async function deleteCertificate(certificateId) {
  return request(`/certificates/${certificateId}`, {
    method: 'DELETE'
  });
}

export async function listAuditLogs(params = {}) {
  return request(`/audit-logs${buildQuery(params)}`);
}

export async function listUsers() {
  return request('/users');
}

export async function listRoles() {
  return request('/users/roles');
}

export async function createUser(payload) {
  return request('/users', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateUser(userId, payload) {
  return request(`/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function updateUserRoles(userId, roleNames) {
  return request(`/users/${userId}/roles`, {
    method: 'PATCH',
    body: JSON.stringify({
      role_names: roleNames
    })
  });
}

export async function updateUserStatus(userId, isActive) {
  return request(`/users/${userId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({
      is_active: isActive
    })
  });
}

export async function listUserActivity(userId) {
  return request(`/users/${userId}/activity`);
}

export async function deleteQuotation(quotationId) {
  return request(`/quotations/${quotationId}`, {
    method: 'DELETE'
  });
}

function buildQuery(params = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, value);
    }
  });
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

export async function listCatalogItems(params = {}) {
  return request(`/catalog-items${buildQuery(params)}`);
}

export async function getCapturePackageSummary(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}/capture-package-summary`);
}

export async function downloadCapturePackage(serviceOrderId, workOrderId = null, fallbackFilename = null) {
  const path = workOrderId
    ? `/service-orders/${serviceOrderId}/work-orders/${workOrderId}/capture-package`
    : `/service-orders/${serviceOrderId}/capture-package`;
  const response = await downloadRequest(path);
  const invalidName = !response.filename || ['null', 'undefined', ''].includes(response.filename.toLowerCase());
  return { ...response, filename: invalidName ? (fallbackFilename || `ETS-${serviceOrderId}.zip`) : response.filename };
}

export async function uploadCaptureFiles(serviceOrderId, files) {
  const formData = new FormData();
  Array.from(files || []).forEach((file) => formData.append('files', file));
  return uploadRequest(`/service-orders/${serviceOrderId}/capture-files`, formData);
}

export async function listCaptureFiles(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}/capture-files`);
}

export async function listCaptureMasterReadiness(serviceOrderId = null) {
  return request(`/certificates/capture-master-readiness${serviceOrderId ? `?service_order_id=${serviceOrderId}` : ''}`);
}

export async function downloadCaptureMaster(certificateId, fallbackFilename = null) {
  const response = await downloadRequest(`/certificates/${certificateId}/capture-master`);
  return {
    ...response,
    filename: response.filename || fallbackFilename || `Master_${certificateId}.xlsx`,
  };
}

export async function listReferenceStandards(params = {}) {
  return request(`/reference-standards${buildQuery(params)}`);
}

export async function getReferenceStandard(standardId) {
  return request(`/reference-standards/${standardId}`);
}

export async function createReferenceStandard(payload) {
  return request('/reference-standards', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateReferenceStandard(standardId, payload) {
  return request(`/reference-standards/${standardId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteReferenceStandard(standardId) {
  return request(`/reference-standards/${standardId}`, {
    method: 'DELETE'
  });
}

export async function createReferenceStandardUncertainty(standardId, payload) {
  return request(`/reference-standards/${standardId}/uncertainties`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateReferenceStandardUncertainty(standardId, uncertaintyId, payload) {
  return request(`/reference-standards/${standardId}/uncertainties/${uncertaintyId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteReferenceStandardUncertainty(standardId, uncertaintyId) {
  return request(`/reference-standards/${standardId}/uncertainties/${uncertaintyId}`, {
    method: 'DELETE'
  });
}

export async function listReferenceStandardCertificates(params = {}) {
  return request(`/reference-standard-certificates${buildQuery(params)}`);
}

export async function createReferenceStandardCertificate(standardId, payload) {
  return request(`/reference-standards/${standardId}/certificates`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateReferenceStandardCertificate(certificateId, payload) {
  return request(`/reference-standard-certificates/${certificateId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function activateReferenceStandardCertificate(certificateId) {
  return request(`/reference-standard-certificates/${certificateId}/activate`, {
    method: 'POST'
  });
}

export async function suspendReferenceStandardCertificate(certificateId) {
  return request(`/reference-standard-certificates/${certificateId}/suspend`, {
    method: 'POST'
  });
}

export async function createReferenceStandardCertificateUncertainty(certificateId, payload) {
  return request(`/reference-standard-certificates/${certificateId}/uncertainties`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateReferenceStandardCertificateUncertainty(uncertaintyId, payload) {
  return request(`/reference-standard-certificates/uncertainties/${uncertaintyId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteReferenceStandardCertificateUncertainty(uncertaintyId) {
  return request(`/reference-standard-certificates/uncertainties/${uncertaintyId}`, {
    method: 'DELETE'
  });
}

export async function suggestFieldSheetPatterns(fieldSheetId) {
  return request(`/field-sheets/${fieldSheetId}/suggest-patterns`, {
    method: 'POST'
  });
}

export async function validateFieldSheetPatterns(fieldSheetId) {
  return request(`/field-sheets/${fieldSheetId}/validate-selected-patterns`, {
    method: 'POST'
  });
}

export async function listCalibrationProcedures(params = {}) {
  return request(`/calibration-procedures${buildQuery(params)}`);
}

export async function getCalibrationProcedure(procedureId) {
  return request(`/calibration-procedures/${procedureId}`);
}

export async function createCalibrationProcedure(payload) {
  return request('/calibration-procedures', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateCalibrationProcedure(procedureId, payload) {
  return request(`/calibration-procedures/${procedureId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteCalibrationProcedure(procedureId) {
  return request(`/calibration-procedures/${procedureId}`, {
    method: 'DELETE'
  });
}

export async function listMetrologyProfiles() {
  return request('/metrology/profiles');
}

export async function calculateMetrologyPreview(payload) {
  return request('/metrology/calculate-preview', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listControlledDocuments(params = {}) {
  return request(`/documents${buildQuery(params)}`);
}

export async function createControlledDocument(payload) {
  return request('/documents', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function createCertificateMaster({ code, name, description, revision, effectiveDate, expiresOn, file }) {
  const formData = new FormData();
  formData.append('code', code);
  formData.append('name', name);
  formData.append('revision', revision);
  formData.append('effective_date', effectiveDate);
  if (expiresOn) formData.append('expires_on', expiresOn);
  if (description) formData.append('description', description);
  formData.append('file', file);
  return uploadRequest('/documents/certificate-masters', formData);
}

export async function downloadControlledDocumentVersion(documentId, versionId) {
  return downloadRequest(`/documents/${documentId}/versions/${versionId}/download`);
}

export async function updateControlledDocument(documentId, payload) {
  return request(`/documents/${documentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function createControlledDocumentVersion(documentId, payload) {
  return request(`/documents/${documentId}/versions`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function activateControlledDocumentVersion(documentId, versionId) {
  return request(`/documents/${documentId}/versions/${versionId}/activate`, {
    method: 'POST'
  });
}

export async function archiveControlledDocument(documentId, payload) {
  return request(`/documents/${documentId}/archive`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function listDocumentInterpretations(params = {}) {
  return request(`/document-interpretations${buildQuery(params)}`);
}

export async function createDocumentInterpretation(payload) {
  return request('/document-interpretations', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateDocumentInterpretation(interpretationId, payload) {
  return request(`/document-interpretations/${interpretationId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function approveDocumentInterpretation(interpretationId) {
  return request(`/document-interpretations/${interpretationId}/approve`, {
    method: 'POST'
  });
}

export async function listTechnicalProfiles(params = {}) {
  return request(`/technical-profiles${buildQuery(params)}`);
}

export async function createTechnicalProfile(payload) {
  return request('/technical-profiles', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateTechnicalProfile(profileId, payload) {
  return request(`/technical-profiles/${profileId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function approveTechnicalProfile(profileId) {
  return request(`/technical-profiles/${profileId}/approve`, {
    method: 'POST'
  });
}

export async function resolveTechnicalProfiles(params = {}) {
  return request(`/technical-profiles/resolve${buildQuery(params)}`);
}

export async function listUncertaintyModels(params = {}) {
  return request(`/uncertainty/models${buildQuery(params)}`);
}

export async function createUncertaintyModel(payload) {
  return request('/uncertainty/models', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateUncertaintyModel(modelId, payload) {
  return request(`/uncertainty/models/${modelId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function listUncertaintyModelVersions(modelId) {
  return request(`/uncertainty/models/${modelId}/versions`);
}

export async function getUncertaintyModelVersion(versionId) {
  return request(`/uncertainty/model-versions/${versionId}`);
}

export async function createUncertaintyModelVersion(modelId, payload) {
  return request(`/uncertainty/models/${modelId}/versions`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateUncertaintyModelVersion(versionId, payload) {
  return request(`/uncertainty/model-versions/${versionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function changeUncertaintyModelVersionStatus(versionId, action) {
  return request(`/uncertainty/model-versions/${versionId}/${action}`, {
    method: 'POST'
  });
}

export async function cloneUncertaintyModelVersion(versionId, payload) {
  return request(`/uncertainty/model-versions/${versionId}/clone`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function createUncertaintyComponent(versionId, payload) {
  return request(`/uncertainty/model-versions/${versionId}/components`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateUncertaintyComponent(componentId, payload) {
  return request(`/uncertainty/components/${componentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteUncertaintyComponent(componentId) {
  return request(`/uncertainty/components/${componentId}`, {
    method: 'DELETE'
  });
}

export async function createUncertaintyFormula(versionId, payload) {
  return request(`/uncertainty/model-versions/${versionId}/formulas`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateUncertaintyFormula(formulaId, payload) {
  return request(`/uncertainty/formulas/${formulaId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteUncertaintyFormula(formulaId) {
  return request(`/uncertainty/formulas/${formulaId}`, {
    method: 'DELETE'
  });
}

export async function getUncertaintyPreview(fieldSheetId) {
  return request(`/uncertainty/field-sheets/${fieldSheetId}/preview`);
}

export async function createCatalogItem(payload) {
  return request('/catalog-items', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function updateCatalogItem(catalogItemId, payload) {
  return request(`/catalog-items/${catalogItemId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function deleteCatalogItem(catalogItemId) {
  return request(`/catalog-items/${catalogItemId}`, {
    method: 'DELETE'
  });
}

export async function getQuotationTemplate() {
  return request('/document-templates/quotation');
}

export async function updateQuotationTemplate(payload) {
  return request('/document-templates/quotation', {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function restoreQuotationTemplateDefaults() {
  return request('/document-templates/quotation/restore-defaults', {
    method: 'POST',
    body: JSON.stringify({})
  });
}

export function getQuotationPdfUrl(quotationId) {
  return `${API_URL}/quotations/${quotationId}/pdf`;
}

function sanitizePdfFilenamePart(value) {
  return String(value ?? 'cotizacion')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .replace(/[^A-Za-z0-9_.-]+/g, '-')
    .replace(/^[-_.]+|[-_.]+$/g, '') || 'cotizacion';
}

function getFilenameFromDisposition(disposition) {
  const encodedMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encodedMatch?.[1]) {
    return decodeURIComponent(encodedMatch[1].replace(/"/g, ''));
  }
  const match = disposition.match(/filename="([^"]+)"/i);
  return match?.[1] ?? null;
}

export async function downloadQuotationPdf(quotationId, quotation = null, clientName = '') {
  const token = getAccessToken();
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(getQuotationPdfUrl(quotationId), { headers });
  if (!response.ok) {
    throw new Error('No se pudo generar el PDF de la cotizacion');
  }

  const disposition = response.headers.get('Content-Disposition') ?? '';
  const filename =
    getFilenameFromDisposition(disposition) ??
    `Cotizacion_${sanitizePdfFilenamePart(quotation?.folio ?? quotationId)}_${sanitizePdfFilenamePart(clientName)}.pdf`;
  const blob = await response.blob();
  return { blob, filename };
}

export async function changeQuotationStatus(quotationId, action, comment = null) {
  return request(`/quotations/${quotationId}/${action}`, {
    method: 'POST',
    body: JSON.stringify({ comment })
  });
}

export function getActivity(entityType, entityId) {
  return request(`/activity/${entityType}/${entityId}`);
}

export function listActivityEntities() {
  return request('/activity/entities');
}

export function listActivityMentionableUsers() {
  return request('/activity/mentionable-users');
}

export function getResolutionActivityTarget(publicId) {
  return request(`/activity/resolution-target/${encodeURIComponent(publicId)}`);
}

export function listActivityInbox({
  unreadOnly = false,
  attentionOnly = false,
  limit = 50,
} = {}) {
  const query = new URLSearchParams({
    unread_only: String(unreadOnly),
    attention_only: String(attentionOnly),
    limit: String(limit),
  });
  return request(`/activity/inbox?${query.toString()}`);
}

export function markActivityRead(entityType, entityId) {
  return request(`/activity/${entityType}/${entityId}/read`, {
    method: 'POST',
  });
}

export function createActivityMessage(entityType, entityId, payload) {
  return request(`/activity/${entityType}/${entityId}/messages`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateActivityMessage(messageId, payload) {
  return request(`/activity/messages/${messageId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function withdrawActivityMessage(messageId, payload) {
  return request(`/activity/messages/${messageId}`, {
    method: 'DELETE',
    body: JSON.stringify(payload),
  });
}

export function requestActivityAttention(messageId, payload) {
  return request(`/activity/messages/${messageId}/attention`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function resolveActivityAttention(attentionId, payload = {}) {
  return request(`/activity/attention/${attentionId}/resolve`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function addActivityAttachment(messageId, file) {
  const formData = new FormData();
  formData.append('file', file);
  return uploadRequest(`/activity/messages/${messageId}/attachments`, formData);
}

export async function downloadActivityAttachment(attachment) {
  const result = await downloadRequest(`/activity/attachments/${attachment.id}/download`);
  const url = window.URL.createObjectURL(result.blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = result.filename || attachment.original_name || 'archivo';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

function notificationQuery(params = {}) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (
      value !== undefined
      && value !== null
      && value !== ''
    ) {
      query.set(key, String(value));
    }
  });

  const value = query.toString();

  return value
    ? `?${value}`
    : '';
}

export function listNotifications(params = {}) {
  return request(
    `/notifications${notificationQuery(params)}`,
  );
}

export function getNotificationUnreadCount() {
  return request('/notifications/unread-count');
}

export function markNotificationRead(
  notificationId,
) {
  return request(
    `/notifications/${encodeURIComponent(
      notificationId,
    )}/read`,
    {
      method: 'POST',
    },
  );
}

export function markAllNotificationsRead() {
  return request('/notifications/read-all', {
    method: 'POST',
  });
}
export function getCommunicationDirectory() {
  return request('/communications/directory');
}

export function listCommunicationConversations(params = {}) {
  const query = new URLSearchParams();
  if (params.conversation_type) query.set('conversation_type', params.conversation_type);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return request(`/communications/conversations${suffix}`);
}

export function getCommunicationConversation(conversationId) {
  return request(`/communications/conversations/${encodeURIComponent(conversationId)}`);
}

export function createCommunicationConversation(payload) {
  return request('/communications/conversations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function sendCommunicationMessage(conversationId, body) {
  return request(`/communications/conversations/${encodeURIComponent(conversationId)}/messages`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  });
}


export function getClientPortalQuotations() {
  return request('/client-portal/quotations', { portal: true });
}

export function getClientPortalServiceOrders() {
  return request('/client-portal/service-orders', { portal: true });
}

export function getClientPortalCertificates() {
  return request('/client-portal/certificates', { portal: true });
}

export async function downloadClientPortalCertificate(certificate) {
  const result = await downloadRequest(`/client-portal/certificates/${certificate.id}/pdf`, { portal: true });
  const url = window.URL.createObjectURL(result.blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = result.filename || `${certificate.authentication_code || certificate.folio}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

export async function portalLogin(identifier, password) {
  const tokens = await request('/portal/auth/login', { method: 'POST', body: JSON.stringify({ identifier, password }), portal: true });
  savePortalTokens(tokens);
  return getClientPortalProfile();
}

export function portalLogout() {
  return request('/portal/auth/logout', { method: 'POST', portal: true }).finally(clearPortalTokens);
}

export function getClientPortalProfile() {
  return request('/client-portal/profile', { portal: true });
}

export function createPortalRegistration(payload) {
  return request('/portal/registration', { method: 'POST', body: JSON.stringify(payload), portal: true });
}

export function verifyPortalEmail(token) {
  return request('/portal/registration/verify-email', { method: 'POST', body: JSON.stringify({ token }), portal: true });
}

export function validatePortalInvitation(token) {
  return request(`/portal/invitations/${encodeURIComponent(token)}`, { portal: true });
}

export function acceptPortalInvitation(token, payload) {
  return request(`/portal/invitations/${encodeURIComponent(token)}/accept`, { method: 'POST', body: JSON.stringify(payload), portal: true });
}

export function getClientPortalCompany() { return request('/client-portal/company', { portal: true }); }
export function getClientPortalEquipment() { return request('/client-portal/equipment', { portal: true }); }
export function getClientPortalInvoices() { return request('/client-portal/invoices', { portal: true }); }
export function getClientPortalPayments() { return request('/client-portal/payments', { portal: true }); }

export function listPortalMemberships(clientId) { return request(`/client-portal/memberships${clientId ? `?client_id=${clientId}` : ''}`); }
export function listPortalInvitations(clientId) { return request(`/client-portal/invitations${clientId ? `?client_id=${clientId}` : ''}`); }
export function createPortalInvitation(payload) { return request('/client-portal/invitations', { method: 'POST', body: JSON.stringify(payload) }); }
export function listPortalRoles(clientId) { return request(`/client-portal/roles${clientId ? `?client_id=${clientId}` : ''}`); }
export function listPortalRegistrations() { return request('/client-portal/registrations'); }
export function listPortalLinkRequests() { return request('/client-portal/link-requests'); }
export function createPortalLinkRequest(payload) { return request('/client-portal/link-requests', { method: 'POST', body: JSON.stringify(payload) }); }
export function reviewPortalLinkRequest(requestId) { return request(`/client-portal/link-requests/${requestId}/review`, { method: 'POST' }); }
export function approvePortalLinkRequest(requestId, payload) { return request(`/client-portal/link-requests/${requestId}/approve`, { method: 'POST', body: JSON.stringify(payload) }); }
export function rejectPortalLinkRequest(requestId, payload) { return request(`/client-portal/link-requests/${requestId}/reject`, { method: 'POST', body: JSON.stringify(payload) }); }
export function cancelPortalLinkRequest(requestId, reason) { return request(`/client-portal/link-requests/${requestId}/cancel`, { method: 'POST', body: JSON.stringify({ reason }) }); }
export function updatePortalMembershipRoles(membershipId, roleCodes) { return request(`/client-portal/memberships/${membershipId}/roles`, { method: 'PATCH', body: JSON.stringify({ role_codes: roleCodes }) }); }
export function suspendPortalMembership(membershipId, reason) { return request(`/client-portal/memberships/${membershipId}/suspend`, { method: 'POST', body: JSON.stringify({ reason }) }); }
export function reactivatePortalMembership(membershipId) { return request(`/client-portal/memberships/${membershipId}/reactivate`, { method: 'POST' }); }
export function revokePortalMembership(membershipId, reason) { return request(`/client-portal/memberships/${membershipId}/revoke`, { method: 'POST', body: JSON.stringify({ reason }) }); }
export function setPrimaryPortalMembership(membershipId) { return request(`/client-portal/memberships/${membershipId}/primary`, { method: 'POST' }); }
export function cancelPortalInvitation(invitationId) { return request(`/client-portal/invitations/${invitationId}/cancel`, { method: 'POST' }); }
export function revokePortalInvitation(invitationId) { return request(`/client-portal/invitations/${invitationId}/revoke`, { method: 'POST' }); }
export function resendPortalInvitation(invitationId) { return request(`/client-portal/invitations/${invitationId}/resend`, { method: 'POST' }); }
export function getPortalConfiguration(clientId) { return request(`/client-portal/configuration/${clientId}`); }
export function savePortalConfiguration(clientId, payload) { return request(`/client-portal/configuration/${clientId}`, { method: 'PUT', body: JSON.stringify(payload) }); }

export function getPortalCompanyUsers() { return request('/client-portal/users', { portal: true }); }
export function getPortalCompanyInvitations() { return request('/client-portal/users/invitations', { portal: true }); }
export function getPortalCompanyRoles() { return request('/client-portal/users/roles', { portal: true }); }
export function invitePortalCompanyUser(payload) { return request('/client-portal/users/invitations', { method: 'POST', body: JSON.stringify(payload), portal: true }); }
export function updatePortalCompanyUserRoles(membershipId, roleCodes) { return request(`/client-portal/users/${membershipId}/roles`, { method: 'PATCH', body: JSON.stringify({ role_codes: roleCodes }), portal: true }); }
export function suspendPortalCompanyUser(membershipId, reason) { return request(`/client-portal/users/${membershipId}/suspend`, { method: 'POST', body: JSON.stringify({ reason }), portal: true }); }
export function reactivatePortalCompanyUser(membershipId) { return request(`/client-portal/users/${membershipId}/reactivate`, { method: 'POST', portal: true }); }
export function setPrimaryPortalCompanyUser(membershipId) { return request(`/client-portal/users/${membershipId}/primary`, { method: 'POST', portal: true }); }
