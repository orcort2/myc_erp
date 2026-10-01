// Pure recipient/result helpers for the quotation email modal (EMAIL-3).
// The backend validates and deduplicates again: this only improves the UX.

const EMAIL_PATTERN = /^[^\s@,;<>]+@[^\s@,;<>]+\.[^\s@,;<>]{2,}$/;

export function normalizeEmail(value) {
  return String(value ?? '').trim();
}

export function isValidEmail(value) {
  return EMAIL_PATTERN.test(normalizeEmail(value));
}

export function hasEmail(list, email) {
  const key = normalizeEmail(email).toLowerCase();
  return list.some((item) => normalizeEmail(item).toLowerCase() === key);
}

// Adds a manual address; returns { list, error }. Duplicates are ignored (case-insensitive).
export function addManualRecipient(list, value) {
  const email = normalizeEmail(value);
  if (!isValidEmail(email)) {
    return { list, error: 'Escribe una dirección de correo válida.' };
  }
  if (hasEmail(list, email)) {
    return { list, error: '' };
  }
  return { list: [...list, email], error: '' };
}

export function toggleRecipient(list, email) {
  return hasEmail(list, email)
    ? list.filter((item) => normalizeEmail(item).toLowerCase() !== normalizeEmail(email).toLowerCase())
    : [...list, email];
}

// TO wins over CC; only recipients can be sent (never subject/body/html/files).
export function buildSendPayload(to, cc) {
  const toKeys = new Set(to.map((item) => normalizeEmail(item).toLowerCase()));
  const uniqueCc = [];
  for (const item of cc) {
    const key = normalizeEmail(item).toLowerCase();
    if (!toKeys.has(key) && !hasEmail(uniqueCc, item)) uniqueCc.push(normalizeEmail(item));
  }
  const uniqueTo = [];
  for (const item of to) if (!hasEmail(uniqueTo, item)) uniqueTo.push(normalizeEmail(item));
  return { to: uniqueTo, cc: uniqueCc };
}

// SMTP accepted != delivered/read: never claim the client received it.
export function sendResultMessage(result) {
  return result?.sent
    ? 'El relay aceptó el correo para envío.'
    : 'No fue posible enviar el correo.';
}

export const emailStatusLabels = {
  pending: 'Pendiente',
  sending: 'Enviando',
  sent: 'Aceptado por el relay',
  failed: 'Fallido'
};
