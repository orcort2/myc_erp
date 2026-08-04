import React, { useEffect, useMemo, useState } from 'react';

import ActivityInboxWidget from '../components/activity/ActivityInboxWidget.jsx';
import { ModuleCard } from '../components/ModuleCard.jsx';
import { defaultCounts, modules } from '../constants/navigation.js';
import { getDashboardCounts } from '../services/api.js';
import { navigate } from '../utils/routing.js';
import { filterAccessibleEntries } from '../utils/accessControl.js';

function getRoleLabel(user) {
  return user?.roles?.[0]?.name ?? 'Sin rol';
}

function safeNumber(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function DashboardHome({ user }) {
  const [counts, setCounts] = useState(defaultCounts);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    async function loadCounts() {
      try {
        const nextCounts = await getDashboardCounts(user);
        if (isMounted) {
          setCounts({ ...defaultCounts, ...nextCounts });
        }
      } catch (requestError) {
        if (isMounted) {
          setError(requestError.message);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadCounts();

    return () => {
      isMounted = false;
    };
  }, [user]);

  const roleLabel = useMemo(() => getRoleLabel(user), [user]);
  const pendingItems = [
    ['Cotizaciones pendientes', counts.quotations],
    ['Servicios programados', counts.servicesScheduled],
    ['Servicios en proceso', counts.servicesInProgress],
    ['Devueltos a técnico', counts.returnedToTechnician],
    ['Captura pendiente', counts.capturePending],
    ['Calidad pendiente', counts.qualityPending],
    ['Autenticación pendiente', counts.authenticationPending],
    ['Certificados por liberar', counts.certificatesToRelease],
    ['Facturación pendiente', counts.billingPending]
  ];
  const indicatorItems = [
    ['Clientes activos', counts.clients],
    ['Servicios abiertos', safeNumber(counts.serviceOrders) - safeNumber(counts.servicesClosed)],
    ['Servicios cerrados', counts.servicesClosed],
    ['Avance promedio ETS', `${safeNumber(counts.etsAverageProgress)}%`],
    ['Certificados pendientes', safeNumber(counts.certificates) - safeNumber(counts.certificatesReleased)],
    ['Certificados autenticados', counts.authenticatedCertificates],
    ['Certificados liberados', counts.certificatesReleased]
  ];

  return (
    <>
      <section className="workspace-header">
        <div>
          <p>MYC SYSTEM</p>
          <h1>Dashboard ejecutivo</h1>
          <span className="workspace-header__welcome">
            Bienvenido {user?.full_name ?? 'Usuario'} · Rol: {roleLabel}
          </span>
        </div>
        <div className="workspace-header__summary">
          <strong>{isLoading ? '-' : counts.clients}</strong>
          <span>clientes activos</span>
        </div>
      </section>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}

      <section className="dashboard-control-panel" aria-busy={isLoading}>
        <div className="dashboard-control-panel__header">
          <div>
            <p>Centro de control operativo</p>
            <h2 className="dashboard-title">Expedientes técnicos en operación</h2>
          </div>
          <div className="dashboard-progress-summary">
            <strong>{isLoading ? '-' : `${safeNumber(counts.etsAverageProgress)}%`}</strong>
            <span>avance promedio ETS</span>
          </div>
        </div>
        <div className="dashboard-progress-bar">
          <span style={{ width: `${safeNumber(counts.etsAverageProgress)}%` }} />
        </div>
        <div className="operations-band dashboard-executive-grid" aria-label="Pendientes operativos">
          {pendingItems.map(([label, value]) => (
            <div className="operations-band__metric" key={label}>
              <strong>{isLoading ? '-' : safeNumber(value)}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="dashboard-section-block">
        <div className="dashboard-section-heading">
          <p>Indicadores ejecutivos</p>
          <h2 className="dashboard-title">Estado consolidado</h2>
        </div>
        <div className="operations-band dashboard-executive-grid dashboard-executive-grid--compact" aria-busy={isLoading} aria-label="Indicadores ejecutivos">
          {indicatorItems.map(([label, value]) => (
            <div className="operations-band__metric" key={label}>
              <strong>{isLoading ? '-' : typeof value === 'string' ? value : Math.max(safeNumber(value), 0)}</strong>
              <span>{label}</span>
            </div>
          ))}
        </div>
      </section>

      <ActivityInboxWidget />

      <section className="dashboard-section-block">
        <div className="dashboard-section-heading">
          <p>Accesos rápidos</p>
          <h2 className="dashboard-title">Trabajo diario</h2>
        </div>
        <div className="modules-grid" aria-busy={isLoading} aria-label="Accesos rapidos">
          {filterAccessibleEntries(modules, user).map((module) => {
            const count = counts[module.key];
            const hasCount = typeof count === 'number';
            return (
              <ModuleCard
                count={hasCount ? safeNumber(count) : undefined}
                isLoading={isLoading}
                key={module.key}
                module={module}
                onOpen={() => navigate(module.path)}
              />
            );
          })}
        </div>
      </section>
    </>
  );
}



export default DashboardHome;
