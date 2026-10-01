// Pure helpers for the quotation "main contact" selector (EMAIL-3).
// The person's data lives in ClientContact; the quotation only stores contact_id.

export function contactLabel(contact) {
  return [contact.name, contact.position, contact.email].filter(Boolean).join(' · ');
}

// Active contacts of the selected client, plus the currently assigned one when it
// was deactivated later (so history stays readable and the select does not blank).
export function contactOptionsForClient(client, selectedContactId = '') {
  const contacts = Array.isArray(client?.contacts) ? client.contacts : [];
  const selected = String(selectedContactId ?? '');
  return contacts
    .filter((contact) => contact.is_active !== false || String(contact.id) === selected)
    .map((contact) => ({
      value: String(contact.id),
      label: contact.is_active === false ? `${contactLabel(contact)} (inactivo)` : contactLabel(contact)
    }));
}

// A contact belongs to exactly one client: switching client always clears a stale selection.
export function contactIdAfterClientChange(nextClient, currentContactId) {
  const contacts = Array.isArray(nextClient?.contacts) ? nextClient.contacts : [];
  const stillValid = contacts.some(
    (contact) => String(contact.id) === String(currentContactId) && contact.is_active !== false
  );
  return stillValid ? String(currentContactId) : '';
}

export function contactIdPayload(value) {
  return value ? Number(value) : null;
}
