import { Award, FileText, Home, LogOut, Menu, UserRound, Wrench, X } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import BrandLockup from '../components/BrandLockup.jsx';
import { navigate } from '../utils/routing.js';

const entries = [
  { path: '/portal', label: 'Inicio', icon: Home },
  { path: '/portal/cotizaciones', label: 'Cotizaciones', icon: FileText },
  { path: '/portal/servicios', label: 'Mis servicios', icon: Wrench },
  { path: '/portal/certificados', label: 'Certificados', icon: Award },
  { path: '/portal/perfil', label: 'Mi perfil', icon: UserRound },
];

export default function ClientPortalLayout({ children, currentPath, onLogout, user }) {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key === 'Escape') setIsOpen(false);
    }
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, []);

  function go(path) {
    navigate(path);
    setIsOpen(false);
  }

  return (
    <main className={`client-portal-shell ${isOpen ? 'is-navigation-open' : ''}`}>
      <button className="client-portal-overlay" aria-label="Cerrar menú" onClick={() => setIsOpen(false)} type="button" />
      <aside className="client-portal-sidebar">
        <div className="client-portal-sidebar__head">
          <BrandLockup subtitle="Portal de clientes" />
          <button className="client-portal-mobile-close" aria-label="Cerrar menú" onClick={() => setIsOpen(false)} type="button"><X size={19} /></button>
        </div>
        <nav aria-label="Navegación del portal">
          {entries.map(({ path, label, icon: Icon }) => (
            <button
              className={`client-portal-nav-item ${currentPath === path ? 'is-active' : ''}`}
              key={path}
              onClick={() => go(path)}
              type="button"
            >
              <Icon aria-hidden="true" size={19} />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="client-portal-sidebar__footer">
          <strong>{user?.full_name ?? 'Cliente MYC'}</strong>
          <span>{user?.email}</span>
        </div>
      </aside>

      <section className="client-portal-workspace">
        <header className="client-portal-topbar">
          <button className="client-portal-menu" aria-label="Abrir menú" onClick={() => setIsOpen(true)} type="button"><Menu size={20} /></button>
          <div>
            <small>METROLOGÍA Y SERVICIOS MYC</small>
            <strong>Portal de clientes</strong>
          </div>
          <button className="client-portal-logout" onClick={onLogout} type="button"><LogOut size={18} /><span>Salir</span></button>
        </header>
        {children}
      </section>
    </main>
  );
}
