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

export async function getDashboardCounts() {
  const endpoints = [
    ['clients', '/clients'],
    ['quotations', '/quotations'],
    ['serviceOrders', '/service-orders'],
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

  return {
    ...Object.fromEntries(results),
    quality: certificateItems.filter((item) => ['generated', 'quality_review'].includes(item.status)).length,
    certificates: certificateItems.length,
    certificatesReview: certificateItems.filter((item) => ['generated', 'quality_review'].includes(item.status)).length,
    certificatesApproved: certificateItems.filter((item) => item.status === 'approved').length,
    certificatesReleased: certificateItems.filter((item) => item.status === 'released').length
  };
}

export async function listClients() {
  return request('/clients');
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

export async function createQuotation(payload) {
  return request('/quotations', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function listQuotations() {
  return request('/quotations');
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

export async function changeServiceOrderStatus(serviceOrderId, action, comment = null) {
  return request(`/service-orders/${serviceOrderId}/${action}`, {
    method: 'POST',
    body: JSON.stringify({ comment })
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

export async function listCertificates(params = {}) {
  return request(`/certificates${buildQuery(params)}`);
}

export async function getCertificate(certificateId) {
  return request(`/certificates/${certificateId}`);
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
