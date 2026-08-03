import {
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  UserRound,
  X,
} from 'lucide-react';
import React, {
  useEffect,
  useState,
} from 'react';

import { navigation } from '../constants/navigation.js';
import { navigate } from '../utils/routing.js';
import { filterAccessibleEntries } from '../utils/accessControl.js';
import BrandLockup from './BrandLockup.jsx';
import NotificationBell from './notifications/NotificationBell.jsx';
import { NotificationProvider } from './notifications/NotificationProvider.jsx';

import './notifications/notifications.css';

function getRoleLabel(user) {
  return user?.roles?.[0]?.name ?? 'Sin rol';
}

function AppLayout({
  children,
  onLogout,
  showSidebar = false,
  subtitle,
  user,
}) {
  const [
    isSidebarCollapsed,
    setIsSidebarCollapsed,
  ] = useState(false);

  const [
    isMobileSidebarOpen,
    setIsMobileSidebarOpen,
  ] = useState(false);

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

    window.addEventListener(
      'keydown',
      handleEscape,
    );

    return () => {
      window.removeEventListener(
        'keydown',
        handleEscape,
      );
    };
  }, [showSidebar]);

  function navigateFromSidebar(path) {
    navigate(path);
    setIsMobileSidebarOpen(false);
  }

  const shellClassName = [
    'app-shell',
    showSidebar
      ? 'app-shell--module'
      : 'app-shell--dashboard',
    showSidebar && isSidebarCollapsed
      ? 'is-sidebar-collapsed'
      : '',
    showSidebar && isMobileSidebarOpen
      ? 'is-mobile-sidebar-open'
      : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <NotificationProvider enabled={Boolean(user)}>
      <main className={shellClassName}>
        {showSidebar ? (
          <>
            <button
              aria-label="Cerrar navegación lateral"
              className="sidebar-overlay"
              onClick={() =>
                setIsMobileSidebarOpen(false)
              }
              type="button"
            />

            <aside className="sidebar">
              <div className="sidebar__controls">
                <button
                  aria-label="Cerrar navegación"
                  className="sidebar-mobile-close"
                  onClick={() =>
                    setIsMobileSidebarOpen(false)
                  }
                  type="button"
                >
                  <X
                    aria-hidden="true"
                    size={18}
                  />
                </button>

                <button
                  aria-label={
                    isSidebarCollapsed
                      ? 'Expandir navegación lateral'
                      : 'Colapsar navegación lateral'
                  }
                  className="sidebar-collapse-button"
                  onClick={() =>
                    setIsSidebarCollapsed(
                      (current) => !current,
                    )
                  }
                  type="button"
                >
                  {isSidebarCollapsed ? (
                    <PanelLeftOpen
                      aria-hidden="true"
                      size={18}
                    />
                  ) : (
                    <PanelLeftClose
                      aria-hidden="true"
                      size={18}
                    />
                  )}
                </button>
              </div>

              <BrandLockup subtitle={subtitle} />

              <nav
                aria-label="Navegación principal"
                className="nav-list"
              >
                {filterAccessibleEntries(navigation, user).map((item) => {
                  const Icon = item.icon;

                  return (
                    <button
                      className="nav-item"
                      key={item.label}
                      onClick={() =>
                        navigateFromSidebar(
                          item.path,
                        )
                      }
                      title={item.label}
                      type="button"
                    >
                      <Icon
                        aria-hidden="true"
                        size={18}
                      />

                      <span>{item.label}</span>
                    </button>
                  );
                })}
              </nav>
            </aside>
          </>
        ) : null}

        <section className="workspace">
          <header className="topbar">
            <div className="topbar__start">
              {showSidebar ? (
                <button
                  aria-label="Abrir navegación lateral"
                  className="sidebar-menu-button"
                  onClick={() =>
                    setIsMobileSidebarOpen(true)
                  }
                  type="button"
                >
                  <Menu
                    aria-hidden="true"
                    size={19}
                  />
                </button>
              ) : null}

              <BrandLockup
                compact
                subtitle={subtitle}
              />
            </div>

            <div className="topbar__actions">
              <div className="topbar__identity">
                <UserRound
                  aria-hidden="true"
                  size={20}
                />

                <div>
                  <strong>
                    {user?.full_name
                      ?? 'Usuario MYC'}
                  </strong>

                  <span>
                    Rol: {getRoleLabel(user)}
                  </span>
                </div>
              </div>

              <NotificationBell />

              <button
                className="icon-text-button"
                onClick={onLogout}
                type="button"
              >
                <LogOut
                  aria-hidden="true"
                  size={18}
                />

                <span>Salir</span>
              </button>
            </div>
          </header>

          {children}
        </section>
      </main>
    </NotificationProvider>
  );
}

export default AppLayout;
