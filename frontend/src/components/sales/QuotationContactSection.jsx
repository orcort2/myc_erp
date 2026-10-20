import { Mail, MessagesSquare, Phone } from 'lucide-react';
import React, { useState } from 'react';

import { createCommunicationConversation } from '../../services/api.js';
import { navigate } from '../../utils/routing.js';
import {
  buildQuotationContact,
  communicationsConversationPath
} from '../../utils/quotationContact.js';

/**
 * Contacto asociado a la cotización (contact_id). Nunca elige uno por omisión.
 *
 * "Abrir en Comunicaciones" reutiliza POST /communications/conversations (tipo
 * client), que busca la conversación existente del cliente antes de crear otra.
 * Es una conversación INTERNA del ERP sobre el cliente: no se entrega al contacto
 * externo. El envío real al contacto es el correo de la cotización.
 */
export default function QuotationContactSection({ quotation, client, canOpenCommunications }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const contact = buildQuotationContact(quotation, client);

  async function openInCommunications() {
    setBusy(true);
    setError('');
    try {
      const conversation = await createCommunicationConversation({
        conversation_type: 'client',
        client_id: quotation.client_id
      });
      const path = communicationsConversationPath(conversation);
      if (path) navigate(path);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="quotation-section" aria-label="Contacto de la cotización">
      <div className="quotation-section__title">
        <p>Contacto</p>
        <h3>Contacto de la cotización</h3>
      </div>
      {contact ? (
        <div className="quotation-contact-card">
          <dl>
            <div><dt>Nombre</dt><dd>{contact.name || 'Sin nombre'}</dd></div>
            <div><dt>Cargo</dt><dd>{contact.position || 'Sin cargo'}</dd></div>
            <div><dt>Correo</dt><dd>{contact.email || 'Sin correo'}</dd></div>
            <div><dt>Teléfono</dt><dd>{contact.phone || 'Sin teléfono'}</dd></div>
            <div><dt>Empresa</dt><dd>{contact.company || 'Sin empresa'}</dd></div>
          </dl>
          <div className="quotation-contact-card__actions">
            {contact.tel ? (
              <a className="table-button" href={contact.tel}><Phone size={15} /> Llamar</a>
            ) : null}
            {contact.mailto ? (
              <a className="table-button" href={contact.mailto}><Mail size={15} /> Correo</a>
            ) : null}
            {canOpenCommunications ? (
              <button className="table-button" disabled={busy} onClick={openInCommunications} type="button">
                <MessagesSquare size={15} /> {busy ? 'Abriendo…' : 'Abrir en Comunicaciones'}
              </button>
            ) : null}
          </div>
          {canOpenCommunications ? (
            <small className="quotation-contact-card__note">
              Abre la conversación interna del cliente en Comunicaciones; el contacto externo no la recibe.
              Para enviarle la cotización usa «Enviar por correo».
            </small>
          ) : null}
          {error ? <small role="alert" className="form-error">{error}</small> : null}
        </div>
      ) : (
        <div className="client-fiscal-note">
          Esta cotización no tiene un contacto asociado. Elige uno en «Contacto de la cotización» de la ficha editable.
        </div>
      )}
    </section>
  );
}
