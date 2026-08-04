import { Wrench } from 'lucide-react';
import React from 'react';

import PortalEmptyState from '../components/PortalEmptyState.jsx';
import PortalStatusBadge from '../components/PortalStatusBadge.jsx';
import { SERVICE_STATUS, formatPortalDate, presentationFor } from '../presentation/clientPortalPresentation.js';

export default function ClientPortalServices({ items, loading }) {
  return (
    <div className="client-portal-page">
      <header className="client-portal-page-header"><div><span className="client-portal-eyebrow">Operación</span><h1>Mis servicios</h1><p>Da seguimiento a los servicios asociados con tu organización.</p></div><Wrench size={28} /></header>
      {loading ? <div className="portal-loading">Cargando servicios...</div> : items.length ? (
        <div className="portal-card-list">
          {items.map((service) => {
            const status = presentationFor(SERVICE_STATUS, service.status);
            const progress = status.progress ?? 0;
            return (
              <article className="portal-record-card portal-record-card--service" key={service.id}>
                <div className="portal-record-card__main">
                  <div className="portal-record-card__title"><div><small>Expediente de servicio</small><h2>{service.folio}</h2></div><PortalStatusBadge presentation={status} /></div>
                  <p>{service.items?.map((item) => item.service_name).filter(Boolean).slice(0, 3).join(' · ') || 'Servicio metrológico'}</p>
                  <div className="portal-progress" aria-label={`Avance ${progress}%`}><span style={{ width: `${progress}%` }} /></div>
                  <div className="portal-record-card__meta"><span>Programado: {formatPortalDate(service.agenda_date)}</span><span>Equipos: {service.completed_equipment ?? 0} de {service.total_equipment ?? 0}</span>{service.technician_name ? <span>Técnico: {service.technician_name}</span> : null}</div>
                </div>
              </article>
            );
          })}
        </div>
      ) : <PortalEmptyState title="No hay servicios activos" description="Los servicios programados y en proceso aparecerán en esta sección." />}
    </div>
  );
}
