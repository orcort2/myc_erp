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

// Ordered-request guard: only the latest request may write state ("what you see is what is sent").
export function createVersionGate() {
  let version = 0;
  return {
    next: () => ++version,
    invalidate: () => ++version,
    isCurrent: (candidate) => candidate === version
  };
}

// Send is possible only when the shown preview belongs to the CURRENT selection.
export function canSendEmail({ isLoading, isSending, isRefreshingPreview, previewCurrent, to }) {
  return !isLoading && !isSending && !isRefreshingPreview && previewCurrent && to.length > 0;
}

// An address lives in TO or in CC, never both: TO wins.
export function selectInTo(to, cc, email) {
  const nextTo = hasEmail(to, email) ? to : [...to, normalizeEmail(email)];
  return { to: nextTo, cc: cc.filter((item) => normalizeEmail(item).toLowerCase() !== normalizeEmail(email).toLowerCase()) };
}

export function selectInCc(to, cc, email) {
  if (hasEmail(to, email)) return { to, cc };
  return { to, cc: hasEmail(cc, email) ? cc : [...cc, normalizeEmail(email)] };
}

export function removeRecipient(list, email) {
  return list.filter((item) => normalizeEmail(item).toLowerCase() !== normalizeEmail(email).toLowerCase());
}
