import { normalizeKey } from './formatters.js';
export function getClientContact(client) {
  return client.contacts?.find((contact) => contact.is_active !== false) ?? client.contacts?.[0];
}

export function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export function validateClientForm(form) {
  const errors = {};

  if (!form.commercialName.trim()) {
    errors.commercialName = 'El nombre comercial es obligatorio.';
  }

  if (!form.rfc.trim()) {
    errors.rfc = 'El RFC es obligatorio.';
  }

  if (form.email.trim() && !isValidEmail(form.email.trim())) {
    errors.email = 'Captura un correo valido.';
  }

  if (form.postalCode.trim() && !/^\d+$/.test(form.postalCode.trim())) {
    errors.postalCode = 'El codigo postal solo debe contener numeros.';
  }

  if (form.fiscalPostalCode.trim() && !/^\d+$/.test(form.fiscalPostalCode.trim())) {
    errors.fiscalPostalCode = 'El codigo postal fiscal solo debe contener numeros.';
  }

  return errors;
}

export function getFirstValidationTab(errors) {
  if (errors.commercialName || errors.rfc || errors.email) {
    return 'general';
  }
  if (errors.postalCode) {
    return 'address';
  }
  if (errors.fiscalPostalCode) {
    return 'fiscal';
  }
  return 'general';
}

export function toClientPayload(form) {
  const legalName = form.fiscalLegalName.trim() || form.commercialName.trim();
  const rfc = form.fiscalRfc.trim() || form.rfc.trim();
  const payload = {
    legal_name: legalName,
    commercial_name: form.commercialName.trim() || null,
    rfc: rfc || null,
    phone: form.phone.trim() || null,
    email: form.email.trim() || null,
    tax_regime: form.taxRegime.trim() || null
  };

  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined)
  );
}

export function toClientCreatePayload(form) {
  const contactName = form.contactName.trim();
  return {
    ...toClientPayload(form),
    contacts: contactName
      ? [
          {
            name: contactName,
            email: form.email.trim() || null,
            phone: form.phone.trim() || null
          }
        ]
      : []
  };
}

export function buildClientImportPreview(rows, existingClients) {
  const existingRfc = new Set(existingClients.map((client) => normalizeKey(client.rfc)).filter(Boolean));
  const existingEmail = new Set(existingClients.map((client) => normalizeKey(client.email)).filter(Boolean));
  const existingName = new Set(
    existingClients.map((client) => normalizeKey(client.commercial_name || client.legal_name)).filter(Boolean)
  );

  const seenRfc = new Set();
  const seenEmail = new Set();
  const seenName = new Set();

  const reviewedRows = rows.map((row, index) => {
    const name = row['Nombre comercial'] || row.nombre || row.Cliente || '';
    const rfc = row.RFC || row.rfc || '';
    const email = row.Correo || row.Email || row.email || '';
    const postalCode = row['Codigo postal'] || row['Código postal'] || '';
    const nameKey = normalizeKey(name);
    const rfcKey = normalizeKey(rfc);
    const emailKey = normalizeKey(email);
    const errors = [];
    const duplicates = [];

    if (!name.trim()) {
      errors.push('Nombre comercial obligatorio');
    }
    if (email.trim() && !isValidEmail(email.trim())) {
      errors.push('Correo invalido');
    }
    if (postalCode.trim() && !/^\d+$/.test(postalCode.trim())) {
      errors.push('Codigo postal no numerico');
    }
    if (rfcKey && (existingRfc.has(rfcKey) || seenRfc.has(rfcKey))) {
      duplicates.push('RFC');
    }
    if (emailKey && (existingEmail.has(emailKey) || seenEmail.has(emailKey))) {
      duplicates.push('Correo');
    }
    if (nameKey && (existingName.has(nameKey) || seenName.has(nameKey))) {
      duplicates.push('Nombre');
    }

    if (rfcKey) seenRfc.add(rfcKey);
    if (emailKey) seenEmail.add(emailKey);
    if (nameKey) seenName.add(nameKey);

    return {
      id: `${index}-${nameKey || 'cliente'}`,
      name: name || '-',
      rfc: rfc || '-',
      email: email || '-',
      status: errors.length ? 'error' : duplicates.length ? 'duplicate' : 'valid',
      errors,
      duplicates,
      raw: row
    };
  });

  return {
    rows: reviewedRows,
    valid: reviewedRows.filter((row) => row.status === 'valid'),
    duplicates: reviewedRows.filter((row) => row.status === 'duplicate'),
    errors: reviewedRows.filter((row) => row.status === 'error')
  };
}
export function getRowValue(row, names) {
  const entries = Object.entries(row).map(([key, value]) => [normalizeKey(key), value]);
  for (const name of names) {
    const match = entries.find(([key]) => key === normalizeKey(name));
    if (match) {
      return match[1] ?? '';
    }
  }
  return '';
}