import React, { useEffect, useState } from 'react';

import { previewQuotationEmail, sendQuotationEmail } from '../services/api.js';
import {
  addManualRecipient,
  buildSendPayload,
  hasEmail,
  sendResultMessage,
  toggleRecipient
} from '../utils/quotationEmail.js';

const sourceLabels = {
  quotation_contact: 'Contacto de la cotización',
  client_contact: 'Contacto del cliente',
  client_email: 'Correo general del cliente'
};

function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return '';
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function RecipientField({ label, suggestions, selected, onToggle, manual, onAdd, inputLabel }) {
  const [value, setValue] = useState('');
  const [error, setError] = useState('');

  function add() {
    const result = onAdd(value);
    setError(result);
    if (!result) setValue('');
  }

  return (
    <fieldset className="quotation-email__recipients">
      <legend>{label}</legend>
      {suggestions.map((item) => (
        <label className="quotation-email__recipient" key={item.email}>
          <input checked={hasEmail(selected, item.email)} onChange={() => onToggle(item.email)} type="checkbox" />
          <span className="quotation-email__recipient-text">
            <strong>{item.name || item.email}</strong>
            {item.name ? <span>{item.email}</span> : null}
            <small>{sourceLabels[item.source] ?? ''}</small>
          </span>
        </label>
      ))}
      {manual.map((email) => (
        <label className="quotation-email__recipient" key={email}>
          <input checked={hasEmail(selected, email)} onChange={() => onToggle(email)} type="checkbox" />
          <span className="quotation-email__recipient-text">
            <strong>{email}</strong>
            <small>Manual</small>
          </span>
        </label>
      ))}
      <div className="quotation-email__manual">
        <input
          aria-label={inputLabel}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              add();
            }
          }}
          placeholder="otro@empresa.com"
          type="email"
          value={value}
        />
        <button className="table-button" onClick={add} type="button">
          + Agregar
        </button>
      </div>
      {error ? <span className="field-error">{error}</span> : null}
    </fieldset>
  );
}

// Preview and send are both backend-built; this modal only chooses TO/CC.
function QuotationEmailModal({ quotationId, folio, onClose, onSent = () => {} }) {
  const [preview, setPreview] = useState(null);
  const [to, setTo] = useState([]);
  const [cc, setCc] = useState([]);
  const [manualTo, setManualTo] = useState([]);
  const [manualCc, setManualCc] = useState([]);
  const [isBusy, setIsBusy] = useState(true);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    let active = true;
    previewQuotationEmail(quotationId)
      .then((data) => {
        if (!active) return;
        setPreview(data);
        setTo(data.to);
        setCc(data.cc);
      })
      .catch((requestError) => active && setError(requestError.message))
      .finally(() => active && setIsBusy(false));
    return () => {
      active = false;
    };
  }, [quotationId]);

  // The rendered message depends on the first TO recipient (contact name): refresh it from the backend.
  async function refreshPreview(nextTo, nextCc) {
    if (!nextTo.length) return;
    try {
      const data = await previewQuotationEmail(quotationId, buildSendPayload(nextTo, nextCc));
      setPreview((current) => ({ ...data, available_recipients: current?.available_recipients ?? data.available_recipients }));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function updateTo(next) {
    setTo(next);
    refreshPreview(next, cc);
  }

  // Manual addresses apply to this send only; they never create contacts or touch the client.
  function addRecipient(value, { manual, setManual, list, apply }) {
    const added = addManualRecipient(list, value);
    if (added.error) return added.error;
    const known = (preview?.available_recipients ?? []).some((item) => hasEmail([item.email], value));
    if (!known) setManual(addManualRecipient(manual, value).list);
    apply(added.list);
    return '';
  }

  async function send() {
    const payload = buildSendPayload(to, cc);
    if (!payload.to.length) {
      setError('Selecciona al menos un destinatario en PARA.');
      return;
    }
    setError('');
    setIsBusy(true);
    try {
      const outcome = await sendQuotationEmail(quotationId, payload);
      setResult(outcome);
      onSent(outcome);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsBusy(false);
    }
  }

  const suggestions = preview?.available_recipients ?? [];

  return (
    <div className="modal-backdrop" role="presentation">
      <section aria-label={`Enviar cotización ${folio}`} aria-modal="true" className="client-modal quotation-email-modal" role="dialog">
        <div className="client-modal-header">
          <div>
            <p>Correo</p>
            <h2>Enviar cotización {folio}</h2>
          </div>
          <button aria-label="Cerrar" disabled={isBusy} onClick={onClose} type="button">
            ×
          </button>
        </div>

        {error ? <div className="form-error">{error}</div> : null}

        {result ? (
          <div className={result.sent ? 'form-notice' : 'form-error'}>{sendResultMessage(result)}</div>
        ) : preview ? (
          <div className="quotation-email__layout">
            <div className="quotation-email__column">
              <RecipientField
                inputLabel="Agregar destinatario"
                label="Para"
                manual={manualTo}
                onAdd={(value) => addRecipient(value, { manual: manualTo, setManual: setManualTo, list: to, apply: updateTo })}
                onToggle={(email) => updateTo(toggleRecipient(to, email))}
                selected={to}
                suggestions={suggestions}
              />
              <RecipientField
                inputLabel="Agregar copia"
                label="CC"
                manual={manualCc}
                onAdd={(value) => addRecipient(value, { manual: manualCc, setManual: setManualCc, list: cc, apply: setCc })}
                onToggle={(email) => setCc(toggleRecipient(cc, email))}
                selected={cc}
                suggestions={suggestions}
              />
            </div>

            <div className="quotation-email__column quotation-email__message">
              <div>
                <span className="quotation-email__label">Asunto</span>
                <p className="quotation-email__subject">{preview.subject}</p>
              </div>
              <div>
                <span className="quotation-email__label">Vista previa</span>
                {/* Backend-rendered HTML in a fully sandboxed frame: no scripts, read-only. */}
                <iframe className="quotation-email__frame" sandbox="" srcDoc={preview.body_html} title="Vista previa del mensaje" />
              </div>
              <div>
                <span className="quotation-email__label">Adjunto</span>
                {preview.attachments.map((file) => (
                  <div className="quotation-email__attachment" key={file.filename}>
                    <strong>PDF oficial</strong>
                    <span>
                      {file.filename}
                      {formatSize(file.size) ? ` · ${formatSize(file.size)}` : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : isBusy ? (
          <div className="clients-empty">Preparando vista previa…</div>
        ) : null}

        <div className="quotation-email__actions">
          <button className="table-button" disabled={isBusy} onClick={onClose} type="button">
            {result ? 'Cerrar' : 'Cancelar'}
          </button>
          {!result && preview ? (
            <button className="primary-button" disabled={isBusy || to.length === 0} onClick={send} type="button">
              {isBusy ? 'Enviando…' : 'Enviar'}
            </button>
          ) : null}
        </div>
      </section>
    </div>
  );
}

export default QuotationEmailModal;
