const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api';
const ACCESS_TOKEN_KEY = 'myc_access_token';
const REFRESH_TOKEN_KEY = 'myc_refresh_token';

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

async function request(path, options = {}) {
  const token = getAccessToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {})
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let message = 'No se pudo completar la solicitud';
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
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    method: options.method ?? 'POST',
    headers,
    body: formData
  });
  if (!response.ok) {
    let message = 'No se pudo completar la solicitud';
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
  const token = getAccessToken();
  const headers = {
    ...(options.headers ?? {})
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers
  });
  if (!response.ok) {
    let message = 'No se pudo completar la solicitud';
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

export async function listInvoices() {
  return request('/invoices');
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

export async function getInvoicePaymentReceiptPdfUrl(paymentId) {
  return `${API_URL}/invoice-payments/${paymentId}/receipt-pdf`;
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

export async function getDashboardCounts() {
  const endpoints = [
    ['clients', '/clients'],
    ['quotations', '/quotations'],
    ['equipment', '/equipment'],
    ['fieldSheets', '/field-sheets']
  ];

  const results = await Promise.all(
    endpoints.map(async ([key, path]) => {
      const items = await request(path);
      return [key, Array.isArray(items) ? items.length : 0];
    })
  );

  const certificates = await request('/certificates');
  const certificateItems = Array.isArray(certificates) ? certificates : [];
  const serviceOrders = await request('/service-orders');
  const serviceOrderItems = Array.isArray(serviceOrders) ? serviceOrders : [];
  const fieldSheets = await request('/field-sheets');
  const fieldSheetItems = Array.isArray(fieldSheets) ? fieldSheets : [];
  const openServiceOrders = serviceOrderItems.filter((item) => !['closed', 'cancelled'].includes(item.status));
  const etsProgressValues = openServiceOrders.map((order) => {
    const stageChecks = [
      Boolean(order.quotation_id),
      Boolean(order.agenda_date),
      order.total_equipment > 0,
      certificateItems.some((certificate) => certificate.service_order_id === order.id),
      certificateItems.some((certificate) => certificate.service_order_id === order.id && certificate.final_pdf_path),
      certificateItems.some((certificate) => certificate.service_order_id === order.id && ['quality_approved', 'pdf_pending', 'pdf_uploaded', 'released_to_client'].includes(certificate.status)),
      certificateItems.some((certificate) => certificate.service_order_id === order.id && certificate.authenticated_pdf_path),
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
    certificatesToRelease: certificateItems.filter((item) => ['quality_approved', 'pdf_pending', 'pdf_uploaded'].includes(item.status)).length,
    billingPending: serviceOrderItems.filter((item) => item.status === 'pending_payment' || item.requires_payment).length,
    certificates: certificateItems.length,
    certificatesReview: certificateItems.filter((item) => ['ready_for_quality', 'quality_review'].includes(item.status)).length,
    certificatesApproved: certificateItems.filter((item) => ['quality_approved', 'pdf_pending', 'pdf_uploaded'].includes(item.status)).length,
    certificatesReleased: certificateItems.filter((item) => item.status === 'released_to_client').length,
    authenticationPending: certificateItems.filter((item) => ['quality_approved', 'pdf_pending', 'pdf_uploaded'].includes(item.status) && !item.authenticated_pdf_path).length,
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
  const token = getAccessToken();
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(getAuthenticatedCertificatePdfUrl(certificateId), { headers });
  if (!response.ok) {
    let message = 'No se pudo descargar el PDF autenticado';
    try {
      const payload = await response.json();
      message = typeof payload.detail === 'string' ? payload.detail : message;
    } catch {
      // Keep default message.
    }
    throw new Error(message);
  }
  const disposition = response.headers.get('Content-Disposition') ?? '';
  const filename =
    getFilenameFromDisposition(disposition) ??
    `Certificado_${sanitizePdfFilenamePart(folio ?? certificateId)}_${sanitizePdfFilenamePart(authenticationCode ?? 'autenticado')}.pdf`;
  return { blob: await response.blob(), filename };
}

export async function downloadOriginalCertificatePdf(certificateId, filename = null) {
  const token = getAccessToken();
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(getOriginalCertificatePdfUrl(certificateId), { headers });
  if (!response.ok) {
    let message = 'No se pudo abrir el PDF original';
    try {
      const payload = await response.json();
      message = typeof payload.detail === 'string' ? payload.detail : message;
    } catch {
      // Keep default message.
    }
    throw new Error(message);
  }
  const disposition = response.headers.get('Content-Disposition') ?? '';
  return {
    blob: await response.blob(),
    filename: getFilenameFromDisposition(disposition) ?? filename ?? `Certificado_${certificateId}_original.pdf`
  };
}

export async function bulkUploadCertificatePdfs(serviceOrderId, files) {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append('files', file));
  return uploadRequest(`/service-orders/${serviceOrderId}/certificate-pdfs`, formData);
}

export async function authenticateApprovedCertificates(serviceOrderId) {
  return request(`/service-orders/${serviceOrderId}/certificates/authenticate-approved`, {
    method: 'POST'
  });
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
