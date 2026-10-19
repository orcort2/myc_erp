// Presentación del contacto asociado a la cotización (sin selección implícita).

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validEmail(value) {
  const email = String(value || '').trim();
  return EMAIL_PATTERN.test(email) ? email : null;
}

export function phoneHref(value) {
  const raw = String(value || '').trim();
  const digits = raw.replace(/[^\d+]/g, '');
  const onlyDigits = digits.replace(/\+/g, '');
  if (onlyDigits.length < 7) return null;
  return `tel:${digits.startsWith('+') ? '+' : ''}${onlyDigits}`;
}

export function buildQuotationContact(quotation, client) {
  if (!quotation?.contact_id) return null;
  return {
    name: quotation.contact_name || null,
    position: quotation.contact_position || null,
    email: quotation.contact_email || null,
    phone: quotation.contact_phone || null,
    company: client?.commercial_name || client?.legal_name || null,
    mailto: validEmail(quotation.contact_email)
      ? `mailto:${validEmail(quotation.contact_email)}`
      : null,
    tel: phoneHref(quotation.contact_phone),
  };
}

export function communicationsConversationPath(conversation) {
  return conversation?.id ? `/communications?conversation_id=${conversation.id}` : null;
}
