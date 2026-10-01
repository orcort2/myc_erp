import React, { useEffect, useState } from 'react';

import {
  createClientContact,
  deactivateClientContact,
  listClientContacts,
  restoreClientContact,
  updateClientContact
} from '../services/api.js';

const emptyForm = { name: '', position: '', email: '', phone: '' };

// Contacts are people of the client, managed one by one (ids are kept: quotations reference them).
function ClientContactsPanel({ clientId, canEdit = true, onChanged = () => {} }) {
  const [contacts, setContacts] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    listClientContacts(clientId)
      .then((items) => active && setContacts(items))
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setIsLoading(false));
    return () => {
      active = false;
    };
  }, [clientId]);

  function openForm(contact = null) {
    setError('');
    setEditingId(contact?.id ?? null);
    setForm(
      contact
        ? { name: contact.name ?? '', position: contact.position ?? '', email: contact.email ?? '', phone: contact.phone ?? '' }
        : emptyForm
    );
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    setForm(emptyForm);
  }

  function replaceContact(saved) {
    const next = contacts.some((item) => item.id === saved.id)
      ? contacts.map((item) => (item.id === saved.id ? saved : item))
      : [...contacts, saved];
    setContacts(next);
    onChanged(next);
  }

  async function save() {
    if (!form.name.trim()) {
      setError('El nombre del contacto es obligatorio.');
      return;
    }
    setIsBusy(true);
    setError('');
    const payload = {
      name: form.name.trim(),
      position: form.position.trim() || null,
      email: form.email.trim() || null,
      phone: form.phone.trim() || null
    };
    try {
      const saved = editingId
        ? await updateClientContact(clientId, editingId, payload)
        : await createClientContact(clientId, payload);
      replaceContact(saved);
      closeForm();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsBusy(false);
    }
  }

  async function toggleActive(contact) {
    setIsBusy(true);
    setError('');
    try {
      const saved = contact.is_active
        ? await deactivateClientContact(clientId, contact.id)
        : await restoreClientContact(clientId, contact.id);
      replaceContact(saved);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <section className="client-contacts-panel" aria-label="Contactos del cliente">
      <div className="client-contacts-panel__intro">
        <div>
          <h3>Contactos</h3>
          <p>Personas de contacto de este cliente. El correo general del cliente se edita en Datos generales.</p>
        </div>
        {canEdit ? (
          <button className="primary-button" disabled={isBusy} onClick={() => openForm()} type="button">
            Nuevo contacto
          </button>
        ) : null}
      </div>

      {error ? <div className="form-error">{error}</div> : null}

      {isFormOpen ? (
        <div className="client-contacts-panel__form" role="group" aria-label={editingId ? 'Editar contacto' : 'Nuevo contacto'}>
          <label>
            Nombre
            <input onChange={(event) => setForm({ ...form, name: event.target.value })} type="text" value={form.name} />
          </label>
          <label>
            Puesto
            <input onChange={(event) => setForm({ ...form, position: event.target.value })} type="text" value={form.position} />
          </label>
          <label>
            Correo del contacto
            <input onChange={(event) => setForm({ ...form, email: event.target.value })} type="email" value={form.email} />
          </label>
          <label>
            Teléfono
            <input onChange={(event) => setForm({ ...form, phone: event.target.value })} type="text" value={form.phone} />
          </label>
          <div className="client-contacts-panel__form-actions">
            <button className="table-button" disabled={isBusy} onClick={closeForm} type="button">
              Cancelar
            </button>
            <button className="primary-button" disabled={isBusy} onClick={save} type="button">
              {isBusy ? 'Guardando...' : 'Guardar contacto'}
            </button>
          </div>
        </div>
      ) : null}

      {isLoading ? (
        <div className="clients-empty">Cargando contactos…</div>
      ) : contacts.length === 0 ? (
        <div className="clients-empty">Este cliente aún no tiene contactos registrados.</div>
      ) : (
        <ul className="client-contacts-panel__list">
          {contacts.map((contact) => (
            <li className={contact.is_active ? 'client-contact-card' : 'client-contact-card is-inactive'} key={contact.id}>
              <div className="client-contact-card__head">
                <strong>{contact.name}</strong>
                <mark className={contact.is_active ? 'status-active' : 'status-inactive'}>
                  {contact.is_active ? 'Activo' : 'Inactivo'}
                </mark>
              </div>
              <div className="client-contact-card__data">
                <span>{contact.position || 'Sin puesto'}</span>
                <span>{contact.email || 'Sin correo'}</span>
                <span>{contact.phone || 'Sin teléfono'}</span>
              </div>
              {canEdit ? (
                <div className="client-contact-card__actions">
                  <button className="table-button" disabled={isBusy} onClick={() => openForm(contact)} type="button">
                    Editar
                  </button>
                  <button className="table-button" disabled={isBusy} onClick={() => toggleActive(contact)} type="button">
                    {contact.is_active ? 'Desactivar' : 'Reactivar'}
                  </button>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default ClientContactsPanel;
