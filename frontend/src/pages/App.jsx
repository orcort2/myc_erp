import {
  BadgeCheck,
  Banknote,
  Boxes,
  Building2,
  ClipboardList,
  Download,
  FileCheck2,
  FileText,
  Gauge,
  LogOut,
  MessageSquareText,
  Settings,
  ShieldCheck,
  Upload,
  UserRound
} from 'lucide-react';
import React from 'react';
import { useEffect, useMemo, useState } from 'react';

import mycLogo from '../assets/myc-logo.png';
import {
  changeQuotationStatus,
  clearTokens,
  createClient,
  createCatalogItem,
  createQuotation,
  createQuotationItem,
  deleteCatalogItem,
  getAccessToken,
  getCurrentUser,
  getDashboardCounts,
  getQuotation,
  getQuotationPdfUrl,
  listCatalogItems,
  listClients,
  listQuotations,
  login,
  register,
  downloadQuotationPdf,
  updateCatalogItem,
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

const emptyQuotationItemForm = {
  catalogItemId: '',
  description: '',
  quantity: '1',
  unit: 'Servicio',
  unitPrice: '',
  currency: 'MXN',
  discount: '0',
  observations: '',
  satKey: ''
};

const emptyProductForm = {
  category: '',
  internalKey: '',
  name: '',
  description: '',
  type: 'Servicio',
  commodity: 'calibration',
  calibrationScope: 'traceable',
  quotationLegend: '',
  satKey: '',
  satUnit: '',
  internalUnit: 'service',
  customInternalUnit: '',
  basePrice: '',
  sourceCurrency: 'MXN',
  exchangeRate: '1',
  internalCost: '',
  costCurrency: 'MXN',
  margin: '',
  taxObject: 'iva_16',
  status: 'Activo'
};

const clientTemplateColumns = [
  'Nombre comercial',
  'Razon social',
  'RFC',
  'Contacto principal',
  'Correo',
  'Telefono',
  'Pais',
  'Calle',
  'Numero exterior',
  'Numero interior',
  'Colonia',
  'Municipio / Ciudad',
  'Estado',
  'Codigo postal',
  'Regimen fiscal',
  'Uso CFDI',
  'Estado del cliente'
];

const catalogTemplateColumns = [
  'Tipo',
  'Commodity',
  'Categoria',
  'Clave interna',
  'Nombre',
  'Descripcion',
  'Clave SAT',
  'Unidad SAT',
  'Unidad interna',
  'Unidad interna personalizada',
  'Precio origen',
  'Moneda origen',
  'Tipo de cambio',
  'Costo interno',
  'Moneda de costo',
  'Margen %',
  'Precio final MXN',
  'Objeto impuesto',
  'Estado'
];

const serviceCategories = [
  'Calibracion',
  'Mantenimiento',
  'Calificacion',
  'Validacion',
  'Capacitacion',
  'Consultoria'
];

const productCategories = [
  'Patrones',
  'Equipos',
  'Accesorios',
  'Consumibles'
];

const validCatalogCurrencies = new Set(['MXN', 'USD', 'EUR']);

const catalogTypeToApi = {
  Producto: 'product',
  Servicio: 'service'
};

const catalogTypeFromApi = {
  product: 'Producto',
  service: 'Servicio'
};

const catalogCommodityOptions = [
  { value: 'calibration', label: 'Calibracion' },
  { value: 'maintenance', label: 'Mantenimiento' },
  { value: 'repair', label: 'Reparacion' },
  { value: 'sale', label: 'Venta' },
  { value: 'general_service', label: 'Servicio general' }
];

const calibrationScopeOptions = [
  { value: 'accredited_iso_17025', label: 'Acreditado ISO/IEC 17025:2017' },
  { value: 'traceable', label: 'Trazable' },
  { value: 'accredited_linked_lab', label: 'Acreditado laboratorio vinculado' }
];

const internalUnitOptions = [
  { value: 'service', label: 'Servicio' },
  { value: 'piece', label: 'Pieza' },
  { value: 'equipment', label: 'Equipo' },
  { value: 'hour', label: 'Hora' },
  { value: 'day', label: 'Dia' },
  { value: 'package', label: 'Paquete' },
  { value: 'lot', label: 'Lote' },
  { value: 'meter', label: 'Metro' },
  { value: 'kilogram', label: 'Kilogramo' },
  { value: 'liter', label: 'Litro' },
  { value: 'other', label: 'Otra' }
];

const taxObjectOptions = [
  { value: 'iva_16', label: 'IVA 16%' },
  { value: 'iva_0', label: 'IVA 0%' },
  { value: 'exempt', label: 'Exento' },
  { value: 'not_subject', label: 'No sujeto' }
];

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

function calculateFinalPriceMxn({ basePrice, exchangeRate, margin }) {
  const price = Number(basePrice || 0);
  const rate = Number(exchangeRate || 1);
  const marginFactor = 1 + Number(margin || 0) / 100;
  return price * rate * marginFactor;
}

function mapCatalogItemFromApi(item) {
  return {
    id: item.id,
    type: catalogTypeFromApi[item.item_type] ?? item.item_type,
    itemType: item.item_type,
    commodity: item.commodity,
    calibrationScope: item.calibration_scope ?? '',
    quotationLegend: item.quotation_legend ?? '',
    category: item.category ?? '',
    internalKey: item.internal_key ?? '',
    name: item.name ?? '',
    description: item.description ?? '',
    satKey: item.sat_key ?? '',
    satUnit: item.sat_unit ?? '',
    internalUnit: item.internal_unit ?? 'service',
    customInternalUnit: item.custom_internal_unit ?? '',
    basePrice: String(item.origin_price ?? ''),
    sourceCurrency: item.origin_currency ?? 'MXN',
    exchangeRate: String(item.exchange_rate ?? '1'),
    internalCost: item.internal_cost == null ? '' : String(item.internal_cost),
    costCurrency: item.cost_currency ?? 'MXN',
    margin: String(item.margin_percent ?? ''),
    finalPriceMxn: Number(item.final_price_mxn ?? 0),
    taxObject: item.tax_object ?? 'iva_16',
    taxRate: Number(item.tax_rate ?? 16),
    status: item.is_active === false ? 'Inactivo' : 'Activo'
  };
}

function mapCatalogPayloadFromForm(form) {
  const commodity = form.commodity || 'general_service';
  return {
    item_type: catalogTypeToApi[form.type] ?? form.type,
    commodity,
    category: form.category.trim(),
    name: form.name.trim(),
    description: form.description.trim() || null,
    sat_key: form.satKey.trim() || null,
    sat_unit: form.satUnit.trim() || null,
    internal_unit: form.internalUnit || 'service',
    custom_internal_unit: form.internalUnit === 'other' ? form.customInternalUnit.trim() || null : null,
    origin_price: Number(form.basePrice || 0),
    origin_currency: form.sourceCurrency,
    exchange_rate: Number(form.exchangeRate || 1),
    margin_percent: Number(form.margin || 0),
    internal_cost: form.internalCost === '' ? null : Number(form.internalCost),
    cost_currency: form.internalCost === '' ? null : form.costCurrency,
    calibration_scope: commodity === 'calibration' ? form.calibrationScope : null,
    quotation_legend: commodity === 'general_service' ? form.quotationLegend.trim() : form.quotationLegend.trim() || null,
    tax_object: form.taxObject || 'iva_16'
  };
}

function normalizeKey(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');
}

function toCsvValue(value) {
  const text = String(value ?? '');
  return `"${text.replace(/"/g, '""')}"`;
}

function downloadCsv(filename, columns, rows = []) {
  const content = [
    columns.map(toCsvValue).join(','),
    ...rows.map((row) => columns.map((column) => toCsvValue(row[column])).join(','))
  ].join('\n');
  const blob = new Blob([`\ufeff${content}`], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function parseDelimitedText(text) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    return { columns: [], rows: [] };
  }

  const separator = lines[0].includes('\t') ? '\t' : ',';
  const columns = lines[0].split(separator).map((column) => column.replace(/^"|"$/g, '').trim());
  const rows = lines.slice(1).map((line) => {
    const values = line.split(separator).map((value) => value.replace(/^"|"$/g, '').trim());
    return Object.fromEntries(columns.map((column, index) => [column, values[index] ?? '']));
  });

  return { columns, rows };
}

function getRowValue(row, names) {
  const entries = Object.entries(row).map(([key, value]) => [normalizeKey(key), value]);
  for (const name of names) {
    const match = entries.find(([key]) => key === normalizeKey(name));
    if (match) {
      return match[1] ?? '';
    }
  }
  return '';
}

function buildClientImportPreview(rows, existingClients) {
  const existingRfc = new Set(existingClients.map((client) => normalizeKey(client.rfc)).filter(Boolean));
  const existingEmail = new Set(existingClients.map((client) => normalizeKey(client.email)).filter(Boolean));
  const existingName = new Set(
    existingClients.map((client) => normalizeKey(client.commercial_name || client.legal_name)).filter(Boolean)
  );

  const seenRfc = new Set();
  const seenEmail = new Set();
  const seenName = new Set();

  const reviewedRows = rows.map((row, index) => {
    const name = row['Nombre comercial'] || row.nombre || row.Cliente || '';
    const rfc = row.RFC || row.rfc || '';
    const email = row.Correo || row.Email || row.email || '';
    const postalCode = row['Codigo postal'] || row['Código postal'] || '';
    const nameKey = normalizeKey(name);
    const rfcKey = normalizeKey(rfc);
    const emailKey = normalizeKey(email);
    const errors = [];
    const duplicates = [];

    if (!name.trim()) {
      errors.push('Nombre comercial obligatorio');
    }
    if (email.trim() && !isValidEmail(email.trim())) {
      errors.push('Correo invalido');
    }
    if (postalCode.trim() && !/^\d+$/.test(postalCode.trim())) {
      errors.push('Codigo postal no numerico');
    }
    if (rfcKey && (existingRfc.has(rfcKey) || seenRfc.has(rfcKey))) {
      duplicates.push('RFC');
    }
    if (emailKey && (existingEmail.has(emailKey) || seenEmail.has(emailKey))) {
      duplicates.push('Correo');
    }
    if (nameKey && (existingName.has(nameKey) || seenName.has(nameKey))) {
      duplicates.push('Nombre');
    }

    if (rfcKey) seenRfc.add(rfcKey);
    if (emailKey) seenEmail.add(emailKey);
    if (nameKey) seenName.add(nameKey);

    return {
      id: `${index}-${nameKey || 'cliente'}`,
      name: name || '-',
      rfc: rfc || '-',
      email: email || '-',
      status: errors.length ? 'error' : duplicates.length ? 'duplicate' : 'valid',
      errors,
      duplicates,
      raw: row
    };
  });

  return {
    rows: reviewedRows,
    valid: reviewedRows.filter((row) => row.status === 'valid'),
    duplicates: reviewedRows.filter((row) => row.status === 'duplicate'),
    errors: reviewedRows.filter((row) => row.status === 'error')
  };
}

function buildCatalogImportPreview(rows, existingItems) {
  const existingName = new Set(existingItems.map((item) => normalizeKey(item.name)).filter(Boolean));
  const existingInternalKey = new Set(existingItems.map((item) => normalizeKey(item.internalKey)).filter(Boolean));
  const existingCategoryName = new Set(
    existingItems.map((item) => `${normalizeKey(item.category)}|${normalizeKey(item.name)}`).filter((value) => value !== '|')
  );
  const seenName = new Set();
  const seenInternalKey = new Set();
  const seenCategoryName = new Set();

  const reviewedRows = rows.map((row, index) => {
    const type = getRowValue(row, ['Tipo']);
    const category = getRowValue(row, ['Categoria', 'Categoría']);
    const internalKey = getRowValue(row, ['Clave interna']);
    const name = getRowValue(row, ['Nombre']);
    const price = getRowValue(row, ['Precio origen']);
    const currency = getRowValue(row, ['Moneda origen']);
    const nameKey = normalizeKey(name);
    const internalKeyKey = normalizeKey(internalKey);
    const categoryNameKey = `${normalizeKey(category)}|${nameKey}`;
    const errors = [];
    const duplicates = [];

    if (!name.trim()) errors.push('Nombre obligatorio');
    if (!type.trim()) errors.push('Tipo obligatorio');
    if (!category.trim()) errors.push('Categoria obligatoria');
    if (price.trim() && Number.isNaN(Number(price))) errors.push('Precio no numerico');
    if (currency.trim() && !validCatalogCurrencies.has(currency.trim().toUpperCase())) {
      errors.push('Moneda no valida');
    }
    if (nameKey && (existingName.has(nameKey) || seenName.has(nameKey))) duplicates.push('Nombre');
    if (internalKeyKey && (existingInternalKey.has(internalKeyKey) || seenInternalKey.has(internalKeyKey))) {
      duplicates.push('Clave interna');
    }
    if (nameKey && category.trim() && (existingCategoryName.has(categoryNameKey) || seenCategoryName.has(categoryNameKey))) {
      duplicates.push('Categoria + nombre');
    }

    if (nameKey) seenName.add(nameKey);
    if (internalKeyKey) seenInternalKey.add(internalKeyKey);
    if (nameKey && category.trim()) seenCategoryName.add(categoryNameKey);

    return {
      id: `${index}-${nameKey || 'concepto'}`,
      name: name || '-',
      type: type || '-',
      category: category || '-',
      price: price || '-',
      currency: currency || '-',
      status: errors.length ? 'error' : duplicates.length ? 'duplicate' : 'valid',
      errors,
      duplicates,
      raw: row
    };
  });

  return {
    rows: reviewedRows,
    valid: reviewedRows.filter((row) => row.status === 'valid'),
    duplicates: reviewedRows.filter((row) => row.status === 'duplicate'),
    errors: reviewedRows.filter((row) => row.status === 'error')
  };
}

function getQuotationItems(quotation) {
  return Array.isArray(quotation?.items) ? quotation.items.filter((item) => item.is_active !== false) : [];
}

function calculateLineAmounts(item) {
  const quantity = Number(item.quantity || 0);
  const unitPrice = Number(item.unit_price ?? item.unitPrice ?? 0);
  const discount = Number(item.discount_percent ?? item.discount ?? 0);
  const taxRate = Number(item.tax_rate ?? item.taxRate ?? 16);
  const amount = quantity * unitPrice;
  const discountAmount = amount * (discount / 100);
  const subtotal = Math.max(amount - discountAmount, 0);
  const tax = subtotal * (taxRate / 100);
  return { amount, discountAmount, subtotal, tax, total: subtotal + tax };
}

function calculateQuotationSummary(quotation) {
  const items = getQuotationItems(quotation);
  const subtotal = items.length
    ? items.reduce((total, item) => total + calculateLineAmounts(item).subtotal, 0)
    : Number(quotation?.subtotal ?? 0);
  const tax = items.length
    ? items.reduce((total, item) => total + calculateLineAmounts(item).tax, 0)
    : Number(quotation?.tax_total ?? 0);
  const total = items.length ? subtotal + tax : Number(quotation?.total ?? 0);
  return { subtotal, tax, total };
}

function calculateQuotationDraftSummary(quotation, draftItems = []) {
  const savedSubtotal = getQuotationItems(quotation).reduce(
    (total, item) => total + calculateLineAmounts(item).subtotal,
    0
  );
  const draftSubtotal = draftItems.reduce(
    (total, item) => total + calculateLineAmounts(item).subtotal,
    0
  );
  const savedTax = getQuotationItems(quotation).reduce(
    (total, item) => total + calculateLineAmounts(item).tax,
    0
  );
  const draftTax = draftItems.reduce(
    (total, item) => total + calculateLineAmounts(item).tax,
    0
  );
  const fallbackSubtotal = Number(quotation?.subtotal ?? 0);
  const subtotal = savedSubtotal || draftItems.length ? savedSubtotal + draftSubtotal : fallbackSubtotal;
  const tax = savedSubtotal || draftItems.length ? savedTax + draftTax : Number(quotation?.tax_total ?? 0);
  return { subtotal, tax, total: subtotal + tax };
}

function totalToSpanishText(value) {
  const amount = Number(value || 0);
  return `${formatMoney(amount)} MXN`;
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
  const [isClientImportOpen, setIsClientImportOpen] = useState(false);
  const [clientImportFileName, setClientImportFileName] = useState('');
  const [clientImportColumns, setClientImportColumns] = useState([]);
  const [clientImportPreview, setClientImportPreview] = useState(null);
  const [clientImportMessage, setClientImportMessage] = useState('');
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

  function closeClientImportModal() {
    setIsClientImportOpen(false);
    setClientImportFileName('');
    setClientImportColumns([]);
    setClientImportPreview(null);
    setClientImportMessage('');
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

  function downloadClientTemplate() {
    downloadCsv('plantilla_clientes_myc.csv', clientTemplateColumns, [
      {
        'Nombre comercial': 'Cliente Demo',
        'Razon social': 'Cliente Demo SA de CV',
        RFC: 'CDE010101AB1',
        'Contacto principal': 'Contacto Compras',
        Correo: 'compras@cliente.com',
        Telefono: '5555555555',
        Pais: 'Mexico',
        Calle: 'Calle ejemplo',
        'Numero exterior': '100',
        'Numero interior': '',
        Colonia: 'Centro',
        'Municipio / Ciudad': 'Ciudad de Mexico',
        Estado: 'CDMX',
        'Codigo postal': '01000',
        'Regimen fiscal': '601',
        'Uso CFDI': 'G03',
        'Estado del cliente': 'Activo'
      }
    ]);
  }

  function exportClients() {
    const rows = clients.map((client) => {
      const contact = getClientContact(client);
      return {
        'Nombre comercial': client.commercial_name ?? '',
        'Razon social': client.legal_name ?? '',
        RFC: client.rfc ?? '',
        'Contacto principal': contact?.name ?? '',
        Correo: client.email ?? contact?.email ?? '',
        Telefono: client.phone ?? contact?.phone ?? '',
        Pais: '',
        Calle: '',
        'Numero exterior': '',
        'Numero interior': '',
        Colonia: '',
        'Municipio / Ciudad': '',
        Estado: '',
        'Codigo postal': '',
        'Regimen fiscal': client.tax_regime ?? '',
        'Uso CFDI': '',
        'Estado del cliente': client.is_active ? 'Activo' : 'Inactivo'
      };
    });
    downloadCsv('clientes_myc_export.csv', clientTemplateColumns, rows);
  }

  function downloadClientImportErrors() {
    if (!clientImportPreview?.errors.length) {
      return;
    }
    const rows = clientImportPreview.errors.map((row) => ({
      ...row.raw,
      Errores: row.errors.join(' | ')
    }));
    downloadCsv('clientes_myc_errores.csv', [...clientImportColumns, 'Errores'], rows);
  }

  function handleClientImportFile(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setClientImportFileName(file.name);
    setClientImportMessage('');

    if (/\.(xlsx|xls)$/i.test(file.name)) {
      setClientImportColumns(clientTemplateColumns);
      setClientImportPreview(buildClientImportPreview([], clients));
      setClientImportMessage('Archivo Excel recibido. La lectura real de XLSX se conectara cuando el backend o parser dedicado este listo; por ahora usa CSV exportado desde Excel para vista previa.');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const { columns, rows } = parseDelimitedText(String(reader.result ?? ''));
      setClientImportColumns(columns);
      setClientImportPreview(buildClientImportPreview(rows, clients));
    };
    reader.readAsText(file);
  }

  function confirmClientImport() {
    setClientImportMessage('Importacion preparada visualmente. No se enviaron datos al backend en esta version.');
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
          <div className="toolbar-actions">
            <button className="table-button" onClick={() => setIsClientImportOpen(true)} type="button">
              <Upload size={16} />
              Importar Excel
            </button>
            <button className="table-button" onClick={exportClients} type="button">
              <Download size={16} />
              Exportar Excel
            </button>
            <button className="table-button" onClick={downloadClientTemplate} type="button">
              <Download size={16} />
              Descargar plantilla
            </button>
            <button className="primary-button" onClick={openNewClientModal} type="button">
              Nuevo cliente
            </button>
          </div>
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

      {isClientImportOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal import-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Clientes</p>
                <h2>Importar clientes</h2>
              </div>
              <button className="icon-text-button" onClick={closeClientImportModal} type="button">
                Cerrar
              </button>
            </div>

            <div className="import-upload-zone">
              <label>
                Archivo Excel o CSV
                <input accept=".xlsx,.xls,.csv,.tsv" onChange={handleClientImportFile} type="file" />
              </label>
              <div>
                <strong>{clientImportFileName || 'Sin archivo seleccionado'}</strong>
                <span>La importacion no se ejecuta automaticamente. Primero se revisa la vista previa.</span>
              </div>
            </div>

            {clientImportMessage ? <div className="client-fiscal-note">{clientImportMessage}</div> : null}

            <div className="import-template-grid">
              <article>
                <span>Columnas detectadas</span>
                <strong>{clientImportColumns.length}</strong>
              </article>
              <article>
                <span>Registros validos</span>
                <strong>{clientImportPreview?.valid.length ?? 0}</strong>
              </article>
              <article>
                <span>Posibles duplicados</span>
                <strong>{clientImportPreview?.duplicates.length ?? 0}</strong>
              </article>
              <article>
                <span>Con errores</span>
                <strong>{clientImportPreview?.errors.length ?? 0}</strong>
              </article>
            </div>

            <section className="import-preview-section">
              <h3>Columnas esperadas / detectadas</h3>
              <div className="import-chip-list">
                {(clientImportColumns.length ? clientImportColumns : clientTemplateColumns).map((column) => (
                  <span key={column}>{column}</span>
                ))}
              </div>
            </section>

            <section className="import-preview-section">
              <h3>Vista previa</h3>
              <div className="import-preview-list">
                {clientImportPreview?.rows.length ? (
                  clientImportPreview.rows.slice(0, 8).map((row) => (
                    <article className={`import-row import-row--${row.status}`} key={row.id}>
                      <strong>{row.name}</strong>
                      <span>{row.rfc} · {row.email}</span>
                      <small>
                        {row.status === 'valid'
                          ? 'Valido'
                          : row.status === 'duplicate'
                            ? `Duplicado posible: ${row.duplicates.join(', ')}`
                            : row.errors.join(', ')}
                      </small>
                    </article>
                  ))
                ) : (
                  <div className="clients-empty">Sube un CSV exportado desde Excel para ver registros en esta version.</div>
                )}
              </div>
            </section>

            <div className="client-form__actions client-form__actions--modal">
              <button
                className="table-button"
                disabled={!clientImportPreview?.errors.length}
                onClick={downloadClientImportErrors}
                type="button"
              >
                Descargar errores
              </button>
              <button className="icon-text-button" onClick={closeClientImportModal} type="button">
                Cancelar
              </button>
              <button
                className="primary-button"
                disabled={!clientImportPreview?.valid.length}
                onClick={confirmClientImport}
                type="button"
              >
                Confirmar importacion
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}

function QuotationsPage() {
  const [salesTab, setSalesTab] = useState('quotations');
  const [quotationDetailTab, setQuotationDetailTab] = useState('info');
  const [quotations, setQuotations] = useState([]);
  const [clients, setClients] = useState([]);
  const [quotationForm, setQuotationForm] = useState(emptyQuotationForm);
  const [detailForm, setDetailForm] = useState(emptyQuotationForm);
  const [draftItems, setDraftItems] = useState([]);
  const [selectedQuotation, setSelectedQuotation] = useState(null);
  const [catalogItems, setCatalogItems] = useState([]);
  const [productForm, setProductForm] = useState(emptyProductForm);
  const [editingProductId, setEditingProductId] = useState(null);
  const [catalogFilters, setCatalogFilters] = useState({
    type: 'Todos',
    category: '',
    currency: 'Todas',
    status: 'Todos',
    search: ''
  });
  const [catalogImportFileName, setCatalogImportFileName] = useState('');
  const [catalogImportColumns, setCatalogImportColumns] = useState([]);
  const [catalogImportPreview, setCatalogImportPreview] = useState(null);
  const [catalogImportMessage, setCatalogImportMessage] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [isCatalogImportOpen, setIsCatalogImportOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDetailSaving, setIsDetailSaving] = useState(false);
  const [savingDraftIds, setSavingDraftIds] = useState(new Set());
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const clientsById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients]
  );

  const filteredCatalogItems = useMemo(
    () =>
      catalogItems.filter((item) => {
        const matchesType = catalogFilters.type === 'Todos' || item.type === catalogFilters.type;
        const matchesCategory =
          !catalogFilters.category || normalizeKey(item.category).includes(normalizeKey(catalogFilters.category));
        const matchesCurrency = catalogFilters.currency === 'Todas' || item.sourceCurrency === catalogFilters.currency;
        const matchesStatus = catalogFilters.status === 'Todos' || item.status === catalogFilters.status;
        const searchKey = normalizeKey(`${item.name} ${item.internalKey} ${item.category}`);
        const matchesSearch = !catalogFilters.search || searchKey.includes(normalizeKey(catalogFilters.search));
        return matchesType && matchesCategory && matchesCurrency && matchesStatus && matchesSearch;
      }),
    [catalogFilters, catalogItems]
  );


  async function loadQuotationData() {
    setError('');
    setIsLoading(true);
    try {
      const [quotationItems, clientItems, catalogApiItems] = await Promise.all([
        listQuotations(),
        listClients(),
        listCatalogItems({ is_active: true })
      ]);
      setQuotations(Array.isArray(quotationItems) ? quotationItems : []);
      setClients(Array.isArray(clientItems) ? clientItems : []);
      setCatalogItems(
        Array.isArray(catalogApiItems) ? catalogApiItems.map(mapCatalogItemFromApi) : []
      );
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
      setQuotationDetailTab('info');
      setIsDetailOpen(true);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function closeQuotationDetail() {
    setIsDetailOpen(false);
    setSelectedQuotation(null);
    setDetailForm(emptyQuotationForm);
    setDraftItems([]);
    setQuotationDetailTab('info');
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

  function openQuotationPdf(mode = 'view') {
    if (!selectedQuotation) return;
    const url = getQuotationPdfUrl(selectedQuotation.id);
    const pdfWindow = window.open(url, '_blank', 'noopener,noreferrer');
    if (mode === 'print' && pdfWindow) {
      pdfWindow.addEventListener('load', () => {
        pdfWindow.focus();
        pdfWindow.print();
      });
    }
  }

  async function handleDownloadQuotationPdf() {
    if (!selectedQuotation) return;
    setError('');
    setNotice('');
    try {
      const { blob, filename } = await downloadQuotationPdf(selectedQuotation.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setNotice(`PDF ${filename} generado correctamente`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function openProductModal(item = null) {
    setError('');
    setNotice('');
    if (item) {
      setEditingProductId(item.id);
      setProductForm({
        category: item.category,
        internalKey: item.internalKey,
        name: item.name,
        description: item.description,
        type: item.type,
        commodity: item.commodity,
        calibrationScope: item.calibrationScope || 'traceable',
        quotationLegend: item.quotationLegend,
        satKey: item.satKey,
        satUnit: item.satUnit,
        internalUnit: item.internalUnit,
        customInternalUnit: item.customInternalUnit,
        basePrice: item.basePrice,
        sourceCurrency: item.sourceCurrency,
        exchangeRate: item.exchangeRate,
        internalCost: item.internalCost,
        costCurrency: item.costCurrency,
        margin: item.margin,
        taxObject: item.taxObject,
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

  async function handleProductSubmit(event) {
    event.preventDefault();
    setError('');
    setNotice('');

    if (!productForm.name.trim()) {
      setError('Captura el nombre del producto o servicio.');
      return;
    }
    if (!productForm.type.trim() || !productForm.category.trim()) {
      setError('Selecciona tipo y categoria del concepto.');
      return;
    }
    if (productForm.basePrice && Number.isNaN(Number(productForm.basePrice))) {
      setError('El precio origen debe ser numerico.');
      return;
    }
    if (!validCatalogCurrencies.has(productForm.sourceCurrency)) {
      setError('Selecciona una moneda origen valida.');
      return;
    }
    if (productForm.commodity === 'calibration' && !productForm.calibrationScope) {
      setError('Selecciona el alcance de calibracion.');
      return;
    }
    if (productForm.commodity === 'general_service' && !productForm.quotationLegend.trim()) {
      setError('Captura la leyenda para cotizacion del servicio general.');
      return;
    }
    if (productForm.internalUnit === 'other' && !productForm.customInternalUnit.trim()) {
      setError('Captura la unidad interna personalizada.');
      return;
    }

    setIsSaving(true);
    try {
      const payload = mapCatalogPayloadFromForm(productForm);
      const saved = editingProductId
        ? await updateCatalogItem(editingProductId, payload)
        : await createCatalogItem(payload);
      const mapped = mapCatalogItemFromApi(saved);
      setCatalogItems((current) =>
        editingProductId
          ? current.map((item) => (item.id === editingProductId ? mapped : item))
          : [mapped, ...current]
      );
      setNotice(editingProductId ? 'Producto/servicio actualizado' : 'Producto/servicio agregado al catalogo');
      closeProductModal();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteCatalogItem(item) {
    if (!window.confirm(`¿Desactivar ${item.name} del Catalogo MYC?`)) {
      return;
    }
    setError('');
    setNotice('');
    try {
      await deleteCatalogItem(item.id);
      setCatalogItems((current) => current.filter((catalogItem) => catalogItem.id !== item.id));
      setNotice('Producto/servicio desactivado del catalogo');
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function updateCatalogFilter(field, value) {
    setCatalogFilters((current) => ({ ...current, [field]: value }));
  }

  function openCatalogImportModal() {
    setCatalogImportFileName('');
    setCatalogImportColumns([]);
    setCatalogImportPreview(null);
    setCatalogImportMessage('');
    setIsCatalogImportOpen(true);
  }

  function closeCatalogImportModal() {
    setIsCatalogImportOpen(false);
    setCatalogImportFileName('');
    setCatalogImportColumns([]);
    setCatalogImportPreview(null);
    setCatalogImportMessage('');
  }

  function handleCatalogImportFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    setCatalogImportFileName(file.name);
    setCatalogImportMessage('');
    if (/\.(xlsx|xls)$/i.test(file.name)) {
      setCatalogImportColumns(catalogTemplateColumns);
      setCatalogImportPreview(buildCatalogImportPreview([], catalogItems));
      setCatalogImportMessage('Archivo Excel recibido. La lectura real XLSX se conectara despues; por ahora usa CSV exportado desde Excel para previsualizar por encabezados.');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const { columns, rows } = parseDelimitedText(String(reader.result ?? ''));
      setCatalogImportColumns(columns);
      setCatalogImportPreview(buildCatalogImportPreview(rows, catalogItems));
    };
    reader.readAsText(file);
  }

  function confirmCatalogImport() {
    setCatalogImportMessage('Importacion preparada visualmente. No se agregaron conceptos al catalogo ni se envio informacion al backend.');
  }

  function downloadCatalogImportErrors() {
    if (!catalogImportPreview?.errors.length) return;
    const rows = catalogImportPreview.errors.map((row) => ({
      ...row.raw,
      Errores: row.errors.join(' | ')
    }));
    downloadCsv('catalogo_myc_errores.csv', [...catalogImportColumns, 'Errores'], rows);
  }

  function addDraftItem() {
    setError('');
    setDraftItems((current) => [
      ...current,
      {
        ...emptyQuotationItemForm,
        id: crypto.randomUUID(),
        isDraft: true,
        catalogSearch: ''
      }
    ]);
  }

  function updateDraftItem(draftId, field, value) {
    setDraftItems((current) =>
      current.map((item) => (item.id === draftId ? { ...item, [field]: value } : item))
    );
  }

  function selectDraftCatalogConcept(draftId, conceptId) {
    const item = catalogItems.find((catalogItem) => catalogItem.id === conceptId);
    if (!item) return;
    setDraftItems((current) =>
      current.map((draft) =>
        draft.id === draftId
          ? {
              ...draft,
              catalogItemId: item.id,
              catalogSearch: item.name,
              description: item.description || item.name,
              unit: item.customInternalUnit || item.internalUnit || item.satUnit || 'Servicio',
              unitPrice: String(item.finalPriceMxn ?? calculateFinalPriceMxn(item)),
              currency: 'MXN',
              satKey: item.satKey || '',
              satUnit: item.satUnit || '',
              internalUnit: item.internalUnit || '',
              commodity: item.commodity || null,
              calibrationScope: item.calibrationScope || null,
              quotationLegend: item.quotationLegend || null,
              taxObject: item.taxObject || 'iva_16',
              taxRate: item.taxRate ?? 16
            }
          : draft
      )
    );
  }

  function cancelDraftItem(draftId) {
    setDraftItems((current) => current.filter((item) => item.id !== draftId));
  }

  async function saveDraftItem(draft) {
    if (!selectedQuotation) return;
    if (!draft.description.trim()) {
      setError('Captura la descripcion de la partida.');
      return;
    }

    setSavingDraftIds((current) => new Set(current).add(draft.id));
    setError('');
    setNotice('');
    try {
      const updated = await createQuotationItem(selectedQuotation.id, {
        catalog_item_id: draft.catalogItemId ? Number(draft.catalogItemId) : null,
        service_name: draft.description.trim(),
        description: draft.observations.trim() || null,
        quantity: Number(draft.quantity || 1),
        unit: draft.unit?.trim() || null,
        sat_key: draft.satKey || null,
        sat_unit: draft.satUnit || null,
        internal_unit: draft.internalUnit || null,
        unit_price: Number(draft.unitPrice || 0),
        discount_percent: Number(draft.discount || 0),
        currency: draft.currency || 'MXN',
        commodity: draft.commodity || null,
        calibration_scope: draft.calibrationScope || null,
        quotation_legend: draft.quotationLegend || null,
        tax_object: draft.taxObject || 'iva_16',
        tax_rate: Number(draft.taxRate ?? 16)
      });
      setSelectedQuotation(updated);
      setNotice(`Partida agregada a ${updated.folio}`);
      setQuotationDetailTab('items');
      setDraftItems((current) => current.filter((item) => item.id !== draft.id));
      await loadQuotationData();
    } catch (requestError) {
      setError(`${requestError.message}. La linea se conserva como borrador para corregirla.`);
    } finally {
      setSavingDraftIds((current) => {
        const next = new Set(current);
        next.delete(draft.id);
        return next;
      });
    }
  }

  function downloadCatalogTemplate() {
    downloadCsv('plantilla_catalogo_myc.csv', catalogTemplateColumns, [
      {
        Tipo: 'Servicio',
        Commodity: 'calibration',
        Categoria: 'Calibracion',
        'Clave interna': 'Generada por sistema',
        Nombre: 'Calibracion de manometro',
        Descripcion: 'Servicio de calibracion por alcance definido',
        'Clave SAT': '81141504',
        'Unidad SAT': 'E48',
        'Unidad interna': 'service',
        'Unidad interna personalizada': '',
        'Precio origen': '1000',
        'Moneda origen': 'MXN',
        'Tipo de cambio': '1',
        'Costo interno': '650',
        'Moneda de costo': 'MXN',
        'Margen %': '35',
        'Precio final MXN': '1350',
        'Objeto impuesto': 'iva_16',
        Estado: 'Activo'
      }
    ]);
  }

  function exportCatalog() {
    const rows = catalogItems.map((item) => ({
      Tipo: item.type,
      Commodity: item.commodity,
      Categoria: item.category,
      'Clave interna': item.internalKey,
      Nombre: item.name,
      Descripcion: item.description,
      'Clave SAT': item.satKey,
      'Unidad SAT': item.satUnit,
      'Unidad interna': item.internalUnit,
      'Unidad interna personalizada': item.customInternalUnit,
      'Precio origen': item.basePrice,
      'Moneda origen': item.sourceCurrency,
      'Tipo de cambio': item.exchangeRate,
      'Costo interno': item.internalCost,
      'Moneda de costo': item.costCurrency,
      'Margen %': item.margin,
      'Precio final MXN': item.finalPriceMxn,
      'Objeto impuesto': item.taxObject,
      Estado: item.status
    }));
    downloadCsv('catalogo_myc_export.csv', catalogTemplateColumns, rows);
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
          Catalogo MYC
        </button>
        <button
          aria-selected={salesTab === 'template'}
          className={salesTab === 'template' ? 'module-tab is-active' : 'module-tab'}
          onClick={() => setSalesTab('template')}
          type="button"
        >
          Plantilla cotizacion
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
      ) : salesTab === 'catalog' ? (
      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Catalogo MYC</p>
            <h2>{filteredCatalogItems.length} conceptos visibles</h2>
          </div>
          <div className="toolbar-actions">
            <button
              className="table-button"
              onClick={openCatalogImportModal}
              type="button"
            >
              <Upload size={16} />
              Importar Excel
            </button>
            <button className="table-button" onClick={exportCatalog} type="button">
              <Download size={16} />
              Exportar Excel
            </button>
            <button className="table-button" onClick={downloadCatalogTemplate} type="button">
              <Download size={16} />
              Descargar plantilla
            </button>
            <button className="primary-button" onClick={() => openProductModal()} type="button">
              Nuevo producto/servicio
            </button>
          </div>
        </div>

        <div className="client-fiscal-note catalog-note">
          Cada servicio MYC debe existir como concepto independiente por magnitud, alcance y precio. Esta seccion es frontend visual hasta conectar backend.
        </div>

        <div className="import-chip-list catalog-rules">
          <span>Duplicados: nombre normalizado</span>
          <span>Duplicados: clave interna</span>
          <span>Duplicados: categoria + nombre</span>
          <span>Conversion V1: tipo de cambio manual</span>
        </div>

        <div className="catalog-category-map">
          <section>
            <h3>Servicios</h3>
            <div className="import-chip-list">
              {serviceCategories.map((category) => (
                <span key={category}>{category}</span>
              ))}
            </div>
          </section>
          <section>
            <h3>Productos</h3>
            <div className="import-chip-list">
              {productCategories.map((category) => (
                <span key={category}>{category}</span>
              ))}
            </div>
          </section>
        </div>

        <div className="catalog-filters">
          <label>
            Tipo
            <select onChange={(event) => updateCatalogFilter('type', event.target.value)} value={catalogFilters.type}>
              <option>Todos</option>
              <option>Producto</option>
              <option>Servicio</option>
            </select>
          </label>
          <label>
            Categoria
            <input
              onChange={(event) => updateCatalogFilter('category', event.target.value)}
              placeholder="Filtrar categoria"
              type="text"
              value={catalogFilters.category}
            />
          </label>
          <label>
            Busqueda
            <input
              onChange={(event) => updateCatalogFilter('search', event.target.value)}
              placeholder="Nombre o clave"
              type="text"
              value={catalogFilters.search}
            />
          </label>
          <label>
            Moneda
            <select
              onChange={(event) => updateCatalogFilter('currency', event.target.value)}
              value={catalogFilters.currency}
            >
              <option>Todas</option>
              <option>MXN</option>
              <option>USD</option>
              <option>EUR</option>
            </select>
          </label>
          <label>
            Estado
            <select onChange={(event) => updateCatalogFilter('status', event.target.value)} value={catalogFilters.status}>
              <option>Todos</option>
              <option>Activo</option>
              <option>Inactivo</option>
            </select>
          </label>
        </div>

        <div className="clients-table products-table">
          <div className="clients-table__head">
            <span>Tipo</span>
            <span>Categoria</span>
            <span>Clave</span>
            <span>Nombre</span>
            <span>Clave SAT</span>
            <span>Precio origen</span>
            <span>Precio final MXN</span>
            <span>Estado</span>
            <span>Acciones</span>
          </div>

          {filteredCatalogItems.length ? (
            filteredCatalogItems.map((item) => (
              <div className="clients-table__row" key={item.id}>
                <span>{item.type}</span>
                <span>{item.category || '-'}</span>
                <span>{item.internalKey || '-'}</span>
                <span>{item.name}</span>
                <span>{item.satKey || '-'}</span>
                <span>{formatMoney(item.basePrice)} {item.sourceCurrency}</span>
                <span>{formatMoney(item.finalPriceMxn ?? calculateFinalPriceMxn(item))}</span>
                <span>
                  <mark className={item.status === 'Activo' ? 'status-pill' : 'status-pill status-pill--muted'}>
                    {item.status}
                  </mark>
                </span>
                <span className="clients-table__actions">
                  <button className="table-button" onClick={() => openProductModal(item)} type="button">
                    Editar
                  </button>
                  <button className="table-button" onClick={() => handleDeleteCatalogItem(item)} type="button">
                    Desactivar
                  </button>
                </span>
              </div>
            ))
          ) : (
            <div className="clients-empty">Todavia no hay productos o servicios cargados en esta vista.</div>
          )}
        </div>
      </section>
      ) : (
      <section className="clients-list-panel quotation-template-panel">
        <div className="section-heading">
          <div>
            <p>Plantilla visual</p>
            <h2>Estructura de cotizacion MYC</h2>
          </div>
          <button
            className="table-button"
            onClick={() => setNotice('El PDF real se genera desde el detalle de cada cotizacion.')}
            type="button"
          >
            PDF desde cotizacion
          </button>
        </div>

        <div className="quotation-sheet">
          <header className="quotation-sheet__header">
            <div className="quotation-sheet__brand">
              <img alt="MYC" src={mycLogo} />
              <div>
                <strong>Metrologia y Servicios MYC</strong>
                <span>Servicios de metrologia, calibracion, venta y soporte tecnico especializado</span>
              </div>
            </div>
          </header>

          <section className="quotation-sheet__title-block">
            <p>COTIZACION</p>
            <span>Propuesta comercial de servicios, calibracion y soluciones tecnicas</span>
          </section>

          <div className="quotation-sheet__meta">
            <article className="quotation-sheet__meta-card quotation-sheet__meta-card--folio">
              <span>Folio</span>
              <strong>MYC-06-2026-0001</strong>
            </article>
            <article className="quotation-sheet__meta-card">
              <span>Emision</span>
              <strong>18 jun 2026</strong>
            </article>
            <article className="quotation-sheet__meta-card">
              <span>Vigencia</span>
              <strong>15 dias</strong>
            </article>
          </div>

          <div className="quotation-sheet__grid">
            <section>
              <h3>Datos del cliente</h3>
              <p>Nombre comercial, contacto, correo, telefono y domicilio operativo.</p>
            </section>
            <section>
              <h3>Datos fiscales</h3>
              <p>Razon social, RFC, regimen fiscal, uso CFDI y codigo postal fiscal.</p>
            </section>
          </div>

          <section className="quotation-lines-preview">
            <h3>Partidas</h3>
            <div className="quotation-lines-preview__head">
              <span>Descripcion</span>
              <span>Cantidad</span>
              <span>Unidad</span>
              <span>Precio unitario</span>
              <span>Descuento</span>
              <span>Importe</span>
            </div>
            <div className="quotation-lines-preview__row">
              <span>Servicio de calibracion por concepto independiente</span>
              <span>1</span>
              <span>Servicio</span>
              <span>$1,000.00</span>
              <span>0%</span>
              <span>$1,000.00</span>
            </div>
          </section>

          <div className="quotation-sheet__totals">
            <span>Subtotal $1,000.00</span>
            <span>IVA $160.00</span>
            <strong>Total $1,160.00</strong>
            <small>Total con letra: mil ciento sesenta pesos 00/100 MXN</small>
          </div>

          <div className="quotation-sheet__grid">
            <section>
              <h3>Condiciones comerciales</h3>
              <p>Tiempo de entrega, forma de pago, moneda, vigencia, alcance y condiciones aplicables.</p>
            </section>
            <section>
              <h3>Notas y autorizacion</h3>
              <p>Notas internas/externas, firma comercial, firma de autorizacion y trazabilidad futura.</p>
            </section>
          </div>
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
              <div className="quotation-pdf-actions">
                <button className="table-button" onClick={() => openQuotationPdf('view')} type="button">
                  Vista PDF
                </button>
                <button className="table-button" onClick={handleDownloadQuotationPdf} type="button">
                  Descargar PDF
                </button>
                <button className="table-button" onClick={() => openQuotationPdf('print')} type="button">
                  Imprimir
                </button>
              </div>
              <button
                className="icon-text-button"
                onClick={closeQuotationDetail}
                type="button"
              >
                Cerrar
              </button>
            </div>

            <div className="client-modal-tabs quotation-detail-tabs" role="tablist" aria-label="Detalle de cotizacion">
              {[
                ['info', 'Informacion'],
                ['items', 'Partidas'],
                ['history', 'Historial']
              ].map(([key, label]) => (
                <button
                  aria-selected={quotationDetailTab === key}
                  className={quotationDetailTab === key ? 'client-modal-tab is-active' : 'client-modal-tab'}
                  key={key}
                  onClick={() => setQuotationDetailTab(key)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>

            {quotationDetailTab === 'info' ? (
              <>
                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <p>Resumen economico</p>
                    <h3>Total cotizado</h3>
                  </div>
                  <div className="quotation-summary">
                    <div>
                      <span>Subtotal</span>
                      <strong>{formatMoney(calculateQuotationSummary(selectedQuotation).subtotal)}</strong>
                    </div>
                    <div>
                      <span>IVA</span>
                      <strong>{formatMoney(calculateQuotationSummary(selectedQuotation).tax)}</strong>
                    </div>
                    <div className="quotation-total-card">
                      <span>Total</span>
                      <strong>{formatMoney(calculateQuotationSummary(selectedQuotation).total)}</strong>
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
                    <span>Se mantiene PATCH actual para vigencia y notas.</span>
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
              </>
            ) : null}

            {quotationDetailTab === 'items' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>Partidas reales</p>
                    <h3>{getQuotationItems(selectedQuotation).length + draftItems.length} partidas</h3>
                  </div>
                  <button className="primary-button" onClick={addDraftItem} type="button">
                    + Agregar partida
                  </button>
                </div>

                <div className="quotation-items-table">
                  <div className="quotation-items-table__head">
                    <span>Descripcion</span>
                    <span>Cantidad</span>
                    <span>Unidad</span>
                    <span>Precio unitario</span>
                    <span>Descuento</span>
                    <span>Subtotal</span>
                    <span>Acciones</span>
                  </div>
                  {getQuotationItems(selectedQuotation).length || draftItems.length ? (
                    <>
                      {getQuotationItems(selectedQuotation).map((item) => {
                        const amounts = calculateLineAmounts(item);
                        return (
                          <div className="quotation-items-table__row" key={item.id}>
                            <span>{item.service_name}</span>
                            <span>{item.quantity}</span>
                            <span>{item.unit || 'Servicio'}</span>
                            <span>{formatMoney(item.unit_price)}</span>
                            <span>{item.discount_percent ?? 0}%</span>
                            <span>{formatMoney(amounts.subtotal)}</span>
                            <span className="clients-table__actions">
                              <button className="table-button" disabled type="button">
                                Editar despues
                              </button>
                              <button className="table-button" disabled type="button">
                                Eliminar
                              </button>
                            </span>
                          </div>
                        );
                      })}
                      {draftItems.map((draft) => {
                        const amounts = calculateLineAmounts(draft);
                        const filteredConcepts = catalogItems
                          .filter((item) => item.status !== 'Inactivo')
                          .filter((item) =>
                            normalizeKey(`${item.name} ${item.category} ${item.internalKey}`).includes(normalizeKey(draft.catalogSearch))
                          )
                          .slice(0, 5);
                        const isSavingDraft = savingDraftIds.has(draft.id);
                        return (
                          <div className="quotation-items-table__row quotation-items-table__row--draft" key={draft.id}>
                          <span className="quote-line-concept">
                            <mark className="status-pill status-pill--muted">Borrador</mark>
                            <input
                              list={`catalog-options-${draft.id}`}
                              onChange={(event) => {
                                const selected = catalogItems.find((item) => item.name === event.target.value);
                                if (selected) {
                                  selectDraftCatalogConcept(draft.id, selected.id);
                                } else {
                                  updateDraftItem(draft.id, 'catalogSearch', event.target.value);
                                  updateDraftItem(draft.id, 'description', event.target.value);
                                }
                              }}
                              placeholder="Buscar concepto / descripcion"
                              type="text"
                              value={draft.catalogSearch || draft.description}
                            />
                            <datalist id={`catalog-options-${draft.id}`}>
                              {filteredConcepts.map((item) => (
                                <option key={item.id} label={`${item.category} · ${item.internalKey}`} value={item.name} />
                              ))}
                            </datalist>
                          </span>
                          <span>
                            <input
                              min="1"
                              onChange={(event) => updateDraftItem(draft.id, 'quantity', event.target.value)}
                              type="number"
                              value={draft.quantity}
                            />
                          </span>
                          <span>
                            <input
                              onChange={(event) => updateDraftItem(draft.id, 'unit', event.target.value)}
                              type="text"
                              value={draft.unit}
                            />
                          </span>
                          <span>
                            <input
                              min="0"
                              onChange={(event) => updateDraftItem(draft.id, 'unitPrice', event.target.value)}
                              step="0.01"
                              type="number"
                              value={draft.unitPrice}
                            />
                          </span>
                          <span>
                            <input
                              min="0"
                              onChange={(event) => updateDraftItem(draft.id, 'discount', event.target.value)}
                              step="0.01"
                              type="number"
                              value={draft.discount}
                            />
                          </span>
                          <span>{formatMoney(amounts.subtotal)}</span>
                          <span className="clients-table__actions">
                            <button
                              className="table-button table-button--primary"
                              disabled={isSavingDraft}
                              onClick={() => saveDraftItem(draft)}
                              type="button"
                            >
                              {isSavingDraft ? 'Guardando...' : 'Guardar partida'}
                            </button>
                            <button
                              className="table-button"
                              disabled={isSavingDraft}
                              onClick={() => cancelDraftItem(draft.id)}
                              type="button"
                            >
                              Cancelar borrador
                            </button>
                          </span>
                          </div>
                        );
                      })}
                    </>
                  ) : (
                    <div className="clients-empty">Todavia no hay partidas en esta cotizacion.</div>
                  )}
                </div>

                <div className="quotation-summary quotation-summary--items">
                  <div>
                    <span>Subtotal</span>
                    <strong>{formatMoney(calculateQuotationDraftSummary(selectedQuotation, draftItems).subtotal)}</strong>
                  </div>
                  <div>
                    <span>Impuestos</span>
                    <strong>{formatMoney(calculateQuotationDraftSummary(selectedQuotation, draftItems).tax)}</strong>
                  </div>
                  <div className="quotation-total-card">
                    <span>Total</span>
                    <strong>{formatMoney(calculateQuotationDraftSummary(selectedQuotation, draftItems).total)}</strong>
                  </div>
                </div>
                <div className="client-fiscal-note">
                  Total con letra: {totalToSpanishText(calculateQuotationDraftSummary(selectedQuotation, draftItems).total)}
                </div>
              </section>
            ) : null}

            {quotationDetailTab === 'history' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Historial</p>
                  <h3>Eventos de cotizacion</h3>
                </div>
                <div className="quotation-history-list">
                  <article>
                    <strong>Cotizacion creada</strong>
                    <span>{formatDate(selectedQuotation.issued_on)}</span>
                  </article>
                  <article>
                    <strong>Ultima actualizacion</strong>
                    <span>{new Date(selectedQuotation.updated_at).toLocaleString('es-MX')}</span>
                  </article>
                  <article>
                    <strong>Estado actual</strong>
                    <span>{quotationStatusLabels[selectedQuotation.status] ?? selectedQuotation.status}</span>
                  </article>
                </div>
              </section>
            ) : null}
          </section>
        </div>
      ) : null}

      {isCatalogImportOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal import-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Catalogo MYC</p>
                <h2>Importar conceptos</h2>
              </div>
              <button className="icon-text-button" onClick={closeCatalogImportModal} type="button">
                Cerrar
              </button>
            </div>

            <div className="import-upload-zone">
              <label>
                Archivo Excel o CSV
                <input accept=".xlsx,.xls,.csv,.tsv" onChange={handleCatalogImportFile} type="file" />
              </label>
              <div>
                <strong>{catalogImportFileName || 'Sin archivo seleccionado'}</strong>
                <span>La vista previa busca columnas por encabezado, no por posicion.</span>
              </div>
            </div>

            {catalogImportMessage ? <div className="client-fiscal-note">{catalogImportMessage}</div> : null}

            <div className="import-template-grid">
              <article>
                <span>Columnas</span>
                <strong>{catalogImportColumns.length}</strong>
              </article>
              <article>
                <span>Validos</span>
                <strong>{catalogImportPreview?.valid.length ?? 0}</strong>
              </article>
              <article>
                <span>Duplicados</span>
                <strong>{catalogImportPreview?.duplicates.length ?? 0}</strong>
              </article>
              <article>
                <span>Errores</span>
                <strong>{catalogImportPreview?.errors.length ?? 0}</strong>
              </article>
            </div>

            <section className="import-preview-section">
              <h3>Columnas esperadas / detectadas</h3>
              <div className="import-chip-list">
                {(catalogImportColumns.length ? catalogImportColumns : catalogTemplateColumns).map((column) => (
                  <span key={column}>{column}</span>
                ))}
              </div>
            </section>

            <section className="import-preview-section">
              <h3>Vista previa</h3>
              <div className="import-preview-list">
                {catalogImportPreview?.rows.length ? (
                  catalogImportPreview.rows.slice(0, 8).map((row) => (
                    <article className={`import-row import-row--${row.status}`} key={row.id}>
                      <strong>{row.name}</strong>
                      <span>{row.type} · {row.category} · {row.price} {row.currency}</span>
                      <small>
                        {row.status === 'valid'
                          ? 'Valido'
                          : row.status === 'duplicate'
                            ? `Duplicado posible: ${row.duplicates.join(', ')}`
                            : row.errors.join(', ')}
                      </small>
                    </article>
                  ))
                ) : (
                  <div className="clients-empty">Sube un CSV exportado desde Excel para previsualizar conceptos.</div>
                )}
              </div>
            </section>

            <div className="client-form__actions client-form__actions--modal">
              <button
                className="table-button"
                disabled={!catalogImportPreview?.errors.length}
                onClick={downloadCatalogImportErrors}
                type="button"
              >
                Descargar errores
              </button>
              <button className="icon-text-button" onClick={closeCatalogImportModal} type="button">
                Cancelar
              </button>
              <button
                className="primary-button"
                disabled={!catalogImportPreview?.valid.length}
                onClick={confirmCatalogImport}
                type="button"
              >
                Confirmar importacion
              </button>
            </div>
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
                Tipo
                <select
                  onChange={(event) => {
                    const nextType = event.target.value;
                    updateProductForm('type', nextType);
                    updateProductForm('category', '');
                    updateProductForm('commodity', nextType === 'Producto' ? 'sale' : 'calibration');
                  }}
                  value={productForm.type}
                >
                  <option>Producto</option>
                  <option>Servicio</option>
                </select>
              </label>
              <label>
                Commodity
                <select
                  onChange={(event) => updateProductForm('commodity', event.target.value)}
                  value={productForm.commodity}
                >
                  {catalogCommodityOptions
                    .filter((option) =>
                      productForm.type === 'Producto'
                        ? option.value === 'sale'
                        : option.value !== 'sale'
                    )
                    .map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <label>
                Categoria
                <select
                  onChange={(event) => updateProductForm('category', event.target.value)}
                  value={productForm.category}
                >
                  <option value="">Seleccionar categoria</option>
                  {(productForm.type === 'Producto' ? productCategories : serviceCategories).map((category) => (
                    <option key={category}>{category}</option>
                  ))}
                </select>
              </label>
              <label>
                Clave interna generada
                <input
                  readOnly
                  placeholder="Se genera al guardar"
                  type="text"
                  value={productForm.internalKey}
                />
              </label>
              <label>
                Nombre
                <input
                  onChange={(event) => updateProductForm('name', event.target.value)}
                  required
                  type="text"
                  value={productForm.name}
                />
              </label>
              <label className="form-field--wide">
                Descripcion
                <textarea
                  onChange={(event) => updateProductForm('description', event.target.value)}
                  rows={3}
                  value={productForm.description}
                />
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
                Unidad interna
                <select
                  onChange={(event) => updateProductForm('internalUnit', event.target.value)}
                  value={productForm.internalUnit}
                >
                  {internalUnitOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              {productForm.internalUnit === 'other' ? (
                <label>
                  Unidad personalizada
                  <input
                    onChange={(event) => updateProductForm('customInternalUnit', event.target.value)}
                    type="text"
                    value={productForm.customInternalUnit}
                  />
                </label>
              ) : null}
              {productForm.commodity === 'calibration' ? (
                <label>
                  Alcance de calibracion
                  <select
                    onChange={(event) => updateProductForm('calibrationScope', event.target.value)}
                    value={productForm.calibrationScope}
                  >
                    {calibrationScopeOptions.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </select>
                </label>
              ) : null}
              {productForm.commodity === 'general_service' ? (
                <label className="form-field--wide">
                  Leyenda para cotizacion
                  <textarea
                    onChange={(event) => updateProductForm('quotationLegend', event.target.value)}
                    rows={2}
                    value={productForm.quotationLegend}
                  />
                </label>
              ) : null}
              <label>
                Precio origen
                <input
                  min="0"
                  onChange={(event) => updateProductForm('basePrice', event.target.value)}
                  step="0.01"
                  type="number"
                  value={productForm.basePrice}
                />
              </label>
              <label>
                Moneda origen
                <select
                  onChange={(event) => updateProductForm('sourceCurrency', event.target.value)}
                  value={productForm.sourceCurrency}
                >
                  <option>MXN</option>
                  <option>USD</option>
                  <option>EUR</option>
                </select>
              </label>
              <label>
                Tipo de cambio
                <input
                  min="0"
                  onChange={(event) => updateProductForm('exchangeRate', event.target.value)}
                  step="0.0001"
                  type="number"
                  value={productForm.exchangeRate}
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
                Moneda de costo
                <select
                  onChange={(event) => updateProductForm('costCurrency', event.target.value)}
                  value={productForm.costCurrency}
                >
                  <option>MXN</option>
                  <option>USD</option>
                  <option>EUR</option>
                </select>
              </label>
              <label>
                Margen %
                <input
                  min="0"
                  onChange={(event) => updateProductForm('margin', event.target.value)}
                  step="0.01"
                  type="number"
                  value={productForm.margin}
                />
              </label>
              <label>
                Objeto impuesto
                <select
                  onChange={(event) => updateProductForm('taxObject', event.target.value)}
                  value={productForm.taxObject}
                >
                  {taxObjectOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <div className="price-preview-card">
                <span>Precio final MXN</span>
                <strong>{formatMoney(calculateFinalPriceMxn(productForm))}</strong>
                <small>Manual: precio_origen x tipo_cambio x (1 + margen / 100)</small>
              </div>
              <label>
                Estado
                <select onChange={(event) => updateProductForm('status', event.target.value)} value={productForm.status}>
                  <option>Activo</option>
                  <option>Inactivo</option>
                </select>
              </label>

              <div className="client-fiscal-note form-field--wide">
                La conversion automatica se conectara posteriormente a un proveedor de tipo de cambio.
              </div>

              <div className="client-form__actions client-form__actions--modal">
                <button className="icon-text-button" disabled={isSaving} onClick={closeProductModal} type="button">
                  Cancelar
                </button>
                <button className="primary-button" disabled={isSaving} type="submit">
                  {isSaving ? 'Guardando...' : editingProductId ? 'Guardar cambios' : 'Agregar al catalogo'}
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
