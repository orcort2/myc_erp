import { Award, CalendarDays, FileClock, FileText, Wrench } from 'lucide-react';
import React from 'react';

import { navigate } from '../../utils/routing.js';
import PortalEmptyState from '../components/PortalEmptyState.jsx';
import PortalStatusBadge from '../components/PortalStatusBadge.jsx';
import PortalSummaryCard from '../components/PortalSummaryCard.jsx';
import {
  SERVICE_STATUS,
  formatPortalDate,
  presentationFor,
} from '../presentation/clientPortalPresentation.js';

export default function ClientPortalHome({ certificates, loading, quotations, serviceOrders, user }) {
  const activeServices = serviceOrders.filter((item) => !['closed', 'released'].includes(item.status));
  const pendingQuotations = quotations.filter((item) => ['sent', 'waiting'].includes(item.status));
  const nextService = [...activeServices]
    .filter((item) => item.agenda_date || item.service_date)
    .sort((a, b) => `${a.agenda_date ?? a.service_date}`.localeCompare(`${b.agenda_date ?? b.service_date}`))[0];

  return (
    <div className="client-portal-page">
      <section className="client-portal-hero">
        <div>
          <span className="client-portal-eyebrow">Resumen de tu cuenta</span>
          <h1>Hola, {user?.full_name?.split(' ')[0] ?? 'bienvenido'}</h1>
          <p>Consulta el estado de tus servicios y descarga la documentación que MYC ha liberado para ti.</p>
        </div>
        <div className="client-portal-hero__date"><CalendarDays size={20} /><span>{formatPortalDate(new Date().toISOString())}</span></div>
      </section>

      <section className="portal-summary-grid" aria-label="Resumen">
        <PortalSummaryCard icon={FileClock} label="Cotizaciones por revisar" value={loading ? '—' : pendingQuotations.length} detail="Enviadas o en espera" onClick={() => navigate('/portal/cotizaciones')} />
        <PortalSummaryCard icon={Wrench} label="Servicios activos" value={loading ? '—' : activeServices.length} detail="En curso o programados" onClick={() => navigate('/portal/servicios')} />
        <PortalSummaryCard icon={Award} label="Certificados disponibles" value={loading ? '—' : certificates.length} detail="Listos para descargar" onClick={() => navigate('/portal/certificados')} />
      </section>

      <section className="portal-dashboard-grid">
        <article className="portal-panel">
          <header className="portal-panel__header"><div><small>Seguimiento</small><h2>Próximo servicio</h2></div><Wrench size={20} /></header>
          {nextService ? (
            <div className="portal-next-service">
              <div className="portal-next-service__top"><strong>{nextService.folio}</strong><PortalStatusBadge presentation={presentationFor(SERVICE_STATUS, nextService.status)} /></div>
              <p>{nextService.items?.map((item) => item.service_name).filter(Boolean).slice(0, 2).join(' · ') || 'Servicio metrológico'}</p>
              <dl>
                <div><dt>Fecha</dt><dd>{formatPortalDate(nextService.agenda_date ?? nextService.service_date)}</dd></div>
                <div><dt>Equipos</dt><dd>{nextService.completed_equipment ?? 0} de {nextService.total_equipment ?? 0}</dd></div>
              </dl>
              <button className="portal-secondary-button" onClick={() => navigate('/portal/servicios')} type="button">Ver seguimiento</button>
            </div>
          ) : <PortalEmptyState title="Sin servicios próximos" description="Cuando se programe un servicio aparecerá en este espacio." />}
        </article>

        <article className="portal-panel">
          <header className="portal-panel__header"><div><small>Documentación</small><h2>Actividad reciente</h2></div><FileText size={20} /></header>
          {certificates.length ? (
            <div className="portal-recent-list">
              {certificates.slice(0, 4).map((certificate) => (
                <button key={certificate.id} onClick={() => navigate('/portal/certificados')} type="button">
                  <span className="portal-recent-list__icon"><Award size={18} /></span>
                  <span><strong>{certificate.folio}</strong><small>Certificado disponible</small></span>
                  <time>{formatPortalDate(certificate.released_on ?? certificate.released_to_client_at)}</time>
                </button>
              ))}
            </div>
          ) : <PortalEmptyState title="Sin documentos liberados" description="Los certificados autenticados aparecerán aquí." />}
        </article>
      </section>
    </div>
  );
}
