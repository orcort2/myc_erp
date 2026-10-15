import React, { useEffect, useRef, useState } from 'react';
import {
  CheckCircle2,
  FileText,
  Mail,
  Paperclip,
  Send,
  ShieldCheck,
} from 'lucide-react';

import { previewInvoiceEmail, sendInvoiceEmail } from '../../services/api.js';
import {
  addManualRecipient,
  buildSendPayload,
  canSendEmail,
  createVersionGate,
  hasEmail,
  removeRecipient,
  selectInCc,
  selectInTo,
  sendResultMessage
} from '../../utils/quotationEmail.js';

const sourceLabels = {
  quotation_contact: 'Contacto de la cotización',
  client_contact: 'Contacto del cliente',
  client_email: 'Correo general del cliente'
};

function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return '';
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function RecipientField({ label, suggestions, selected, onToggle, manual, onAdd, inputLabel, blocked = [], disabled = false }) {
  const [value, setValue] = useState('');
  const [error, setError] = useState('');

  function add() {
    const result = onAdd(value);
    setError(result);
    if (!result) setValue('');
  }

  const rows = [
    ...suggestions.map((item) => ({ email: item.email, name: item.name, note: sourceLabels[item.source] ?? '' })),
    ...manual.map((email) => ({ email, name: '', note: 'Manual' }))
  ];

  return (
    <fieldset className="quotation-email__recipients" disabled={disabled}>
      <legend>{label}</legend>
      {rows.map((row) => {
        const inOtherList = hasEmail(blocked, row.email);
        return (
          <label className="quotation-email__recipient" key={row.email}>
            <input
              checked={hasEmail(selected, row.email)}
              disabled={inOtherList}
              onChange={() => onToggle(row.email)}
              type="checkbox"
            />
            <span className="quotation-email__recipient-text">
              <strong>{row.name || row.email}</strong>
              {row.name ? <span>{row.email}</span> : null}
              <small>{inOtherList ? 'Ya está en Para' : row.note}</small>
            </span>
          </label>
        );
      })}
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
// initialTo/initialCc preload the recipients of a previous attempt ("Reenviar"):
// the PDF and message are still regenerated and a NEW delivery is created.
function InvoiceEmailModal({ invoiceId, folio, onClose, onSent = () => {}, initialTo = null, initialCc = null }) {
  const [preview, setPreview] = useState(null);
  const [to, setTo] = useState([]);
  const [cc, setCc] = useState([]);
  const [manualTo, setManualTo] = useState([]);
  const [manualCc, setManualCc] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshingPreview, setIsRefreshingPreview] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [previewCurrent, setPreviewCurrent] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const gate = useRef(createVersionGate());

  useEffect(() => {
    let active = true;
    const version = gate.current.next();

    setPreview(null);
    setTo([]);
    setCc([]);
    setManualTo([]);
    setManualCc([]);
    setIsLoading(true);
    setIsRefreshingPreview(false);
    setIsSending(false);
    setPreviewCurrent(false);
    setError('');
    setResult(null);

    const request = initialTo?.length ? { to: initialTo, cc: initialCc ?? [] } : {};
    previewInvoiceEmail(invoiceId, request)
      .then((data) => {
        if (!active || !gate.current.isCurrent(version)) return;
        const known = data.available_recipients.map((item) => item.email);
        setPreview(data);
        setTo(data.to);
        setCc(data.cc);
        // Recipients from a previous attempt that are not suggestions are shown as manual ones.
        setManualTo(data.to.filter((email) => !hasEmail(known, email)));
        setManualCc(data.cc.filter((email) => !hasEmail(known, email)));
        setPreviewCurrent(true);
      })
      .catch((requestError) => {
        if (active && gate.current.isCurrent(version)) {
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (active && gate.current.isCurrent(version)) {
          setIsLoading(false);
        }
      });
    return () => {
      active = false;
      gate.current.invalidate();
    };
  }, [invoiceId]);

  // The message depends on the first TO recipient: refresh it, ignoring out-of-order answers.
  async function refreshPreview(nextTo, nextCc) {
    const version = gate.current.next();
    setPreviewCurrent(false);
    if (!nextTo.length) {
      setIsRefreshingPreview(false);
      setIsLoading(false);
      return;
    }
    setIsRefreshingPreview(true);
    try {
      const data = await previewInvoiceEmail(invoiceId, buildSendPayload(nextTo, nextCc));
      if (!gate.current.isCurrent(version)) return;
      setPreview((current) => ({ ...data, available_recipients: current?.available_recipients ?? data.available_recipients }));
      setError('');
      setPreviewCurrent(true);
    } catch (requestError) {
      if (!gate.current.isCurrent(version)) return;
      setError(requestError.message); // previewCurrent stays false: the old preview cannot be sent
    } finally {
      if (gate.current.isCurrent(version)) {
        setIsRefreshingPreview(false);
        setIsLoading(false);
      }
    }
  }

  function changeSelection(next) {
    setTo(next.to);
    setCc(next.cc);
    refreshPreview(next.to, next.cc);
  }

  // Manual addresses apply to this send only; they never create contacts or touch the client.
  function addRecipient(value, target) {
    const added = addManualRecipient(target === 'to' ? to : cc, value);
    if (added.error) return added.error;
    const known = (preview?.available_recipients ?? []).some((item) => hasEmail([item.email], value));
    if (!known) {
      const setManual = target === 'to' ? setManualTo : setManualCc;
      const manual = target === 'to' ? manualTo : manualCc;
      setManual(addManualRecipient(manual, value).list);
    }
    if (target === 'to') changeSelection(selectInTo(to, cc, value));
    else if (!hasEmail(to, value)) changeSelection(selectInCc(to, cc, value));
    return '';
  }

  function toggleTo(email) {
    if (hasEmail(to, email)) changeSelection({ to: removeRecipient(to, email), cc });
    else changeSelection(selectInTo(to, cc, email));
  }

  function toggleCc(email) {
    if (hasEmail(cc, email)) {
      changeSelection({ to, cc: removeRecipient(cc, email) });
    } else {
      changeSelection(selectInCc(to, cc, email));
    }
  }

  async function send() {
    if (!canSendEmail({ isLoading, isSending, isRefreshingPreview, previewCurrent, to })) return;
    const payload = buildSendPayload(to, cc);
    const version = gate.current.next();
    setError('');
    setIsSending(true);
    try {
      const outcome = await sendInvoiceEmail(invoiceId, payload);
      if (!gate.current.isCurrent(version)) return;
      setResult(outcome);
      onSent(outcome);
    } catch (requestError) {
      if (!gate.current.isCurrent(version)) return;
      setError(requestError.message);
    } finally {
      if (gate.current.isCurrent(version)) {
        setIsSending(false);
      }
    }
  }

  const suggestions = preview?.available_recipients ?? [];
  const isDraft = preview?.document_mode === 'draft';
  const canSend = canSendEmail({ isLoading, isSending, isRefreshingPreview, previewCurrent, to });

  return (
    <div className="modal-backdrop" role="presentation">
      <section aria-label={`Enviar factura ${folio}`} aria-modal="true" className="client-modal quotation-email-modal" role="dialog">
        <div className="client-modal-header quotation-email__header">
          <div className="quotation-email__heading">
            <span className="quotation-email__heading-icon">
              <Mail size={23} aria-hidden="true" />
            </span>
            <div>
              <p>COMUNICACIÓN COMERCIAL</p>
              <h2>Enviar factura</h2>
              <span className="quotation-email__folio">{folio}</span>
            </div>
          </div>
          <button aria-label="Cerrar" disabled={isSending} onClick={onClose} type="button">
            ×
          </button>
        </div>

        {error ? <div className="form-error">{error}</div> : null}

        {result ? (
          <section
            className={`quotation-email__result ${result.sent ? 'is-success' : 'is-error'}`}
            role="status"
            aria-live="polite"
          >
            <span className="quotation-email__result-icon">
              {result.sent
                ? <CheckCircle2 size={30} aria-hidden="true" />
                : <Mail size={30} aria-hidden="true" />}
            </span>
            <div>
              <h3>{result.sent ? 'Correo aceptado para envío' : 'No se pudo enviar el correo'}</h3>
              <p>{sendResultMessage(result)}</p>
              <p className="quotation-email__result-folio">
                Factura: <strong>{folio}</strong>
              </p>
              <p>Destinatarios: <strong>{to.join(', ')}</strong></p>
              {cc.length > 0 ? (
                <p>Con copia: <strong>{cc.join(', ')}</strong></p>
              ) : null}
              {result.delivery_id != null ? (
                <p className="quotation-email__result-id">
                  Registro de envío #{result.delivery_id}
                </p>
              ) : null}
              {result.sent ? (
                <p className="quotation-email__delivery-note">
                  La aceptación por el servidor SMTP no confirma
                  la entrega al buzón del destinatario.
                </p>
              ) : null}
            </div>
          </section>
        ) : preview ? (
          <>
            <div className="quotation-email__intro">
              <ShieldCheck size={19} aria-hidden="true" />
              <span>
                Envío institucional de MYC. Revisa los destinatarios
                y el documento antes de confirmar.
              </span>
            </div>

            <div className="quotation-email__section-heading">
              <span className="quotation-email__step">01</span>
              <div>
                <h3>Destinatarios</h3>
                <p>Selecciona a quién se enviará la factura.</p>
              </div>
            </div>

            <div className="quotation-email__compose-recipients">
              <RecipientField
                disabled={isSending}
                inputLabel="Agregar destinatario"
                label="Para"
                manual={manualTo}
                onAdd={(value) => addRecipient(value, 'to')}
                onToggle={toggleTo}
                selected={to}
                suggestions={suggestions}
              />
              <RecipientField
                blocked={to}
                disabled={isSending}
                inputLabel="Agregar copia"
                label="CC"
                manual={manualCc}
                onAdd={(value) => addRecipient(value, 'cc')}
                onToggle={toggleCc}
                selected={cc}
                suggestions={suggestions}
              />
            </div>

            <div className="quotation-email__section-heading">
              <span className="quotation-email__step">02</span>
              <div>
                <h3>Mensaje y documento</h3>
                <p>Vista previa del contenido generado por el ERP.</p>
              </div>
            </div>

            <section className="quotation-email__message" aria-busy={isRefreshingPreview}>
                <div>
                  <strong>
                    {isDraft
                      ? 'Documento preliminar sin validez fiscal'
                      : 'Factura con evidencia fiscal'}
                  </strong>
                  <p>
                    {isDraft
                      ? 'Se enviará únicamente el PDF institucional MYC. Este documento no es un CFDI timbrado.'
                      : 'Se enviarán el PDF institucional MYC y el XML fiscal.'}
                  </p>
                </div>
              <div>
                <span className="quotation-email__label">Asunto</span>
                <p className="quotation-email__subject">{preview.subject}</p>
              </div>
              <div>
                <span className="quotation-email__label">
                  Vista previa{isRefreshingPreview ? ' · actualizando…' : !previewCurrent ? ' · desactualizada' : ''}
                </span>
                {/* Backend-rendered HTML in a fully sandboxed frame: no scripts, read-only. */}
                <iframe className="quotation-email__frame" sandbox="" srcDoc={preview.body_html} title="Vista previa del mensaje" />
              </div>
              <div>
                <span className="quotation-email__label">
                  <Paperclip size={14} aria-hidden="true" />
                  Documentos adjuntos
                </span>
                {preview.attachments.map((file) => (
                  <div className="quotation-email__attachment" key={file.filename}>
                    <strong className="quotation-email__file-title">
                      <FileText size={17} aria-hidden="true" />
                        {file.content_type === 'application/xml'
                          ? 'XML fiscal'
                          : file.content_type === 'application/pdf'
                            ? 'PDF institucional MYC'
                            : 'Documento adjunto'}
                      </strong>
                    <span>
                      {file.filename}
                      {formatSize(file.size) ? ` · ${formatSize(file.size)}` : ''}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          </>
        ) : isLoading ? (
          <div className="clients-empty">Preparando vista previa…</div>
        ) : null}

        <div className="quotation-email__actions">
          <button className="table-button" disabled={isSending} onClick={onClose} type="button">
            {result ? 'Cerrar' : 'Cancelar'}
          </button>
          {!result && preview ? (
            <button className="primary-button" disabled={!canSend} onClick={send} type="button">
              <Send size={16} aria-hidden="true" />
              {isSending ? 'Enviando…' : 'Enviar factura'}
            </button>
          ) : null}
        </div>
      </section>
    </div>
  );
}

export default InvoiceEmailModal;
