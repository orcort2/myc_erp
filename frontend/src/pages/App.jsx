import {
  BadgeCheck,
  Banknote,
  Boxes,
  Building2,
  ClipboardList,
  FileCheck2,
  FileText,
  Gauge,
  LogOut,
  MessageSquareText,
  Settings,
  ShieldCheck,
  UserRound
} from 'lucide-react';
import React from 'react';
import { useEffect, useMemo, useState } from 'react';

import mycLogo from '../assets/myc-logo.png';
import {
  clearTokens,
  getAccessToken,
  getCurrentUser,
  getDashboardCounts,
  login,
  register
} from '../services/api.js';

const navigation = [
  { label: 'Dashboard', icon: Gauge, path: '/dashboard' },
  { label: 'Clientes', icon: Building2, path: '/dashboard#clientes' },
  { label: 'CRM', icon: MessageSquareText, path: '/dashboard#crm' },
  { label: 'Ventas / Cotizaciones', icon: FileText, path: '/dashboard#cotizaciones' },
  { label: 'Servicios', icon: ShieldCheck, path: '/dashboard#servicios' },
  { label: 'Ordenes de servicio', icon: ClipboardList, path: '/dashboard#ordenes' },
  { label: 'Equipos', icon: Boxes, path: '/dashboard#equipos' },
  { label: 'Hojas de campo', icon: BadgeCheck, path: '/dashboard#hojas' },
  { label: 'Certificados', icon: FileCheck2, path: '/dashboard#certificados' },
  { label: 'Finanzas', icon: Banknote, path: '/dashboard#finanzas' },
  { label: 'Configuracion', icon: Settings, path: '/dashboard#configuracion' }
];

const modules = [
  {
    key: 'clients',
    name: 'Clientes',
    description: 'Base comercial para cuentas, contactos y seguimiento operativo.',
    icon: Building2,
    path: '/dashboard#clientes',
    status: 'Activo'
  },
  {
    key: 'crm',
    name: 'CRM',
    description: 'Prospectos, oportunidades y conversaciones comerciales.',
    icon: MessageSquareText,
    path: '/dashboard#crm',
    status: 'Pendiente'
  },
  {
    key: 'quotations',
    name: 'Ventas / Cotizaciones',
    description: 'Propuestas, condiciones comerciales y origen de servicios.',
    icon: FileText,
    path: '/dashboard#cotizaciones',
    status: 'Activo'
  },
  {
    key: 'services',
    name: 'Servicios',
    description: 'Flujo operativo de laboratorio, ruta y programacion tecnica.',
    icon: ShieldCheck,
    path: '/dashboard#servicios',
    status: 'En desarrollo'
  },
  {
    key: 'serviceOrders',
    name: 'Ordenes de servicio',
    description: 'Planeacion, avance y cierre de trabajos autorizados.',
    icon: ClipboardList,
    path: '/dashboard#ordenes',
    status: 'Activo'
  },
  {
    key: 'equipment',
    name: 'Equipos',
    description: 'Instrumentos individuales vinculados a cada orden de servicio.',
    icon: Boxes,
    path: '/dashboard#equipos',
    status: 'Activo'
  },
  {
    key: 'fieldSheets',
    name: 'Hojas de campo',
    description: 'Registro tecnico por equipo, resultados y trazabilidad del trabajo.',
    icon: BadgeCheck,
    path: '/dashboard#hojas',
    status: 'Activo'
  },
  {
    key: 'certificates',
    name: 'Certificados',
    description: 'Generacion, revision y liberacion documental para clientes.',
    icon: FileCheck2,
    path: '/dashboard#certificados',
    status: 'Activo'
  },
  {
    key: 'finance',
    name: 'Finanzas',
    description: 'Pagos, facturas y control de liberacion administrativa.',
    icon: Banknote,
    path: '/dashboard#finanzas',
    status: 'Pendiente'
  },
  {
    key: 'settings',
    name: 'Configuracion',
    description: 'Usuarios, roles, permisos y parametros del sistema.',
    icon: Settings,
    path: '/dashboard#configuracion',
    status: 'En desarrollo'
  }
];

const defaultCounts = {
  clients: 0,
  quotations: 0,
  serviceOrders: 0,
  equipment: 0,
  fieldSheets: 0,
  certificates: 0
};

function getCurrentPath() {
  const pathname = window.location.pathname === '/' ? '/dashboard' : window.location.pathname;
  return `${pathname}${window.location.hash}`;
}

function navigate(path) {
  window.history.pushState({}, '', path);
  window.dispatchEvent(new PopStateEvent('popstate'));
}

function getRoleLabel(user) {
  return user?.roles?.[0]?.name ?? 'Sin rol';
}

function formatModuleDateTime(date) {
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(date);
}

function BrandLockup({ compact = false, subtitle = null }) {
  return (
    <div className={compact ? 'brand-lockup brand-lockup--compact' : 'brand-lockup'}>
      <img alt="MYC" src={mycLogo} />
      <div>
        <strong>MYC SYSTEM</strong>
        {subtitle ? <span>{subtitle}</span> : null}
      </div>
    </div>
  );
}

function LoginPage({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const user =
        mode === 'login'
          ? await login(email, password)
          : await register({ email, fullName, password });
      onAuthenticated(user);
      navigate('/dashboard');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-panel" aria-label="Acceso MYC SYSTEM">
        <BrandLockup subtitle="Acceso principal" />

        <div className="auth-heading">
          <p>{mode === 'login' ? 'Acceso seguro' : 'Primer acceso'}</p>
          <h1>{mode === 'login' ? 'Iniciar sesion' : 'Crear usuario'}</h1>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === 'register' ? (
            <label>
              Nombre
              <input
                autoComplete="name"
                onChange={(event) => setFullName(event.target.value)}
                required
                type="text"
                value={fullName}
              />
            </label>
          ) : null}

          <label>
            Correo
            <input
              autoComplete="email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <label>
            Contrasena
            <input
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              minLength={8}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          {error ? <div className="form-error">{error}</div> : null}

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? 'Validando...' : mode === 'login' ? 'Entrar' : 'Crear usuario'}
          </button>
        </form>

        <button
          className="text-button"
          onClick={() => {
            setError('');
            setMode(mode === 'login' ? 'register' : 'login');
          }}
          type="button"
        >
          {mode === 'login' ? 'Crear primer usuario' : 'Ya tengo usuario'}
        </button>
      </section>
    </main>
  );
}

function AppLayout({ children, onLogout, showSidebar = false, subtitle, user }) {
  return (
    <main className={showSidebar ? 'app-shell app-shell--module' : 'app-shell app-shell--dashboard'}>
      {showSidebar ? (
        <aside className="sidebar">
          <BrandLockup subtitle={subtitle} />

          <nav className="nav-list" aria-label="Navegacion principal">
            {navigation.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  className="nav-item"
                  key={item.label}
                  onClick={() => navigate(item.path)}
                  type="button"
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </aside>
      ) : null}

      <section className="workspace">
        <header className="topbar">
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

function ModulePage({ module, timestamp }) {
  const Icon = module.icon;

  return (
    <section className="module-workspace">
      <div className="module-workspace__hero">
        <span className="module-workspace__icon">
          <Icon size={28} />
        </span>
        <div>
          <p>Modulo MYC SYSTEM</p>
          <h1>{module.name}</h1>
          <span>{module.description}</span>
        </div>
        <time className="module-workspace__time" dateTime={timestamp.toISOString()}>
          {formatModuleDateTime(timestamp)}
        </time>
      </div>

      <div className="module-workspace__panel">
        <h2>{module.status}</h2>
        <p>
          Vista preparada para conectar el flujo funcional del modulo. La navegacion lateral ya
          queda disponible aqui sin ocupar espacio en el dashboard principal.
        </p>
      </div>
    </section>
  );
}

function DashboardPage({ user }) {
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
          <strong>{isLoading ? '-' : counts.certificates}</strong>
          <span>Certificados</span>
        </div>
      </section>
    </>
  );
}

export function App() {
  const [path, setPath] = useState(getCurrentPath);
  const [user, setUser] = useState(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    function handleRouteChange() {
      setPath(getCurrentPath());
    }

    window.addEventListener('popstate', handleRouteChange);
    window.addEventListener('hashchange', handleRouteChange);
    return () => {
      window.removeEventListener('popstate', handleRouteChange);
      window.removeEventListener('hashchange', handleRouteChange);
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function checkSession() {
      if (!getAccessToken()) {
        setIsCheckingSession(false);
        if (path !== '/login') {
          navigate('/login');
        }
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        if (isMounted) {
          setUser(currentUser);
          if (path === '/login') {
            navigate('/dashboard');
          }
        }
      } catch {
        clearTokens();
        if (isMounted) {
          setUser(null);
          navigate('/login');
        }
      } finally {
        if (isMounted) {
          setIsCheckingSession(false);
        }
      }
    }

    checkSession();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60000);
    return () => window.clearInterval(timer);
  }, []);

  function handleLogout() {
    clearTokens();
    setUser(null);
    navigate('/login');
  }

  if (isCheckingSession) {
    return (
      <main className="loading-screen">
        <BrandLockup compact />
        <span>Cargando MYC SYSTEM</span>
      </main>
    );
  }

  if (path === '/login') {
    return <LoginPage onAuthenticated={setUser} />;
  }

  if (!user) {
    navigate('/login');
    return null;
  }

  const selectedModule = modules.find((module) => path === module.path);
  const showModuleNavigation = Boolean(selectedModule);
  const layoutSubtitle = selectedModule ? formatModuleDateTime(now) : 'Sistema principal';

  return (
    <AppLayout
      onLogout={handleLogout}
      showSidebar={showModuleNavigation}
      subtitle={layoutSubtitle}
      user={user}
    >
      {selectedModule ? (
        <ModulePage module={selectedModule} timestamp={now} />
      ) : (
        <DashboardPage user={user} />
      )}
    </AppLayout>
  );
}
