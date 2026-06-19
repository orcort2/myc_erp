import React, { useEffect, useMemo, useState } from 'react';

import { defaultCounts, modules } from '../constants/navigation.js';
import { getDashboardCounts } from '../services/api.js';
import { navigate } from '../utils/routing.js';

function getRoleLabel(user) {
  return user?.roles?.[0]?.name ?? 'Sin rol';
}

function DashboardHome({ user }) {
  const [counts, setCounts] = useState(defaultCounts);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    async function loadCounts() {
      try {
        const nextCounts = await getDashboardCounts();
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
  }, []);

  const roleLabel = useMemo(() => getRoleLabel(user), [user]);

  return (
    <>
      <section className="workspace-header">
        <div>
          <p>MYC SYSTEM</p>
          <h1>Centro modular de operacion</h1>
          <span className="workspace-header__welcome">
            Bienvenido {user?.full_name ?? 'Usuario'} · Rol: {roleLabel}
          </span>
        </div>
        <div className="workspace-header__summary">
          <strong>{isLoading ? '-' : counts.clients}</strong>
          <span>clientes activos</span>
        </div>
      </section>

      <section className="flow-strip" aria-label="Flujo principal">
        <span>Lead</span>
        <span>Cotizacion</span>
        <span>Orden</span>
        <span>Equipo</span>
        <span>Hoja</span>
        <span>Certificado</span>
        <span>Pago</span>
        <span>Cierre</span>
      </section>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}

      <section className="modules-grid" aria-busy={isLoading} aria-label="Modulos principales">
        {modules.map((module) => {
          const Icon = module.icon;
          const count = counts[module.key];
          const hasCount = typeof count === 'number';
          return (
            <button
              className="module-card"
              id={module.path.split('#')[1]}
              key={module.key}
              onClick={() => navigate(module.path)}
              type="button"
            >
              <div className="module-card__shine" />
              <div className="module-card__header">
                <span className="module-card__icon">
                  <Icon size={24} />
                </span>
                <span className={`module-card__status status-${module.status.toLowerCase().replaceAll(' ', '-')}`}>
                  {module.status}
                </span>
              </div>
              <h2>{module.name}</h2>
              <p>{module.description}</p>
              <div className="module-card__footer">
                {hasCount ? (
                  <>
                    <strong>{isLoading ? '-' : count}</strong>
                    <span>registros</span>
                  </>
                ) : (
                  <span>Preparado para navegacion</span>
                )}
              </div>
            </button>
          );
        })}
      </section>

      <section className="operations-band" aria-label="Resumen operativo">
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : counts.quotations}</strong>
          <span>Cotizaciones</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : counts.serviceOrders}</strong>
          <span>Ordenes</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : counts.equipment}</strong>
          <span>Equipos</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : counts.certificatesReview}</strong>
          <span>Certificados pendientes calidad</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : counts.certificatesApproved}</strong>
          <span>Certificados aprobados</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : counts.certificatesReleased}</strong>
          <span>Certificados liberados</span>
        </div>
      </section>
    </>
  );
}



export default DashboardHome;
