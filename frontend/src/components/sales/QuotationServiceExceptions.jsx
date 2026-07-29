import React, { useEffect, useMemo, useState } from 'react';

import {
  applyQuotationServiceChange,
  getQuotationServiceExceptionContext,
  listQuotationServiceExceptions,
  requestQuotationServiceChange,
  reviewQuotationServiceChange
} from '../../services/api.js';
import {
  canShowQuotationServiceException,
  formatQuotationServiceOption,
  hasQuotationExceptionPermission
} from '../../utils/quotationServiceExceptions.js';
import './quotation-service-exceptions.css';


export function QuotationServiceExceptionAction({
  quotation,
  catalogItems,
  currentUser,
  onApplied
}) {
  const [context, setContext] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [form, setForm] = useState({
    quotationLineNumber: '',
    requestedServiceKey: '',
    reason: '',
    observation: ''
  });
  const [message, setMessage] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const activeItems = useMemo(
    () => (quotation?.items || []).filter((item) => item.is_active !== false && item.catalog_item_id),
    [quotation]
  );
  const selectedItem = activeItems[Number(form.quotationLineNumber) - 1];
  const requestedItem = catalogItems.find(
    (item) => item.internalKey === form.requestedServiceKey
  );
  const selectableServices = catalogItems.filter(
    (item) =>
      item.status === 'Activo' &&
      item.itemType === 'service' &&
      item.internalKey &&
      String(item.id) !== String(selectedItem?.catalog_item_id)
  );

  async function loadContext() {
    if (!quotation?.folio || quotation.status !== 'accepted') {
      setContext(null);
      return;
    }
    try {
      setContext(await getQuotationServiceExceptionContext(quotation.folio));
    } catch (error) {
      setContext({ eligible: false, reason: error.message });
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
        quotation_line_number: Number(form.quotationLineNumber),
        requested_service_key: form.requestedServiceKey,
        reason: form.reason.trim(),
        observation: form.observation.trim() || null
      });
      setMessage(`Solicitud ${result.folio} enviada para autorización.`);
      setIsOpen(false);
      await loadContext();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function applyAuthorized() {
    setMessage('');
    setIsSaving(true);
    try {
      const result = await applyQuotationServiceChange(context.active_request.folio);
      setMessage(
        `${result.folio} aplicada. ${result.quotation_folio} y ${result.service_order_folio} fueron sincronizados.`
      );
      await loadContext();
      await onApplied?.();
    } catch (error) {
      setMessage(error.message);
      await loadContext();
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
    <section className="sales-exception-card">
      <div>
        <p>Excepciones</p>
        <h3>Cambiar tipo de servicio</h3>
        <span>
          {context?.service_order_folio
            ? `Cotización ${quotation.folio} · ETS ${context.service_order_folio}`
            : `Cotización ${quotation.folio}`}
        </span>
      </div>

      {active ? (
        <div className="sales-exception-active">
          <strong>{active.folio} · {active.status_label}</strong>
          <span>{active.current_service_name} → {active.requested_service_name}</span>
          {active.expires_at ? (
            <small>Vigencia: {new Date(active.expires_at).toLocaleString('es-MX')}</small>
          ) : null}
          {active.can_apply ? (
            <button
              className="primary-button"
              disabled={isSaving}
              onClick={applyAuthorized}
              type="button"
            >
              Aplicar cambio autorizado
            </button>
          ) : null}
        </div>
      ) : (
        <button
          className="table-button"
          disabled={!context?.eligible}
          onClick={() => setIsOpen(true)}
          title={context?.reason || 'Solicitar cambio limitado de servicio'}
          type="button"
        >
          Cambiar tipo de servicio
        </button>
      )}

      {!active && context?.reason ? <small>{context.reason}</small> : null}
      {message ? <div className="sales-exception-message">{message}</div> : null}

      {isOpen ? (
        <div className="sales-exception-dialog" role="dialog" aria-modal="true">
          <form onSubmit={submitRequest}>
            <div className="sales-exception-dialog__header">
              <div>
                <p>Excepción contextual</p>
                <h3>Cambiar tipo de servicio</h3>
                <span>{quotation.folio} · {context?.service_order_folio}</span>
              </div>
              <button className="icon-text-button" onClick={() => setIsOpen(false)} type="button">
                Cerrar
              </button>
            </div>
            <label>
              Servicio actual
              <select
                required
                value={form.quotationLineNumber}
                onChange={(event) => setForm((value) => ({
                  ...value,
                  quotationLineNumber: event.target.value,
                  requestedServiceKey: ''
                }))}
              >
                <option value="">Selecciona la partida visible</option>
                {activeItems.map((item, index) => (
                  <option key={item.id} value={index + 1}>
                    Partida {index + 1} · {item.service_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Nuevo servicio
              <select
                required
                disabled={!selectedItem}
                value={form.requestedServiceKey}
                onChange={(event) => setForm((value) => ({
                  ...value,
                  requestedServiceKey: event.target.value
                }))}
              >
                <option value="">Selecciona un servicio vigente</option>
                {selectableServices.map((item) => (
                  <option key={item.internalKey} value={item.internalKey}>
                    {formatQuotationServiceOption(item)}
                  </option>
                ))}
              </select>
            </label>
            {selectedItem && requestedItem ? (
              <div className="sales-exception-impact">
                <strong>Impacto a revisar</strong>
                <span>
                  {selectedItem.service_name} → {requestedItem.name}. El backend verificará
                  precio, impuestos, acreditación, plantilla y configuración operativa.
                </span>
              </div>
            ) : null}
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
                {isSaving ? 'Enviando…' : 'Enviar para autorización'}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </section>
  );
}


export function QuotationServiceExceptionReview({ currentUser }) {
  const [items, setItems] = useState([]);
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);

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

  async function decide(item, decision) {
    const labels = {
      authorize: 'Comentario de autorización (opcional)',
      reject: 'Motivo del rechazo',
      request_information: 'Información que debe proporcionar el solicitante'
    };
    const comment = window.prompt(labels[decision], '') ?? '';
    if (decision !== 'authorize' && !comment.trim()) return;
    try {
      await reviewQuotationServiceChange(item.folio, {
        decision,
        comment: comment.trim() || null,
        validity_hours: 72
      });
      setMessage(`${item.folio} actualizado.`);
      await load();
    } catch (error) {
      setMessage(error.message);
    }
  }

  if (!hasQuotationExceptionPermission(
    currentUser,
    'quotations.exceptions.inspect_change_service'
  )) {
    return <div className="empty-state">No tienes permiso para consultar excepciones.</div>;
  }

  return (
    <section className="sales-exception-review">
      <div className="section-heading">
        <div>
          <p>Autorización institucional</p>
          <h2>Excepciones de Ventas</h2>
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
              <div><dt>Servicio</dt><dd>{item.current_service_name} → {item.requested_service_name}</dd></div>
              <div><dt>Solicitó</dt><dd>{item.requester_name}</dd></div>
              <div><dt>ETS</dt><dd>{item.service_order_status} · {item.equipment_count} equipos</dd></div>
              <div><dt>Motivo</dt><dd>{item.reason}</dd></div>
              <div><dt>Impacto</dt><dd>{item.impact?.message}</dd></div>
            </dl>
            {item.can_review && ['pending_review', 'information_required'].includes(item.status) ? (
              <div className="toolbar-actions">
                <button className="primary-button" onClick={() => decide(item, 'authorize')} type="button">
                  Autorizar
                </button>
                <button className="table-button" onClick={() => decide(item, 'request_information')} type="button">
                  Solicitar información
                </button>
                <button className="table-button table-button--danger" onClick={() => decide(item, 'reject')} type="button">
                  Rechazar
                </button>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
