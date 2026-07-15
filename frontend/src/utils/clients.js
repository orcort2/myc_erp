import { normalizeKey } from './formatters.js';
export function getClientContact(client) {
  return client.contacts?.find((contact) => contact.is_active !== false) ?? client.contacts?.[0];
}

export function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export function validateClientForm(form) {
  const errors = {};

  if (!form.clientType) {
    errors.clientType = 'Selecciona el tipo de cliente.';
  }

  if (!form.rfc.trim()) {
    errors.rfc = 'El RFC es obligatorio.';
  }

  if (form.clientType === 'persona_fisica') {
    if (!form.firstName.trim()) {
      errors.firstName = 'El nombre es obligatorio.';
    }
    if (!form.firstLastName.trim()) {
      errors.firstLastName = 'El primer apellido es obligatorio.';
    }
  } else if (!form.legalName.trim()) {
    errors.legalName = 'La razon social es obligatoria.';
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
  if (errors.clientType || errors.legalName || errors.firstName || errors.firstLastName || errors.rfc || errors.email) {
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
  const legalName =
    form.clientType === 'persona_fisica'
      ? [form.firstName.trim(), form.firstLastName.trim(), form.secondLastName.trim()].filter(Boolean).join(' ')
      : form.legalName.trim() || form.fiscalLegalName.trim() || form.commercialName.trim();
  const rfc = form.fiscalRfc.trim() || form.rfc.trim();
  const contactName = form.contactName.trim();
  const payload = {
    client_type: form.clientType,
    legal_name: legalName,
    commercial_name: form.commercialName.trim() || null,
    rfc: rfc || null,
    curp: form.curp.trim() || null,
    first_name: form.firstName.trim() || null,
    first_last_name: form.firstLastName.trim() || null,
    second_last_name: form.secondLastName.trim() || null,
    phone: form.phone.trim() || null,
    email: form.email.trim() || null,
    tax_regime: form.taxRegime.trim() || null,
    cfdi_use: form.cfdiUse.trim() || null,
    street_type: form.streetType.trim() || null,
    street: form.street.trim() || null,
    exterior_number: form.exteriorNumber.trim() || null,
    interior_number: form.interiorNumber.trim() || null,
    neighborhood: form.neighborhood.trim() || null,
    locality: form.locality.trim() || null,
    municipality: form.municipality.trim() || form.city.trim() || null,
    city: form.city.trim() || form.municipality.trim() || null,
    state: form.addressState.trim() || null,
    postal_code: form.postalCode.trim() || null,
    country: form.country.trim() || null,
    fiscal_country_code: form.fiscalCountryCode.trim() || null,
    fiscal_postal_code: form.fiscalPostalCode.trim() || null,
    contacts: contactName
      ? [
          {
            name: contactName,
            email: form.email.trim() || null,
            phone: form.phone.trim() || null,
            position: null
          }
        ]
      : []
  };

  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined)
  );
}

export function toClientCreatePayload(form) {
  return toClientPayload(form);
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
    const name = row.nombre_comercial || row['Nombre comercial'] || row.nombre || row.Cliente || '';
    const legalName = row.razon_social || row['Razón social'] || row['Razon social'] || '';
    const personName = [row.nombres, row.primer_apellido, row.segundo_apellido].filter(Boolean).join(' ');
    const rfc = row.rfc || row.RFC || '';
    const email = row.correo || row.Correo || row.Email || row.email || '';
    const postalCode = row.codigo_postal || row['Codigo postal'] || row['Código postal'] || '';
    const nameKey = normalizeKey(name || legalName || personName);
    const rfcKey = normalizeKey(rfc);
    const emailKey = normalizeKey(email);
    const errors = [];
    const duplicates = [];

    if (!(name || legalName || personName).trim()) {
      errors.push('Nombre comercial, razon social o nombre completo obligatorios');
    }
    if (!rfc.trim()) {
      errors.push('RFC obligatorio');
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
      name: name || legalName || personName || '-',
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
