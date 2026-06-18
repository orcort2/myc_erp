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
  changeQuotationStatus,
  clearTokens,
  createClient,
  createQuotation,
  getAccessToken,
  getCurrentUser,
  getDashboardCounts,
  getQuotation,
  listClients,
  listQuotations,
  login,
  register,
  updateClient,
  updateQuotation
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

const emptyClientForm = {
  commercialName: '',
  rfc: '',
  contactName: '',
  phone: '',
  email: '',
  status: 'Activo',
  street: '',
  exteriorNumber: '',
  interiorNumber: '',
  neighborhood: '',
  city: '',
  addressState: '',
  postalCode: '',
  country: 'Mexico',
  fiscalLegalName: '',
  fiscalRfc: '',
  fiscalPostalCode: '',
  taxRegime: '',
  cfdiUse: ''
};

const clientModalTabs = [
  { key: 'general', label: 'Datos generales' },
  { key: 'address', label: 'Domicilio' },
  { key: 'fiscal', label: 'Datos fiscales' }
];

const emptyQuotationForm = {
  clientId: '',
  validUntil: '',
  notes: ''
};

const emptyProductForm = {
  name: '',
  type: 'Servicio',
  satKey: '',
  satUnit: '',
  basePrice: '',
  internalCost: '',
  status: 'Activo'
};

const quotationStatusLabels = {
  draft: 'Draft',
  sent: 'Sent',
  waiting: 'Waiting',
  accepted: 'Accepted',
  rejected: 'Rejected',
  expired: 'Expired',
  cancelled: 'Cancelled'
};

const quotationActions = [
  { key: 'send', label: 'Enviar', nextStatus: 'sent' },
  { key: 'waiting', label: 'Esperando respuesta', nextStatus: 'waiting' },
  { key: 'accept', label: 'Aceptar', nextStatus: 'accepted' },
  { key: 'reject', label: 'Rechazar', nextStatus: 'rejected' },
  { key: 'expire', label: 'Expirar', nextStatus: 'expired' },
  { key: 'cancel', label: 'Cancelar', nextStatus: 'cancelled' }
];

const quotationTransitions = {
  draft: new Set(['sent', 'cancelled']),
  sent: new Set(['waiting', 'accepted', 'rejected', 'expired', 'cancelled']),
  waiting: new Set(['accepted', 'rejected', 'expired', 'cancelled']),
  accepted: new Set(),
  rejected: new Set(),
  expired: new Set(),
  cancelled: new Set()
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

function formatDate(value) {
  if (!value) {
    return '-';
  }
  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium'
  }).format(new Date(`${value}T00:00:00`));
}

function formatMoney(value) {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat('es-MX', {
    currency: 'MXN',
    style: 'currency'
  }).format(amount);
}

function getClientContact(client) {
  return client.contacts?.find((contact) => contact.is_active !== false) ?? client.contacts?.[0];
}

function getClientDisplayName(client) {
  return client?.commercial_name || client?.legal_name || 'Cliente sin nombre';
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function validateClientForm(form) {
  const errors = {};

  if (!form.commercialName.trim()) {
    errors.commercialName = 'El nombre comercial es obligatorio.';
  }

  if (!form.rfc.trim()) {
    errors.rfc = 'El RFC es obligatorio.';
  }

  if (form.email.trim() && !isValidEmail(form.email.trim())) {
    errors.email = 'Captura un correo valido.';
  }

  if (form.postalCode.trim() && !/^\d+$/.test(form.postalCode.trim())) {
    errors.postalCode = 'El codigo postal solo debe contener numeros.';
  }

  if (form.fiscalPostalCode.trim() && !/^\d+$/.test(form.fiscalPostalCode.trim())) {
    errors.fiscalPostalCode = 'El codigo postal fiscal solo debe contener numeros.';
  }

  return errors;
}

function getFirstValidationTab(errors) {
  if (errors.commercialName || errors.rfc || errors.email) {
    return 'general';
  }
  if (errors.postalCode) {
    return 'address';
  }
  if (errors.fiscalPostalCode) {
    return 'fiscal';
  }
  return 'general';
}

function toClientPayload(form) {
  const legalName = form.fiscalLegalName.trim() || form.commercialName.trim();
  const rfc = form.fiscalRfc.trim() || form.rfc.trim();
  const payload = {
    legal_name: legalName,
    commercial_name: form.commercialName.trim() || null,
    rfc: rfc || null,
    phone: form.phone.trim() || null,
    email: form.email.trim() || null,
    tax_regime: form.taxRegime.trim() || null
  };

  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined)
  );
}

function toClientCreatePayload(form) {
  const contactName = form.contactName.trim();
  return {
    ...toClientPayload(form),
    contacts: contactName
      ? [
          {
            name: contactName,
            email: form.email.trim() || null,
            phone: form.phone.trim() || null
          }
        ]
      : []
  };
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

function ClientsPage() {
  const [clients, setClients] = useState([]);
  const [form, setForm] = useState(emptyClientForm);
  const [editingClientId, setEditingClientId] = useState(null);
  const [isClientModalOpen, setIsClientModalOpen] = useState(false);
  const [clientModalTab, setClientModalTab] = useState('general');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  async function loadClients() {
    setError('');
    setIsLoading(true);
    try {
      const items = await listClients();
      setClients(Array.isArray(items) ? items : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadClients();
  }, []);

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setValidationErrors((current) => {
      if (!current[field]) {
        return current;
      }
      const next = { ...current };
      delete next[field];
      return next;
    });
  }

  function resetForm() {
    setForm(emptyClientForm);
    setEditingClientId(null);
    setIsClientModalOpen(false);
    setClientModalTab('general');
    setValidationErrors({});
    setNotice('');
    setError('');
  }

  function openNewClientModal() {
    setForm(emptyClientForm);
    setEditingClientId(null);
    setNotice('');
    setError('');
    setValidationErrors({});
    setClientModalTab('general');
    setIsClientModalOpen(true);
  }

  function startEdit(client) {
    const contact = getClientContact(client);
    setEditingClientId(client.id);
    setNotice('');
    setError('');
    setValidationErrors({});
    setClientModalTab('general');
    setIsClientModalOpen(true);
    setForm({
      commercialName: client.commercial_name ?? client.legal_name ?? '',
      rfc: client.rfc ?? '',
      contactName: contact?.name ?? '',
      phone: client.phone ?? contact?.phone ?? '',
      email: client.email ?? contact?.email ?? '',
      status: client.is_active ? 'Activo' : 'Inactivo',
      street: '',
      exteriorNumber: '',
      interiorNumber: '',
      neighborhood: '',
      city: '',
      addressState: '',
      postalCode: '',
      country: 'Mexico',
      fiscalLegalName: client.legal_name ?? '',
      fiscalRfc: client.rfc ?? '',
      fiscalPostalCode: '',
      taxRegime: client.tax_regime ?? '',
      cfdiUse: ''
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setNotice('');

    const nextValidationErrors = validateClientForm(form);
    if (Object.keys(nextValidationErrors).length) {
      setValidationErrors(nextValidationErrors);
      setClientModalTab(getFirstValidationTab(nextValidationErrors));
      return;
    }

    setIsSaving(true);

    try {
      if (editingClientId) {
        await updateClient(editingClientId, toClientPayload(form));
        setNotice('Cliente actualizado');
      } else {
        await createClient(toClientCreatePayload(form));
        setNotice('Cliente creado');
      }
      setForm(emptyClientForm);
      setEditingClientId(null);
      setIsClientModalOpen(false);
      setClientModalTab('general');
      setValidationErrors({});
      await loadClients();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCreateQuotation(client) {
    if (!window.confirm('¿Crear nueva cotización para este cliente?')) {
      return;
    }

    setError('');
    setNotice('');
    try {
      const quotation = await createQuotation({
        client_id: client.id,
        items: [],
        notes: `Cotizacion creada desde cliente ${client.legal_name}`
      });
      setNotice(`Cotizacion ${quotation.folio} creada para ${client.legal_name}`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const modalTitle = editingClientId ? 'Editar cliente' : 'Nuevo cliente';

  return (
    <section className="module-workspace clients-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <Building2 size={28} />
        </span>
        <div>
          <p>Modulo MYC SYSTEM</p>
          <h1>Clientes</h1>
          <span>Base operativa para cotizaciones, ordenes de servicio y certificados.</span>
        </div>
      </div>

      {error && !isClientModalOpen ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Listado de clientes</p>
            <h2>{isLoading ? 'Cargando...' : `${clients.length} clientes`}</h2>
          </div>
          <button className="primary-button" onClick={openNewClientModal} type="button">
            Nuevo cliente
          </button>
        </div>

        <div className="clients-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>Cliente</span>
            <span>RFC</span>
            <span>Contacto</span>
            <span>Telefono</span>
            <span>Correo</span>
            <span>Estado</span>
            <span>Acciones</span>
          </div>

          {isLoading ? (
            <div className="clients-empty">Cargando clientes...</div>
          ) : clients.length ? (
            clients.map((client) => {
              const contact = getClientContact(client);
              return (
                <div className="clients-table__row" key={client.id}>
                  <span>{client.commercial_name || client.legal_name}</span>
                  <span>{client.rfc || '-'}</span>
                  <span>{contact?.name || '-'}</span>
                  <span>{client.phone || contact?.phone || '-'}</span>
                  <span>{client.email || contact?.email || '-'}</span>
                  <span>
                    <mark className={client.is_active ? 'status-pill' : 'status-pill status-pill--muted'}>
                      {client.is_active ? 'Activo' : 'Inactivo'}
                    </mark>
                  </span>
                  <span className="clients-table__actions">
                    <button className="table-button" onClick={() => startEdit(client)} type="button">
                      Editar
                    </button>
                    <button
                      className="table-button table-button--primary"
                      onClick={() => handleCreateQuotation(client)}
                      type="button"
                    >
                      Cotizacion
                    </button>
                  </span>
                </div>
              );
            })
          ) : (
            <div className="clients-empty">Todavia no hay clientes registrados.</div>
          )}
        </div>
      </section>

      {isClientModalOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Clientes</p>
                <h2>{modalTitle}</h2>
              </div>
            </div>

            {error ? <div className="form-error dashboard-error">{error}</div> : null}
            {Object.keys(validationErrors).length ? (
              <div className="form-error dashboard-error">
                Revisa los campos marcados antes de guardar.
              </div>
            ) : null}

            <div className="client-modal-tabs" role="tablist" aria-label="Secciones del cliente">
              {clientModalTabs.map((tab) => (
                <button
                  aria-selected={clientModalTab === tab.key}
                  className={clientModalTab === tab.key ? 'client-modal-tab is-active' : 'client-modal-tab'}
                  disabled={isSaving}
                  key={tab.key}
                  onClick={() => setClientModalTab(tab.key)}
                  type="button"
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <form className="client-form client-form--modal" noValidate onSubmit={handleSubmit}>
              {clientModalTab === 'general' ? (
                <>
                  <label>
                    Nombre comercial
                    <input
                      aria-invalid={Boolean(validationErrors.commercialName)}
                      onChange={(event) => updateForm('commercialName', event.target.value)}
                      required
                      type="text"
                      value={form.commercialName}
                    />
                    {validationErrors.commercialName ? (
                      <span className="field-error">{validationErrors.commercialName}</span>
                    ) : null}
                  </label>
                  <label>
                    RFC
                    <input
                      aria-invalid={Boolean(validationErrors.rfc)}
                      maxLength={13}
                      onChange={(event) => updateForm('rfc', event.target.value.toUpperCase())}
                      required
                      type="text"
                      value={form.rfc}
                    />
                    {validationErrors.rfc ? <span className="field-error">{validationErrors.rfc}</span> : null}
                  </label>
                  <label>
                    Contacto
                    <input
                      disabled={Boolean(editingClientId)}
                      onChange={(event) => updateForm('contactName', event.target.value)}
                      type="text"
                      value={form.contactName}
                    />
                  </label>
                  <label>
                    Telefono
                    <input
                      onChange={(event) => updateForm('phone', event.target.value)}
                      type="tel"
                      value={form.phone}
                    />
                  </label>
                  <label>
                    Correo
                    <input
                      aria-invalid={Boolean(validationErrors.email)}
                      onChange={(event) => updateForm('email', event.target.value)}
                      type="email"
                      value={form.email}
                    />
                    {validationErrors.email ? <span className="field-error">{validationErrors.email}</span> : null}
                  </label>
                  <label>
                    Estado
                    <select
                      disabled
                      onChange={(event) => updateForm('status', event.target.value)}
                      value={form.status}
                    >
                      <option>Activo</option>
                      <option>Inactivo</option>
                    </select>
                  </label>
                </>
              ) : null}

              {clientModalTab === 'address' ? (
                <>
                  <label>
                    Calle
                    <input
                      onChange={(event) => updateForm('street', event.target.value)}
                      type="text"
                      value={form.street}
                    />
                  </label>
                  <label>
                    Numero exterior
                    <input
                      onChange={(event) => updateForm('exteriorNumber', event.target.value)}
                      type="text"
                      value={form.exteriorNumber}
                    />
                  </label>
                  <label>
                    Numero interior
                    <input
                      onChange={(event) => updateForm('interiorNumber', event.target.value)}
                      type="text"
                      value={form.interiorNumber}
                    />
                  </label>
                  <label>
                    Colonia
                    <input
                      onChange={(event) => updateForm('neighborhood', event.target.value)}
                      type="text"
                      value={form.neighborhood}
                    />
                  </label>
                  <label>
                    Municipio / Ciudad
                    <input
                      onChange={(event) => updateForm('city', event.target.value)}
                      type="text"
                      value={form.city}
                    />
                  </label>
                  <label>
                    Estado
                    <input
                      onChange={(event) => updateForm('addressState', event.target.value)}
                      type="text"
                      value={form.addressState}
                    />
                  </label>
                  <label>
                    Codigo postal
                    <input
                      aria-invalid={Boolean(validationErrors.postalCode)}
                      inputMode="numeric"
                      onChange={(event) => updateForm('postalCode', event.target.value.replace(/\D/g, ''))}
                      type="text"
                      value={form.postalCode}
                    />
                    {validationErrors.postalCode ? (
                      <span className="field-error">{validationErrors.postalCode}</span>
                    ) : null}
                  </label>
                  <label>
                    Pais
                    <input
                      onChange={(event) => updateForm('country', event.target.value)}
                      type="text"
                      value={form.country}
                    />
                  </label>
                </>
              ) : null}

              {clientModalTab === 'fiscal' ? (
                <>
                  <label>
                    Razon social
                    <input
                      onChange={(event) => updateForm('fiscalLegalName', event.target.value)}
                      type="text"
                      value={form.fiscalLegalName}
                    />
                  </label>
                  <label>
                    RFC fiscal
                    <input
                      maxLength={13}
                      onChange={(event) => updateForm('fiscalRfc', event.target.value.toUpperCase())}
                      type="text"
                      value={form.fiscalRfc}
                    />
                  </label>
                  <label>
                    Codigo postal fiscal
                    <input
                      aria-invalid={Boolean(validationErrors.fiscalPostalCode)}
                      inputMode="numeric"
                      onChange={(event) => updateForm('fiscalPostalCode', event.target.value.replace(/\D/g, ''))}
                      type="text"
                      value={form.fiscalPostalCode}
                    />
                    {validationErrors.fiscalPostalCode ? (
                      <span className="field-error">{validationErrors.fiscalPostalCode}</span>
                    ) : null}
                  </label>
                  <label>
                    Regimen fiscal
                    <input
                      onChange={(event) => updateForm('taxRegime', event.target.value)}
                      type="text"
                      value={form.taxRegime}
                    />
                  </label>
                  <label>
                    Uso CFDI
                    <input
                      onChange={(event) => updateForm('cfdiUse', event.target.value)}
                      type="text"
                      value={form.cfdiUse}
                    />
                  </label>
                  <div className="client-form__visual-actions">
                    <button className="table-button" disabled={isSaving} type="button">
                      Subir constancia fiscal
                    </button>
                    <button className="table-button table-button--primary" disabled={isSaving} type="button">
                      Capturar manualmente
                    </button>
                  </div>
                  <div className="client-fiscal-note">
                    Los datos fiscales completos se conectaran al modulo de facturacion.
                  </div>
                </>
              ) : null}

              <div className="client-form__actions client-form__actions--modal">
                <button className="icon-text-button" disabled={isSaving} onClick={resetForm} type="button">
                  Cancelar
                </button>
                <button className="primary-button" disabled={isSaving} type="submit">
                  {isSaving ? 'Guardando...' : editingClientId ? 'Guardar cambios' : 'Guardar cliente'}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function QuotationsPage() {
  const [salesTab, setSalesTab] = useState('quotations');
  const [quotations, setQuotations] = useState([]);
  const [clients, setClients] = useState([]);
  const [quotationForm, setQuotationForm] = useState(emptyQuotationForm);
  const [detailForm, setDetailForm] = useState(emptyQuotationForm);
  const [selectedQuotation, setSelectedQuotation] = useState(null);
  // Catalogo visual local hasta que existan endpoints backend para productos y servicios.
  const [catalogItems, setCatalogItems] = useState([]);
  const [productForm, setProductForm] = useState(emptyProductForm);
  const [editingProductId, setEditingProductId] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDetailSaving, setIsDetailSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const clientsById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients]
  );

  async function loadQuotationData() {
    setError('');
    setIsLoading(true);
    try {
      const [quotationItems, clientItems] = await Promise.all([
        listQuotations(),
        listClients()
      ]);
      setQuotations(Array.isArray(quotationItems) ? quotationItems : []);
      setClients(Array.isArray(clientItems) ? clientItems : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadQuotationData();
  }, []);

  function updateQuotationForm(field, value) {
    setQuotationForm((current) => ({ ...current, [field]: value }));
  }

  function updateDetailForm(field, value) {
    setDetailForm((current) => ({ ...current, [field]: value }));
  }

  function updateProductForm(field, value) {
    setProductForm((current) => ({ ...current, [field]: value }));
  }

  function closeQuotationModal() {
    setQuotationForm(emptyQuotationForm);
    setIsCreateModalOpen(false);
    setError('');
  }

  async function handleCreateQuotationSubmit(event) {
    event.preventDefault();
    setError('');
    setNotice('');

    if (!quotationForm.clientId) {
      setError('Selecciona un cliente para crear la cotizacion.');
      return;
    }

    setIsSaving(true);
    try {
      const quotation = await createQuotation({
        client_id: Number(quotationForm.clientId),
        valid_until: quotationForm.validUntil || null,
        notes: quotationForm.notes.trim() || null,
        items: []
      });
      setNotice(`Cotizacion ${quotation.folio} creada correctamente`);
      setQuotationForm(emptyQuotationForm);
      setIsCreateModalOpen(false);
      await loadQuotationData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function openQuotationDetail(quotation) {
    setError('');
    try {
      const detail = await getQuotation(quotation.id);
      setSelectedQuotation(detail);
      setDetailForm({
        clientId: String(detail.client_id ?? ''),
        validUntil: detail.valid_until ?? '',
        notes: detail.notes ?? ''
      });
      setIsDetailOpen(true);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function closeQuotationDetail() {
    setIsDetailOpen(false);
    setSelectedQuotation(null);
    setDetailForm(emptyQuotationForm);
    setError('');
  }

  async function handleDetailSubmit(event) {
    event.preventDefault();
    if (!selectedQuotation) {
      return;
    }

    setError('');
    setNotice('');
    setIsDetailSaving(true);
    try {
      const updated = await updateQuotation(selectedQuotation.id, {
        valid_until: detailForm.validUntil || null,
        notes: detailForm.notes.trim() || null
      });
      setSelectedQuotation(updated);
      setDetailForm({
        clientId: String(updated.client_id ?? ''),
        validUntil: updated.valid_until ?? '',
        notes: updated.notes ?? ''
      });
      setNotice(`Cotizacion ${updated.folio} actualizada`);
      await loadQuotationData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsDetailSaving(false);
    }
  }

  async function handleQuotationStatus(quotation, action) {
    const nextLabel = quotationStatusLabels[action.nextStatus] ?? action.nextStatus;
    if (!window.confirm(`¿Cambiar cotizacion ${quotation.folio} a ${nextLabel}?`)) {
      return;
    }

    setError('');
    setNotice('');
    try {
      const updated = await changeQuotationStatus(quotation.id, action.key);
      setNotice(`Cotizacion ${updated.folio} actualizada a ${quotationStatusLabels[updated.status]}`);
      setSelectedQuotation(updated);
      setDetailForm({
        clientId: String(updated.client_id ?? ''),
        validUntil: updated.valid_until ?? '',
        notes: updated.notes ?? ''
      });
      await loadQuotationData();
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function isActionAllowed(quotation, action) {
    return quotationTransitions[quotation.status]?.has(action.nextStatus) ?? false;
  }

  function openProductModal(item = null) {
    setError('');
    setNotice('');
    if (item) {
      setEditingProductId(item.id);
      setProductForm({
        name: item.name,
        type: item.type,
        satKey: item.satKey,
        satUnit: item.satUnit,
        basePrice: item.basePrice,
        internalCost: item.internalCost,
        status: item.status
      });
    } else {
      setEditingProductId(null);
      setProductForm(emptyProductForm);
    }
    setIsProductModalOpen(true);
  }

  function closeProductModal() {
    setIsProductModalOpen(false);
    setEditingProductId(null);
    setProductForm(emptyProductForm);
    setError('');
  }

  function handleProductSubmit(event) {
    event.preventDefault();
    setError('');
    setNotice('');

    if (!productForm.name.trim()) {
      setError('Captura el nombre del producto o servicio.');
      return;
    }

    const nextItem = {
      ...productForm,
      id: editingProductId ?? crypto.randomUUID(),
      name: productForm.name.trim(),
      satKey: productForm.satKey.trim(),
      satUnit: productForm.satUnit.trim(),
      basePrice: productForm.basePrice,
      internalCost: productForm.internalCost
    };

    setCatalogItems((current) =>
      editingProductId
        ? current.map((item) => (item.id === editingProductId ? nextItem : item))
        : [nextItem, ...current]
    );
    setNotice(editingProductId ? 'Producto/servicio actualizado visualmente' : 'Producto/servicio agregado visualmente');
    closeProductModal();
  }

  return (
    <section className="module-workspace quotations-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <FileText size={28} />
        </span>
        <div>
          <p>Modulo MYC SYSTEM</p>
          <h1>Ventas / Cotizaciones</h1>
          <span>Propuestas comerciales conectadas al flujo Cliente, Orden y Servicio.</span>
        </div>
      </div>

      {error && !isCreateModalOpen ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <div className="module-tabs" role="tablist" aria-label="Navegacion interna de ventas">
        <button
          aria-selected={salesTab === 'quotations'}
          className={salesTab === 'quotations' ? 'module-tab is-active' : 'module-tab'}
          onClick={() => setSalesTab('quotations')}
          type="button"
        >
          Cotizaciones
        </button>
        <button
          aria-selected={salesTab === 'catalog'}
          className={salesTab === 'catalog' ? 'module-tab is-active' : 'module-tab'}
          onClick={() => setSalesTab('catalog')}
          type="button"
        >
          Productos / Servicios
        </button>
      </div>

      {salesTab === 'quotations' ? (
      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Listado de cotizaciones</p>
            <h2>{isLoading ? 'Cargando...' : `${quotations.length} cotizaciones`}</h2>
          </div>
          <button
            className="primary-button"
            onClick={() => {
              setError('');
              setNotice('');
              setQuotationForm(emptyQuotationForm);
              setIsCreateModalOpen(true);
            }}
            type="button"
          >
            Nueva cotizacion
          </button>
        </div>

        <div className="clients-table quotations-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>Folio</span>
            <span>Cliente</span>
            <span>Asesor</span>
            <span>Fecha emision</span>
            <span>Vigencia</span>
            <span>Estado</span>
            <span>Total</span>
          </div>

          {isLoading ? (
            <div className="clients-empty">Cargando cotizaciones...</div>
          ) : quotations.length ? (
            quotations.map((quotation) => {
              const client = clientsById.get(quotation.client_id);
              return (
                <button
                  className="clients-table__row quotation-row-button"
                  key={quotation.id}
                  onClick={() => openQuotationDetail(quotation)}
                  type="button"
                >
                  <span>{quotation.folio}</span>
                  <span>{getClientDisplayName(client)}</span>
                  <span>{quotation.advisor_id ? `#${quotation.advisor_id}` : '-'}</span>
                  <span>{formatDate(quotation.issued_on)}</span>
                  <span>{formatDate(quotation.valid_until)}</span>
                  <span>
                    <mark className={`quotation-status status-${quotation.status}`}>
                      {quotationStatusLabels[quotation.status] ?? quotation.status}
                    </mark>
                  </span>
                  <span>{formatMoney(quotation.total)}</span>
                </button>
              );
            })
          ) : (
            <div className="clients-empty">Todavia no hay cotizaciones registradas.</div>
          )}
        </div>
      </section>
      ) : (
      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Catalogo visual</p>
            <h2>{catalogItems.length} productos / servicios</h2>
          </div>
          <button className="primary-button" onClick={() => openProductModal()} type="button">
            Nuevo producto/servicio
          </button>
        </div>

        <div className="client-fiscal-note catalog-note">
          Esta seccion es frontend visual. Se conectara al backend cuando exista el modulo de catalogo.
        </div>

        <div className="clients-table products-table">
          <div className="clients-table__head">
            <span>Nombre</span>
            <span>Tipo</span>
            <span>Clave SAT</span>
            <span>Unidad SAT</span>
            <span>Precio base</span>
            <span>Costo interno</span>
            <span>Estado</span>
            <span>Acciones</span>
          </div>

          {catalogItems.length ? (
            catalogItems.map((item) => (
              <div className="clients-table__row" key={item.id}>
                <span>{item.name}</span>
                <span>{item.type}</span>
                <span>{item.satKey || '-'}</span>
                <span>{item.satUnit || '-'}</span>
                <span>{formatMoney(item.basePrice)}</span>
                <span>{formatMoney(item.internalCost)}</span>
                <span>
                  <mark className={item.status === 'Activo' ? 'status-pill' : 'status-pill status-pill--muted'}>
                    {item.status}
                  </mark>
                </span>
                <span className="clients-table__actions">
                  <button className="table-button" onClick={() => openProductModal(item)} type="button">
                    Editar
                  </button>
                </span>
              </div>
            ))
          ) : (
            <div className="clients-empty">Todavia no hay productos o servicios cargados en esta vista.</div>
          )}
        </div>
      </section>
      )}

      {isCreateModalOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Cotizaciones</p>
                <h2>Nueva cotizacion</h2>
              </div>
            </div>

            {error ? <div className="form-error dashboard-error">{error}</div> : null}

            <form className="client-form client-form--modal" noValidate onSubmit={handleCreateQuotationSubmit}>
              <label>
                Cliente
                <select
                  onChange={(event) => updateQuotationForm('clientId', event.target.value)}
                  required
                  value={quotationForm.clientId}
                >
                  <option value="">Seleccionar cliente</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {getClientDisplayName(client)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Fecha vigencia
                <input
                  onChange={(event) => updateQuotationForm('validUntil', event.target.value)}
                  type="date"
                  value={quotationForm.validUntil}
                />
              </label>
              <label className="form-field--wide">
                Notas
                <textarea
                  onChange={(event) => updateQuotationForm('notes', event.target.value)}
                  rows={4}
                  value={quotationForm.notes}
                />
              </label>

              <div className="client-form__actions client-form__actions--modal">
                <button className="icon-text-button" disabled={isSaving} onClick={closeQuotationModal} type="button">
                  Cancelar
                </button>
                <button className="primary-button" disabled={isSaving} type="submit">
                  {isSaving ? 'Guardando...' : 'Crear cotizacion'}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {isDetailOpen && selectedQuotation ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-detail-modal" aria-modal="true" role="dialog">
            <div className="quotation-detail-header">
              <div>
                <p>Cotizacion</p>
                <h2>{selectedQuotation.folio}</h2>
                <span>{getClientDisplayName(clientsById.get(selectedQuotation.client_id))}</span>
              </div>
              <mark className={`quotation-status quotation-status--large status-${selectedQuotation.status}`}>
                {quotationStatusLabels[selectedQuotation.status] ?? selectedQuotation.status}
              </mark>
              <button
                className="icon-text-button"
                onClick={closeQuotationDetail}
                type="button"
              >
                Cerrar
              </button>
            </div>

            <section className="quotation-section">
              <div className="quotation-section__title">
                <p>Resumen economico</p>
                <h3>Total cotizado</h3>
              </div>
              <div className="quotation-summary">
                <div>
                  <span>Subtotal</span>
                  <strong>{formatMoney(selectedQuotation.subtotal)}</strong>
                </div>
                <div>
                  <span>IVA</span>
                  <strong>{formatMoney(selectedQuotation.tax_total)}</strong>
                </div>
                <div className="quotation-total-card">
                  <span>Total</span>
                  <strong>{formatMoney(selectedQuotation.total)}</strong>
                </div>
              </div>
            </section>

            <form className="quotation-detail-form" onSubmit={handleDetailSubmit}>
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Datos comerciales</p>
                  <h3>Ficha editable</h3>
                </div>
                <div className="quotation-commercial-grid">
                  <article>
                    <span>Cliente</span>
                    <strong>{getClientDisplayName(clientsById.get(selectedQuotation.client_id))}</strong>
                  </article>
                  <article>
                    <span>Emision</span>
                    <strong>{formatDate(selectedQuotation.issued_on)}</strong>
                  </article>
                  <label>
                    Vigencia
                    <input
                      onChange={(event) => updateDetailForm('validUntil', event.target.value)}
                      type="date"
                      value={detailForm.validUntil}
                    />
                  </label>
                  <article>
                    <span>Asesor</span>
                    <strong>{selectedQuotation.advisor_id ? `#${selectedQuotation.advisor_id}` : 'Sin asesor asignado'}</strong>
                  </article>
                </div>
              </section>

              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Notas</p>
                  <h3>Condiciones y observaciones</h3>
                </div>
                <label className="quotation-notes-field">
                  <textarea
                    onChange={(event) => updateDetailForm('notes', event.target.value)}
                    placeholder="Sin notas registradas."
                    rows={4}
                    value={detailForm.notes}
                  />
                </label>
              </section>

              <div className="quotation-detail-save">
                <span>Por ahora se editan vigencia y notas. Partidas y PDF se conectaran despues.</span>
                <button className="primary-button" disabled={isDetailSaving} type="submit">
                  {isDetailSaving ? 'Guardando...' : 'Guardar cambios'}
                </button>
              </div>
            </form>

            <section className="quotation-section">
              <div className="quotation-section__title">
                <p>Acciones de estado</p>
                <h3>Flujo comercial</h3>
              </div>
              <div className="quotation-actions">
                {quotationActions.map((action) => (
                  <button
                    className="table-button"
                    disabled={!isActionAllowed(selectedQuotation, action)}
                    key={action.key}
                    onClick={() => handleQuotationStatus(selectedQuotation, action)}
                    type="button"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            </section>

            <section className="quotation-future-area">
              <h3>Preparado para siguientes iteraciones</h3>
              <div>
                <span>Partidas</span>
                <span>IVA</span>
                <span>PDF</span>
                <span>Historial</span>
              </div>
            </section>
          </section>
        </div>
      ) : null}

      {isProductModalOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Catalogo</p>
                <h2>{editingProductId ? 'Editar producto/servicio' : 'Nuevo producto/servicio'}</h2>
              </div>
            </div>

            {error ? <div className="form-error dashboard-error">{error}</div> : null}

            <form className="client-form client-form--modal" noValidate onSubmit={handleProductSubmit}>
              <label>
                Nombre
                <input
                  onChange={(event) => updateProductForm('name', event.target.value)}
                  required
                  type="text"
                  value={productForm.name}
                />
              </label>
              <label>
                Tipo
                <select onChange={(event) => updateProductForm('type', event.target.value)} value={productForm.type}>
                  <option>Producto</option>
                  <option>Servicio</option>
                </select>
              </label>
              <label>
                Clave SAT
                <input
                  onChange={(event) => updateProductForm('satKey', event.target.value)}
                  type="text"
                  value={productForm.satKey}
                />
              </label>
              <label>
                Unidad SAT
                <input
                  onChange={(event) => updateProductForm('satUnit', event.target.value)}
                  type="text"
                  value={productForm.satUnit}
                />
              </label>
              <label>
                Precio base
                <input
                  min="0"
                  onChange={(event) => updateProductForm('basePrice', event.target.value)}
                  step="0.01"
                  type="number"
                  value={productForm.basePrice}
                />
              </label>
              <label>
                Costo interno
                <input
                  min="0"
                  onChange={(event) => updateProductForm('internalCost', event.target.value)}
                  step="0.01"
                  type="number"
                  value={productForm.internalCost}
                />
              </label>
              <label>
                Estado
                <select onChange={(event) => updateProductForm('status', event.target.value)} value={productForm.status}>
                  <option>Activo</option>
                  <option>Inactivo</option>
                </select>
              </label>

              <div className="client-form__actions client-form__actions--modal">
                <button className="icon-text-button" onClick={closeProductModal} type="button">
                  Cancelar
                </button>
                <button className="primary-button" type="submit">
                  {editingProductId ? 'Guardar cambios' : 'Agregar visualmente'}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
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
      {selectedModule?.key === 'clients' ? (
        <ClientsPage />
      ) : selectedModule?.key === 'quotations' ? (
        <QuotationsPage />
      ) : selectedModule ? (
        <ModulePage module={selectedModule} timestamp={now} />
      ) : (
        <DashboardPage user={user} />
      )}
    </AppLayout>
  );
}
