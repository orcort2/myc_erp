import React, { useEffect, useState } from 'react';

import {
  getQuotationServiceExceptionContext,
  listQuotationServiceExceptions,
  requestQuotationServiceChange,
  reviewQuotationServiceChange
} from '../../services/api.js';
import {
  canShowQuotationServiceException,
  canSelfAuthorizeQuotationUnlock,
  hasQuotationExceptionPermission
} from '../../utils/quotationServiceExceptions.js';
import './quotation-service-exceptions.css';


export function QuotationServiceExceptionAction({
  quotation,
  currentUser,
  onContextChange,
  onEnterExceptionalMode
}) {
  const [context, setContext] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [form, setForm] = useState({ reason: '', observation: '' });
  const [message, setMessage] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const canSelfAuthorize = canSelfAuthorizeQuotationUnlock(currentUser);

  async function loadContext() {
    if (!quotation?.folio || quotation.status !== 'accepted') {
      setContext(null);
      onContextChange?.(null);
      return;
    }
    try {
      const result = await getQuotationServiceExceptionContext(quotation.folio);
      setContext(result);
      onContextChange?.(result);
    } catch (error) {
      const result = { eligible: false, reason: error.message };
      setContext(result);
      onContextChange?.(result);
    }
  }

  useEffect(() => {
    loadContext();
  }, [quotation?.folio, quotation?.status]);

  async function submitRequest(event) {
    event.preventDefault();
    setMessage('');
    setIsSaving(true);
    try {
      const result = await requestQuotationServiceChange(quotation.folio, {
        reason: form.reason.trim(),
        observation: form.observation.trim() || null
      });
      setMessage(
        result.can_apply
          ? `${quotation.folio} desbloqueada mediante ${result.folio}.`
          : `Solicitud ${result.folio} enviada para autorización.`
      );
      setIsOpen(false);
      await loadContext();
      if (result.can_apply) onEnterExceptionalMode?.(result);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function authorizeExistingRequest() {
    const active = context?.active_request;
    if (!active) return;
    setMessage('');
    setIsSaving(true);
    try {
      const result = await reviewQuotationServiceChange(active.folio, {
        decision: 'authorize',
        comment: 'Autoautorización administrativa registrada.',
        validity_hours: 72
      });
      setMessage(`${quotation.folio} desbloqueada mediante ${result.folio}.`);
      await loadContext();
      if (result.can_apply) onEnterExceptionalMode?.(result);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsSaving(false);
    }
  }

  if (
    quotation?.status !== 'accepted' ||
    !canShowQuotationServiceException(quotation, currentUser)
  ) {
    return null;
  }

  const active = context?.active_request;
  return (
    <>
      {active?.can_apply ? (
        <button
          className="primary-button"
          onClick={() => onEnterExceptionalMode?.(active)}
          type="button"
        >
          Editar cotización desbloqueada
        </button>
      ) : active &&
        canSelfAuthorize &&
        active.can_review &&
        ['pending_review', 'information_required'].includes(active.status) ? (
        <button
          className="primary-button"
          disabled={isSaving}
          onClick={authorizeExistingRequest}
          type="button"
        >
          {isSaving ? 'Procesando…' : 'Autorizar y editar'}
        </button>
      ) : active ? (
        <span className="sales-exception-inline-status">
          {active.folio} · {active.status_label}
        </span>
      ) : (
        <button
          className="table-button"
          disabled={!context?.eligible}
          onClick={() => setIsOpen(true)}
          title={context?.reason || 'Solicitar desbloqueo controlado'}
          type="button"
        >
          Desbloquear cotización
        </button>
      )}
      {!active && context?.reason ? (
        <small className="sales-exception-inline-status">{context.reason}</small>
      ) : null}
      {message ? <span className="sales-exception-message">{message}</span> : null}

      {isOpen ? (
        <div className="sales-exception-dialog" role="dialog" aria-modal="true">
          <form onSubmit={submitRequest}>
            <div className="sales-exception-dialog__header">
              <div>
                <p>Excepción contextual</p>
                <h3>Desbloquear cotización</h3>
                <span>{quotation.folio} · {context?.service_order_folio}</span>
              </div>
              <button className="icon-text-button" onClick={() => setIsOpen(false)} type="button">
                Cerrar
              </button>
            </div>
            <div className="sales-exception-impact">
              <strong>{canSelfAuthorize ? 'Desbloqueo administrativo' : 'Alcance controlado'}</strong>
              <span>
                {canSelfAuthorize
                  ? 'Tu autoridad permite registrar el motivo y abrir inmediatamente la edición excepcional. La reconstrucción sólo procederá si el ETS continúa virgen.'
                  : 'La autorización habilita la edición directa de partidas y reconstruye el ETS únicamente si continúa sin información operativa.'}
              </span>
            </div>
            <label>
              Motivo
              <textarea
                required
                minLength={3}
                rows={3}
                value={form.reason}
                onChange={(event) => setForm((value) => ({ ...value, reason: event.target.value }))}
              />
            </label>
            <label>
              Observación opcional
              <textarea
                rows={2}
                value={form.observation}
                onChange={(event) => setForm((value) => ({ ...value, observation: event.target.value }))}
              />
            </label>
            <div className="toolbar-actions">
              <button className="table-button" onClick={() => setIsOpen(false)} type="button">
                Cancelar
              </button>
              <button className="primary-button" disabled={isSaving} type="submit">
                {isSaving
                  ? 'Procesando…'
                  : canSelfAuthorize
                    ? 'Registrar y desbloquear'
                    : 'Solicitar desbloqueo'}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </>
  );
}


export function QuotationServiceExceptionReview({ currentUser }) {
  const [items, setItems] = useState([]);
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [reviewing, setReviewing] = useState(null);
  const [review, setReview] = useState({ decision: 'authorize', comment: '', validityHours: '72' });

  async function load() {
    setIsLoading(true);
    try {
      setItems(await listQuotationServiceExceptions());
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submitReview(event) {
    event.preventDefault();
    if (!reviewing) return;
    try {
      await reviewQuotationServiceChange(reviewing.folio, {
        decision: review.decision,
        comment: review.comment.trim() || null,
        validity_hours: Number(review.validityHours || 72)
      });
      setMessage(`${reviewing.folio} actualizado.`);
      setReviewing(null);
      await load();
    } catch (error) {
      setMessage(error.message);
    }
  }

  if (!hasQuotationExceptionPermission(currentUser, 'quotations.exceptions.inspect')) {
    return <div className="empty-state">No tienes permiso para consultar excepciones.</div>;
  }

  return (
    <section className="sales-exception-review">
      <div className="section-heading">
        <div>
          <p>Autorización institucional</p>
          <h2>Desbloqueos de cotizaciones</h2>
          <span>Las referencias visibles son cotización, ETS y folio de excepción.</span>
        </div>
      </div>
      {message ? <div className="sales-exception-message">{message}</div> : null}
      {isLoading ? <div className="empty-state">Cargando solicitudes…</div> : null}
      {!isLoading && !items.length ? <div className="empty-state">No hay solicitudes registradas.</div> : null}
      <div className="sales-exception-list">
        {items.map((item) => (
          <article key={item.folio}>
            <header>
              <div>
                <strong>{item.folio}</strong>
                <span>{item.quotation_folio} · {item.service_order_folio}</span>
              </div>
              <mark>{item.status_label}</mark>
            </header>
            <dl>
              <div><dt>Cliente</dt><dd>{item.client_name}</dd></div>
              <div><dt>Revisión base</dt><dd>{item.base_snapshot_number}</dd></div>
              <div><dt>Solicitó</dt><dd>{item.requester_name}</dd></div>
              <div><dt>ETS</dt><dd>{item.service_order_status}</dd></div>
              <div><dt>Motivo</dt><dd>{item.reason}</dd></div>
              <div>
                <dt>Dependencias</dt>
                <dd>{item.dependencies.length ? item.dependencies.map((entry) => entry.label).join(', ') : 'Ninguna'}</dd>
              </div>
            </dl>
            {item.can_review && ['pending_review', 'information_required'].includes(item.status) ? (
              <button className="primary-button" onClick={() => setReviewing(item)} type="button">
                Revisar solicitud
              </button>
            ) : null}
          </article>
        ))}
      </div>
      {reviewing ? (
        <div className="sales-exception-dialog" role="dialog" aria-modal="true">
          <form onSubmit={submitReview}>
            <div className="sales-exception-dialog__header">
              <div><p>{reviewing.folio}</p><h3>Revisar desbloqueo</h3></div>
              <button className="icon-text-button" onClick={() => setReviewing(null)} type="button">Cerrar</button>
            </div>
            <label>
              Decisión
              <select value={review.decision} onChange={(event) => setReview((value) => ({ ...value, decision: event.target.value }))}>
                <option value="authorize">Autorizar</option>
                <option value="request_information">Solicitar información</option>
                <option value="reject">Rechazar</option>
              </select>
            </label>
            {review.decision === 'authorize' ? (
              <label>
                Vigencia en horas
                <input min="1" max="168" type="number" value={review.validityHours} onChange={(event) => setReview((value) => ({ ...value, validityHours: event.target.value }))} />
              </label>
            ) : null}
            <label>
              Comentario
              <textarea required={review.decision !== 'authorize'} rows={3} value={review.comment} onChange={(event) => setReview((value) => ({ ...value, comment: event.target.value }))} />
            </label>
            <button className="primary-button" type="submit">Guardar decisión</button>
          </form>
        </div>
      ) : null}
    </section>
  );
}
