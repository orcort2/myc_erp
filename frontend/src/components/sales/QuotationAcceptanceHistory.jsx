import React, { useEffect, useState } from 'react';

import { listQuotationAcceptances, openQuotationAcceptancePdf } from '../../services/api.js';

/** Evidencia histórica de cada aceptación: consulta autenticada, sin enlaces públicos. */
export default function QuotationAcceptanceHistory({ quotationId, status }) {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    listQuotationAcceptances(quotationId)
      .then((result) => { if (!cancelled) setRows(result); })
      .catch((requestError) => { if (!cancelled) setError(requestError.message); });
    return () => { cancelled = true; };
  }, [quotationId, status]);

  if (!rows.length && !error) return null;
  return (
    <section className="quotation-section" aria-label="Aceptaciones del cliente">
      <div className="quotation-section__title">
        <p>Evidencia comercial</p>
        <h3>Aceptaciones del cliente</h3>
      </div>
      {error ? <small role="alert" className="form-error">{error}</small> : null}
      <div className="quotation-history-list">
        {rows.map((row) => (
          <article key={row.id}>
            <div>
              <strong>{row.confirmation_folio || `Aceptación #${row.id}`}</strong>
              <span>
                {row.signer_name} · {new Date(row.accepted_at).toLocaleString('es-MX')}
              </span>
              <small>
                {row.is_current
                  ? 'Vigente'
                  : `Ya no vigente desde ${new Date(row.invalidated_at).toLocaleString('es-MX')}; la evidencia se conserva.`}
              </small>
            </div>
            <button
              className="table-button"
              onClick={() => openQuotationAcceptancePdf(quotationId, row.id).catch((e) => setError(e.message))}
              type="button"
            >
              Ver PDF aceptado
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
