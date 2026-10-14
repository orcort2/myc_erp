import React, { useCallback, useEffect, useState } from 'react';
import {
  CheckCircle2,
  Clock3,
  Mail,
  RotateCcw,
  XCircle
} from 'lucide-react';

import { listQuotationEmailDeliveries } from '../services/api.js';
import { emailStatusLabels } from '../utils/quotationEmail.js';

// Contextual history of one quotation. A failed delivery is never mutated:
// "Reenviar" runs the whole contextual flow again and creates a NEW delivery.
function QuotationEmailHistory({ quotationId, refreshKey = 0, canResend = false, onResend = () => {} }) {
  const [deliveries, setDeliveries] = useState([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setDeliveries(await listQuotationEmailDeliveries(quotationId));
      setError('');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }, [quotationId]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  return (
    <section className="quotation-section" aria-label="Correos de la cotización">
      <div className="quotation-section__title">
        <p>Correos</p>
        <h3>
          <Mail size={19} aria-hidden="true" />
          Historial de correos
        </h3>
      </div>
      {error ? <div className="form-error">{error}</div> : null}
      {isLoading ? <div className="clients-empty">Cargando correos…</div> : null}
      {!isLoading && deliveries.length === 0 && !error ? <div className="clients-empty">Esta cotización aún no se ha enviado por correo.</div> : null}
      <div className="quotation-history-list">
        {deliveries.map((delivery) => (
          <article className="quotation-email-delivery" key={delivery.id}>
            <div className="quotation-email-delivery__body">
              <div className="quotation-email-delivery__top">
                <strong className={`quotation-email__status is-${delivery.status}`}>
                  {delivery.status === 'sent'
                    ? <CheckCircle2 size={15} aria-hidden="true" />
                    : delivery.status === 'failed'
                      ? <XCircle size={15} aria-hidden="true" />
                      : <Clock3 size={15} aria-hidden="true" />}
                  {emailStatusLabels[delivery.status] ?? delivery.status}
                </strong>
                <time dateTime={delivery.created_at}>
                  {new Date(delivery.created_at).toLocaleString('es-MX', {
                    dateStyle: 'medium',
                    timeStyle: 'short'
                  })}
                </time>
              </div>
              <span>Para: {delivery.to.join(', ')}</span>
              {delivery.cc.length ? <span>CC: {delivery.cc.join(', ')}</span> : null}
              <span>Por: {delivery.requested_by_name || 'Sistema'}</span>
              {delivery.attachments.map((file) => (
                <span key={file.sha256 || file.filename}>Adjunto: {file.filename}</span>
              ))}
              {delivery.status === 'failed' && delivery.last_error ? (
                <span className="quotation-email-delivery__error">{delivery.last_error}</span>
              ) : null}
            </div>
            {delivery.status === 'failed' && canResend ? (
              <button className="table-button" onClick={() => onResend(delivery)} type="button">
                <RotateCcw size={14} aria-hidden="true" />
                Reenviar
              </button>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

export default QuotationEmailHistory;
