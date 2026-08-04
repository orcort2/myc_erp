import { FileText } from 'lucide-react';
import React from 'react';

import PortalEmptyState from '../components/PortalEmptyState.jsx';
import PortalStatusBadge from '../components/PortalStatusBadge.jsx';
import { QUOTATION_STATUS, formatPortalCurrency, formatPortalDate, presentationFor } from '../presentation/clientPortalPresentation.js';

export default function ClientPortalQuotations({ items, loading }) {
  return (
    <div className="client-portal-page">
      <header className="client-portal-page-header"><div><span className="client-portal-eyebrow">Comercial</span><h1>Mis cotizaciones</h1><p>Consulta las propuestas vigentes enviadas por MYC.</p></div><FileText size={28} /></header>
      {loading ? <div className="portal-loading">Cargando cotizaciones...</div> : items.length ? (
        <div className="portal-card-list">
          {items.map((quotation) => (
            <article className="portal-record-card" key={quotation.id}>
              <div className="portal-record-card__main">
                <div className="portal-record-card__title"><div><small>Cotización</small><h2>{quotation.folio}</h2></div><PortalStatusBadge presentation={presentationFor(QUOTATION_STATUS, quotation.status)} /></div>
                <p>{quotation.items?.map((item) => item.service_name).filter(Boolean).slice(0, 3).join(' · ') || 'Servicios metrológicos'}</p>
                <div className="portal-record-card__meta"><span>Emisión: {formatPortalDate(quotation.issued_on)}</span><span>Vigencia: {formatPortalDate(quotation.valid_until)}</span><span>{quotation.items?.length ?? 0} concepto(s)</span></div>
              </div>
              <div className="portal-record-card__aside"><small>Total</small><strong>{formatPortalCurrency(quotation.total, quotation.items?.[0]?.currency)}</strong><span>{quotation.payment_terms || 'Condiciones indicadas en la cotización'}</span></div>
            </article>
          ))}
        </div>
      ) : <PortalEmptyState title="No hay cotizaciones visibles" description="Aquí aparecerán las cotizaciones enviadas, en espera o aceptadas." />}
    </div>
  );
}
