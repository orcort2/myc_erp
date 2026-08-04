export const QUOTATION_STATUS = {
  sent: { label: 'Enviada', tone: 'info' },
  waiting: { label: 'En espera de respuesta', tone: 'warning' },
  accepted: { label: 'Aceptada', tone: 'success' },
};

export const SERVICE_STATUS = {
  scheduled: { label: 'Programado', tone: 'info', progress: 10 },
  confirmed: { label: 'Confirmado', tone: 'info', progress: 20 },
  called: { label: 'Técnico en camino', tone: 'warning', progress: 30 },
  in_progress: { label: 'Servicio en proceso', tone: 'warning', progress: 45 },
  technical_review: { label: 'En procesamiento técnico', tone: 'info', progress: 60 },
  capture: { label: 'En preparación documental', tone: 'info', progress: 70 },
  quality_review: { label: 'En revisión de calidad', tone: 'warning', progress: 80 },
  pending_payment: { label: 'Pendiente administrativo', tone: 'warning', progress: 88 },
  released: { label: 'Documentación disponible', tone: 'success', progress: 96 },
  closed: { label: 'Finalizado', tone: 'success', progress: 100 },
};

export const CERTIFICATE_STATUS = {
  authenticated: { label: 'Autenticado', tone: 'success' },
  released_to_client: { label: 'Disponible', tone: 'success' },
  released: { label: 'Disponible', tone: 'success' },
};

export function presentationFor(map, value, fallback = 'En proceso') {
  return map[value] ?? { label: fallback, tone: 'neutral' };
}

export function formatPortalDate(value) {
  if (!value) return 'Sin fecha';
  const date = new Date(`${value}`.length === 10 ? `${value}T12:00:00` : value);
  if (Number.isNaN(date.getTime())) return 'Sin fecha';
  return new Intl.DateTimeFormat('es-MX', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

export function formatPortalCurrency(value, currency = 'MXN') {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: currency || 'MXN',
  }).format(Number.isFinite(amount) ? amount : 0);
}
