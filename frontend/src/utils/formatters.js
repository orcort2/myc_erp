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

export function formatModuleDateTime(date) {
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(date);
}

