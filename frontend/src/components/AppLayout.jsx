import { FlaskConical, LogOut, Menu, PanelLeftClose, PanelLeftOpen, UserRound, X } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import { navigation } from '../constants/navigation.js';
import { navigate } from '../utils/routing.js';
import BrandLockup from './BrandLockup.jsx';

function getRoleLabel(user) {
  return user?.roles?.[0]?.name ?? 'Sin rol';
}

function AppLayout({ children, onLogout, showSidebar = false, subtitle, user }) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  useEffect(() => {
    if (!showSidebar) {
      setIsMobileSidebarOpen(false);
      return undefined;
    }

    function handleEscape(event) {
      if (event.key === 'Escape') {
        setIsMobileSidebarOpen(false);
      }
    }

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [showSidebar]);

  function navigateFromSidebar(path) {
    navigate(path);
    setIsMobileSidebarOpen(false);
  }

  const shellClassName = [
    'app-shell',
    showSidebar ? 'app-shell--module' : 'app-shell--dashboard',
    showSidebar && isSidebarCollapsed ? 'is-sidebar-collapsed' : '',
    showSidebar && isMobileSidebarOpen ? 'is-mobile-sidebar-open' : ''
  ].filter(Boolean).join(' ');

  return (
    <main className={shellClassName}>
      {showSidebar ? (
        <>
        <button
          aria-label="Cerrar navegacion lateral"
          className="sidebar-overlay"
          onClick={() => setIsMobileSidebarOpen(false)}
          type="button"
        />
        <aside className="sidebar">
          <div className="sidebar__controls">
            <button
              aria-label="Cerrar navegacion"
              className="sidebar-mobile-close"
              onClick={() => setIsMobileSidebarOpen(false)}
              type="button"
            >
              <X size={18} />
            </button>
            <button
              aria-label={isSidebarCollapsed ? 'Expandir navegacion lateral' : 'Colapsar navegacion lateral'}
              className="sidebar-collapse-button"
              onClick={() => setIsSidebarCollapsed((current) => !current)}
              type="button"
            >
              {isSidebarCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            </button>
          </div>
          <BrandLockup subtitle={subtitle} />

          <nav className="nav-list" aria-label="Navegacion principal">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  className="nav-item"
                  key={item.label}
                  onClick={() => navigateFromSidebar(item.path)}
                  type="button"
                  title={item.label}
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
          <nav className="lab-nav-list" aria-label="Navegacion de desarrollo">
            <span>Desarrollo</span>
            <button className="nav-item nav-item--lab" onClick={() => navigateFromSidebar('/invoice-workbench-lab')} type="button" title="Invoice Workbench (LAB)">
              <FlaskConical size={18} />
              <span>Invoice Workbench (LAB)</span>
            </button>
          </nav>
        </aside>
        </>
      ) : null}

      <section className="workspace">
        <header className="topbar">
          {showSidebar ? (
            <button
              aria-label="Abrir navegacion lateral"
              className="sidebar-menu-button"
              onClick={() => setIsMobileSidebarOpen(true)}
              type="button"
            >
              <Menu size={19} />
            </button>
          ) : null}
          <BrandLockup compact subtitle={subtitle} />
          <div className="topbar__identity">
            <UserRound size={20} />
            <div>
              <strong>{user?.full_name ?? 'Usuario MYC'}</strong>
              <span>Rol: {getRoleLabel(user)}</span>
            </div>
          </div>
          <button className="icon-text-button" onClick={onLogout} type="button">
            <LogOut size={18} />
            <span>Salir</span>
          </button>
        </header>
        {children}
      </section>
    </main>
  );
}



export default AppLayout;
