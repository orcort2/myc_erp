export function formatDate(value) {
  if (!value) {
    return '-';
  }
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium'
  }).format(new Date(`${value}T00:00:00`));
}

export function formatDateTime(value) {
  if (!value) {
    return '-';
  }
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value));
}

export function formatMoney(value) {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat('es-MX', {
    currency: 'MXN',
    style: 'currency'
  }).format(amount);
}

export function normalizeKey(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');
}

export function getClientDisplayName(client) {
  return client?.commercial_name || client?.legal_name || 'Cliente sin nombre';
}

export function getClientAddress(client) {
  if (!client) return '';
  return [
    client.street,
    client.exterior_number,
    client.interior_number,
    client.neighborhood,
    client.locality,
    client.municipality,
    client.city,
    client.state,
    client.postal_code,
    client.country,
  ].map((value) => String(value || '').trim()).filter(Boolean).join(', ');
}

export function formatModuleDateTime(date) {
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(date);
}
