import { Download, FileText, Upload } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';
import mycLogo from '../assets/myc-logo.png';

import {
  catalogCommodityOptions,
  calibrationScopeOptions,
  internalUnitOptions,
  taxObjectOptions,
  serviceCategories,
  productCategories,
  validCatalogCurrencies,
  catalogTypeToApi,
  catalogTypeFromApi
} from '../constants/catalog.js';
import { emptyQuotationForm, emptyQuotationItemForm, emptyProductForm } from '../constants/forms.js';
import { quotationStatusLabels, quotationActions, quotationTransitions } from '../constants/statuses.js';
import {
  changeQuotationStatus,
  createCatalogItem,
  createQuotation,
  createQuotationItem,
  createServiceOrder,
  deleteCatalogItem,
  deleteQuotationItem,
  downloadQuotationPdf,
  getQuotation,
  getQuotationPdfUrl,
  getQuotationTemplate,
  listCatalogItems,
  listClients,
  listQuotations,
  restoreQuotationTemplateDefaults,
  updateCatalogItem,
  updateQuotation,
  updateQuotationItem,
  updateQuotationTemplate
} from '../services/api.js';
import { downloadCsv, parseDelimitedText } from '../utils/csv.js';
import { getRowValue } from '../utils/clients.js';
import { formatDate, formatMoney, getClientDisplayName, normalizeKey } from '../utils/formatters.js';

const defaultQuotationTemplate = {
  name: 'Plantilla de cotizacion MYC',
  company_name: 'Metrologia y Servicios MYC',
  company_tagline: 'Servicios de metrologia, calibracion, venta y soporte tecnico especializado.',
  company_rfc: 'MYC000000XXX',
  company_email: 'contacto@mycmetrology.com.mx',
  company_website: 'www.mycmetrology.com.mx',
  company_address: '',
  company_phone: '',
  document_title: 'COTIZACION',
  document_subtitle: 'Propuesta comercial de servicios, calibracion y soluciones tecnicas',
  document_code: 'FCA-23-2',
  document_revision: '',
  document_issued_on: '2025-03-28',
  terms_version: 'V1',
  commercial_terms: [
    'Precios expresados en moneda nacional, salvo indicacion contraria.',
    'Vigencia sujeta a la fecha indicada en esta cotizacion.',
    'Tiempos de entrega y alcance final se confirman al recibir autorizacion.'
  ].join('\n'),
  metrological_terms: 'Los servicios metrologicos se ejecutan conforme al alcance tecnico autorizado y a la disponibilidad de patrones aplicables.',
  legal_terms: 'La autorizacion de esta cotizacion implica aceptacion de las condiciones comerciales, tecnicas y documentales descritas.',
  privacy_notice: 'Los datos del cliente se usan exclusivamente para fines comerciales, operativos, documentales y de facturacion relacionados con el servicio solicitado.',
  acceptance_text: 'Acepto las condiciones comerciales, metrologicas y legales de la presente cotizacion.',
  show_summary_terms: true,
  show_full_terms: true,
  show_acceptance_signature: true
};

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
function mapTemplateFromApi(template) {
  return {
    ...defaultQuotationTemplate,
    ...(template ?? {}),
    document_revision: template?.document_revision ?? '',
    document_issued_on: template?.document_issued_on ?? defaultQuotationTemplate.document_issued_on,
    company_address: template?.company_address ?? '',
    company_phone: template?.company_phone ?? '',
    show_summary_terms: template?.show_summary_terms ?? true,
    show_full_terms: template?.show_full_terms ?? true,
    show_acceptance_signature: template?.show_acceptance_signature ?? true
  };
}
function mapTemplatePayload(form) {
  const payload = { ...form };
  delete payload.id;
  delete payload.template_key;
  delete payload.is_active;
  delete payload.created_at;
  delete payload.updated_at;
  payload.document_revision = payload.document_revision?.trim() || null;
  payload.document_issued_on = payload.document_issued_on || null;
  return payload;
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

function quotationItemToForm(item) {
  return {
    catalogItemId: item.catalog_item_id || '',
    description: item.service_name || '',
    quantity: String(item.quantity ?? 1),
    unit: item.unit || 'Servicio',
    unitPrice: String(item.unit_price ?? 0),
    currency: item.currency || 'MXN',
    discount: String(item.discount_percent ?? 0),
    observations: item.description || '',
    satKey: item.sat_key || '',
    satUnit: item.sat_unit || '',
    internalUnit: item.internal_unit || '',
    commodity: item.commodity || null,
    calibrationScope: item.calibration_scope || null,
    quotationLegend: item.quotation_legend || '',
    taxObject: item.tax_object || 'iva_16',
    taxRate: String(item.tax_rate ?? 16)
  };
}

function buildQuotationItemPayload(itemForm) {
  return {
    catalog_item_id: itemForm.catalogItemId ? Number(itemForm.catalogItemId) : null,
    service_name: itemForm.description.trim(),
    description: itemForm.observations?.trim() || null,
    quantity: Number(itemForm.quantity || 1),
    unit: itemForm.unit?.trim() || null,
    sat_key: itemForm.satKey || null,
    sat_unit: itemForm.satUnit || null,
    internal_unit: itemForm.internalUnit || null,
    unit_price: Number(itemForm.unitPrice || 0),
    discount_percent: Number(itemForm.discount || 0),
    currency: itemForm.currency || 'MXN',
    commodity: itemForm.commodity || null,
    calibration_scope: itemForm.calibrationScope || null,
    quotation_legend: itemForm.quotationLegend || null,
    tax_object: itemForm.taxObject || 'iva_16',
    tax_rate: Number(itemForm.taxRate ?? 16)
  };
}

function isQuotationTerminal(quotation) {
  return ['accepted', 'rejected', 'expired', 'cancelled'].includes(quotation?.status);
}
function totalToSpanishText(value) {
  const amount = Number(value || 0);
  return `${formatMoney(amount)} MXN`;
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
  const [templateForm, setTemplateForm] = useState(defaultQuotationTemplate);
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
  const [editingItemForms, setEditingItemForms] = useState({});
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isProductModalOpen, setIsProductModalOpen] = useState(false);
  const [isCatalogImportOpen, setIsCatalogImportOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDetailSaving, setIsDetailSaving] = useState(false);
  const [isTemplateSaving, setIsTemplateSaving] = useState(false);
  const [savingDraftIds, setSavingDraftIds] = useState(new Set());
  const [savingItemIds, setSavingItemIds] = useState(new Set());
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
      const [quotationResult, clientResult, catalogResult, templateResult] = await Promise.allSettled([
        listQuotations(),
        listClients(),
        listCatalogItems({ is_active: true }),
        getQuotationTemplate()
      ]);
      if (quotationResult.status === 'rejected') {
        throw quotationResult.reason;
      }
      if (clientResult.status === 'rejected') {
        throw clientResult.reason;
      }
      if (catalogResult.status === 'rejected') {
        throw catalogResult.reason;
      }
      const quotationItems = quotationResult.value;
      const clientItems = clientResult.value;
      const catalogApiItems = catalogResult.value;
      setQuotations(Array.isArray(quotationItems) ? quotationItems : []);
      setClients(Array.isArray(clientItems) ? clientItems : []);
      setCatalogItems(
        Array.isArray(catalogApiItems) ? catalogApiItems.map(mapCatalogItemFromApi) : []
      );
      setTemplateForm(
        templateResult.status === 'fulfilled'
          ? mapTemplateFromApi(templateResult.value)
          : defaultQuotationTemplate
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

  function updateTemplateForm(field, value) {
    setTemplateForm((current) => ({ ...current, [field]: value }));
  }

  async function handleTemplateSubmit(event) {
    event.preventDefault();
    setError('');
    setNotice('');
    setIsTemplateSaving(true);
    try {
      const updated = await updateQuotationTemplate(mapTemplatePayload(templateForm));
      setTemplateForm(mapTemplateFromApi(updated));
      setNotice('Plantilla de cotizacion guardada correctamente');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsTemplateSaving(false);
    }
  }

  async function handleRestoreTemplateDefaults() {
    if (!window.confirm('¿Restaurar los valores por defecto de la plantilla de cotizacion?')) {
      return;
    }
    setError('');
    setNotice('');
    setIsTemplateSaving(true);
    try {
      const restored = await restoreQuotationTemplateDefaults();
      setTemplateForm(mapTemplateFromApi(restored));
      setNotice('Plantilla restaurada a valores por defecto');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsTemplateSaving(false);
    }
  }

  function openTemplatePdfPreview() {
    const sampleQuotation = quotations[0];
    if (!sampleQuotation) {
      setNotice('Crea una cotizacion para generar una vista PDF de prueba.');
      return;
    }
    window.open(getQuotationPdfUrl(sampleQuotation.id), '_blank', 'noopener,noreferrer');
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
    setEditingItemForms({});
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
    if (!getQuotationItems(selectedQuotation).length) {
      const shouldContinue = window.confirm('La cotizacion no tiene partidas registradas. ¿Deseas generar el PDF de todos modos?');
      if (!shouldContinue) return;
    }
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
    if (!getQuotationItems(selectedQuotation).length) {
      const shouldContinue = window.confirm('La cotizacion no tiene partidas registradas. ¿Deseas descargar el PDF de todos modos?');
      if (!shouldContinue) return;
    }
    setError('');
    setNotice('');
    try {
      const { blob, filename } = await downloadQuotationPdf(
        selectedQuotation.id,
        selectedQuotation,
        getClientDisplayName(clientsById.get(selectedQuotation.client_id))
      );
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

  async function confirmCatalogImport() {
    const validRows = catalogImportPreview?.valid ?? [];
    if (!validRows.length) return;
    setIsSaving(true);
    setError('');
    setCatalogImportMessage('');
    try {
      let imported = 0;
      const failed = [];
      for (const row of validRows) {
        const raw = row.raw;
        const type = getRowValue(raw, ['Tipo']);
        const commodity = getRowValue(raw, ['Commodity']);
        const category = getRowValue(raw, ['Categoria', 'Categoría']);
        const name = getRowValue(raw, ['Nombre']);
        const form = {
          ...emptyProductForm,
          type: type || 'Servicio',
          commodity: commodity || (type === 'Producto' ? 'sale' : 'general_service'),
          category,
          name,
          description: getRowValue(raw, ['Descripcion', 'Descripción']),
          satKey: getRowValue(raw, ['Clave SAT']),
          satUnit: getRowValue(raw, ['Unidad SAT']),
          internalUnit: getRowValue(raw, ['Unidad interna']) || 'service',
          customInternalUnit: getRowValue(raw, ['Unidad interna personalizada']),
          basePrice: getRowValue(raw, ['Precio origen']) || '0',
          sourceCurrency: (getRowValue(raw, ['Moneda origen']) || 'MXN').toUpperCase(),
          exchangeRate: getRowValue(raw, ['Tipo de cambio']) || '1',
          internalCost: getRowValue(raw, ['Costo interno']),
          costCurrency: (getRowValue(raw, ['Moneda de costo']) || 'MXN').toUpperCase(),
          margin: getRowValue(raw, ['Margen %']) || '0',
          taxObject: getRowValue(raw, ['Objeto impuesto']) || 'iva_16',
          quotationLegend: getRowValue(raw, ['Leyenda cotizacion', 'Leyenda cotización']),
          calibrationScope: getRowValue(raw, ['Alcance calibracion', 'Alcance calibración']) || 'traceable'
        };
        try {
          const saved = await createCatalogItem(mapCatalogPayloadFromForm(form));
          setCatalogItems((current) => [mapCatalogItemFromApi(saved), ...current]);
          imported += 1;
        } catch (requestError) {
          failed.push({ ...raw, Errores: requestError.message });
        }
      }
      if (failed.length) {
        downloadCsv('catalogo_myc_importacion_fallida.csv', [...catalogImportColumns, 'Errores'], failed);
      }
      setCatalogImportMessage(`Importacion finalizada: ${imported} conceptos creados${failed.length ? `, ${failed.length} con error` : ''}.`);
    } finally {
      setIsSaving(false);
    }
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
      const updated = await createQuotationItem(selectedQuotation.id, buildQuotationItemPayload(draft));
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

  function startEditQuotationItem(item) {
    setError('');
    setEditingItemForms((current) => ({
      ...current,
      [item.id]: quotationItemToForm(item)
    }));
  }

  function updateEditingItem(itemId, field, value) {
    setEditingItemForms((current) => ({
      ...current,
      [itemId]: {
        ...(current[itemId] ?? emptyQuotationItemForm),
        [field]: value
      }
    }));
  }

  function cancelEditQuotationItem(itemId) {
    setEditingItemForms((current) => {
      const next = { ...current };
      delete next[itemId];
      return next;
    });
  }

  async function saveEditedQuotationItem(itemId) {
    if (!selectedQuotation) return;
    const form = editingItemForms[itemId];
    if (!form?.description?.trim()) {
      setError('Captura la descripcion de la partida.');
      return;
    }
    setSavingItemIds((current) => new Set(current).add(itemId));
    setError('');
    setNotice('');
    try {
      const updated = await updateQuotationItem(
        selectedQuotation.id,
        itemId,
        buildQuotationItemPayload(form)
      );
      setSelectedQuotation(updated);
      cancelEditQuotationItem(itemId);
      setNotice(`Partida actualizada en ${updated.folio}`);
      await loadQuotationData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingItemIds((current) => {
        const next = new Set(current);
        next.delete(itemId);
        return next;
      });
    }
  }

  async function deleteSavedQuotationItem(item) {
    if (!selectedQuotation) return;
    if (!window.confirm('¿Eliminar esta partida de la cotización?')) {
      return;
    }
    setSavingItemIds((current) => new Set(current).add(item.id));
    setError('');
    setNotice('');
    try {
      const updated = await deleteQuotationItem(selectedQuotation.id, item.id);
      setSelectedQuotation(updated);
      cancelEditQuotationItem(item.id);
      setNotice('Partida eliminada de la cotizacion');
      await loadQuotationData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSavingItemIds((current) => {
        const next = new Set(current);
        next.delete(item.id);
        return next;
      });
    }
  }

  function duplicateQuotationItem(item) {
    setQuotationDetailTab('items');
    setDraftItems((current) => [
      ...current,
      {
        ...quotationItemToForm(item),
        id: crypto.randomUUID(),
        isDraft: true,
        catalogSearch: item.service_name || ''
      }
    ]);
    setNotice('Partida duplicada como borrador. Revisa y guarda para agregarla.');
  }

  async function addCatalogItemToQuotation(item) {
    setSalesTab('quotations');
    if (!selectedQuotation) {
      setNotice('Abre una cotizacion para agregar este concepto como partida.');
      return;
    }
    if (isQuotationTerminal(selectedQuotation)) {
      setError('No se pueden agregar partidas a una cotizacion en estado terminal.');
      return;
    }
    setQuotationDetailTab('items');
    setDraftItems((current) => [
      ...current,
      {
        ...emptyQuotationItemForm,
        id: crypto.randomUUID(),
        isDraft: true,
        catalogSearch: item.name,
        catalogItemId: item.id,
        description: item.description || item.name,
        unit: item.customInternalUnit || item.internalUnit || item.satUnit || 'Servicio',
        unitPrice: String(item.finalPriceMxn ?? calculateFinalPriceMxn(item)),
        currency: 'MXN',
        satKey: item.satKey || '',
        satUnit: item.satUnit || '',
        internalUnit: item.internalUnit || '',
        commodity: item.commodity || null,
        calibrationScope: item.calibrationScope || null,
        quotationLegend: item.quotationLegend || '',
        taxObject: item.taxObject || 'iva_16',
        taxRate: String(item.taxRate ?? 16)
      }
    ]);
    setIsDetailOpen(true);
    setNotice(`${item.name} agregado como borrador de partida.`);
  }

  async function handleGenerateServiceOrder() {
    if (!selectedQuotation) return;
    if (selectedQuotation.status !== 'accepted') {
      setError('Solo una cotizacion aceptada puede generar orden de servicio.');
      return;
    }
    if (!window.confirm(`¿Generar orden de servicio desde ${selectedQuotation.folio}?`)) {
      return;
    }
    setError('');
    setNotice('');
    try {
      const serviceOrder = await createServiceOrder({
        client_id: selectedQuotation.client_id,
        quotation_id: selectedQuotation.id,
        notes: selectedQuotation.notes || `Generada desde cotizacion ${selectedQuotation.folio}`
      });
      setNotice(`Orden de servicio ${serviceOrder.folio} creada correctamente`);
      if (window.confirm('Orden de servicio creada correctamente. ¿Ir a Orden de Servicio?')) {
        window.location.hash = 'ordenes';
      }
    } catch (requestError) {
      setError(requestError.message);
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
          Cada servicio MYC debe existir como concepto independiente por magnitud, alcance y precio. Esta seccion ya guarda contra el Catalogo MYC del backend.
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
                  <button className="table-button table-button--primary" onClick={() => addCatalogItemToQuotation(item)} type="button">
                    Agregar a cotizacion
                  </button>
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
            <p>Editor PDF</p>
            <h2>Plantilla de cotizacion</h2>
          </div>
          <div className="toolbar-actions">
            <button className="table-button" onClick={openTemplatePdfPreview} type="button">
              Vista PDF de prueba
            </button>
            <button
              className="table-button"
              disabled={isTemplateSaving}
              onClick={handleRestoreTemplateDefaults}
              type="button"
            >
              Restaurar valores
            </button>
            <button
              className="primary-button"
              disabled={isTemplateSaving}
              form="quotation-template-form"
              type="submit"
            >
              {isTemplateSaving ? 'Guardando...' : 'Guardar plantilla'}
            </button>
          </div>
        </div>

        <div className="template-editor-layout">
          <form id="quotation-template-form" className="template-editor-form" onSubmit={handleTemplateSubmit}>
            <section className="quotation-section">
              <div className="quotation-section__title">
                <p>Identidad</p>
                <h3>Datos visibles de MYC</h3>
              </div>
              <div className="template-editor-grid">
                <label>
                  Nombre comercial visible
                  <input value={templateForm.company_name} onChange={(event) => updateTemplateForm('company_name', event.target.value)} />
                </label>
                <label>
                  RFC de MYC
                  <input value={templateForm.company_rfc || ''} onChange={(event) => updateTemplateForm('company_rfc', event.target.value)} />
                </label>
                <label className="form-field--wide">
                  Lema / descripcion
                  <input value={templateForm.company_tagline || ''} onChange={(event) => updateTemplateForm('company_tagline', event.target.value)} />
                </label>
                <label>
                  Correo
                  <input value={templateForm.company_email || ''} onChange={(event) => updateTemplateForm('company_email', event.target.value)} />
                </label>
                <label>
                  Sitio web
                  <input value={templateForm.company_website || ''} onChange={(event) => updateTemplateForm('company_website', event.target.value)} />
                </label>
                <label>
                  Telefono
                  <input value={templateForm.company_phone || ''} onChange={(event) => updateTemplateForm('company_phone', event.target.value)} />
                </label>
                <label className="form-field--wide">
                  Direccion
                  <textarea rows={2} value={templateForm.company_address || ''} onChange={(event) => updateTemplateForm('company_address', event.target.value)} />
                </label>
              </div>
            </section>

            <section className="quotation-section">
              <div className="quotation-section__title">
                <p>Documento</p>
                <h3>Control documental</h3>
              </div>
              <div className="template-editor-grid">
                <label>
                  Titulo principal
                  <input value={templateForm.document_title} onChange={(event) => updateTemplateForm('document_title', event.target.value)} />
                </label>
                <label>
                  Codigo documental
                  <input value={templateForm.document_code || ''} onChange={(event) => updateTemplateForm('document_code', event.target.value)} />
                </label>
                <label className="form-field--wide">
                  Subtitulo
                  <input value={templateForm.document_subtitle || ''} onChange={(event) => updateTemplateForm('document_subtitle', event.target.value)} />
                </label>
                <label>
                  Revision
                  <input value={templateForm.document_revision || ''} onChange={(event) => updateTemplateForm('document_revision', event.target.value)} />
                </label>
                <label>
                  Fecha de emision documental
                  <input type="date" value={templateForm.document_issued_on || ''} onChange={(event) => updateTemplateForm('document_issued_on', event.target.value)} />
                </label>
                <label>
                  Version de terminos
                  <input value={templateForm.terms_version || ''} onChange={(event) => updateTemplateForm('terms_version', event.target.value)} />
                </label>
              </div>
            </section>

            <section className="quotation-section">
              <div className="quotation-section__title">
                <p>Condiciones</p>
                <h3>Textos imprimibles</h3>
              </div>
              <label className="form-field--wide">
                Condiciones comerciales
                <textarea rows={4} value={templateForm.commercial_terms || ''} onChange={(event) => updateTemplateForm('commercial_terms', event.target.value)} />
              </label>
              <label className="form-field--wide">
                Condiciones metrologicas
                <textarea rows={4} value={templateForm.metrological_terms || ''} onChange={(event) => updateTemplateForm('metrological_terms', event.target.value)} />
              </label>
              <label className="form-field--wide">
                Condiciones legales
                <textarea rows={4} value={templateForm.legal_terms || ''} onChange={(event) => updateTemplateForm('legal_terms', event.target.value)} />
              </label>
              <label className="form-field--wide">
                Aviso de privacidad
                <textarea rows={4} value={templateForm.privacy_notice || ''} onChange={(event) => updateTemplateForm('privacy_notice', event.target.value)} />
              </label>
              <label className="form-field--wide">
                Firma de aceptacion
                <textarea rows={2} value={templateForm.acceptance_text || ''} onChange={(event) => updateTemplateForm('acceptance_text', event.target.value)} />
              </label>
            </section>

            <section className="quotation-section">
              <div className="quotation-section__title">
                <p>Opciones PDF</p>
                <h3>Visibilidad en impresion</h3>
              </div>
              <div className="template-toggle-list">
                <label>
                  <input type="checkbox" checked={templateForm.show_summary_terms} onChange={(event) => updateTemplateForm('show_summary_terms', event.target.checked)} />
                  Mostrar terminos resumidos en pagina 1
                </label>
                <label>
                  <input type="checkbox" checked={templateForm.show_full_terms} onChange={(event) => updateTemplateForm('show_full_terms', event.target.checked)} />
                  Mostrar terminos completos como pagina adicional
                </label>
                <label>
                  <input type="checkbox" checked={templateForm.show_acceptance_signature} onChange={(event) => updateTemplateForm('show_acceptance_signature', event.target.checked)} />
                  Mostrar firma de aceptacion
                </label>
              </div>
            </section>
          </form>

          <div className="quotation-sheet template-live-preview">
            <header className="quotation-sheet__header">
              <div className="quotation-sheet__brand">
                <img alt="MYC" src={mycLogo} />
                <div>
                  <strong>{templateForm.company_name}</strong>
                  <span>{templateForm.company_tagline}</span>
                </div>
              </div>
            </header>

            <section className="quotation-sheet__title-block">
              <div className="quotation-sheet__document-control">
                <span>Codigo</span>
                <strong>{templateForm.document_code || '-'}</strong>
                {templateForm.document_revision ? (
                  <>
                    <span>Revision</span>
                    <strong>{templateForm.document_revision}</strong>
                  </>
                ) : null}
                <span>Emision</span>
                <strong>{templateForm.document_issued_on || '-'}</strong>
              </div>
              <p>{templateForm.document_title}</p>
              <span>{templateForm.document_subtitle}</span>
            </section>

            <div className="quotation-sheet__meta quotation-sheet__meta--four">
              <article className="quotation-sheet__meta-card quotation-sheet__meta-card--folio">
                <span>Folio</span>
                <strong>MYC-06-26-0001</strong>
              </article>
              <article className="quotation-sheet__meta-card">
                <span>Emision</span>
                <strong>18/06/2026</strong>
              </article>
              <article className="quotation-sheet__meta-card">
                <span>Vigencia</span>
                <strong>15 dias</strong>
              </article>
              <article className="quotation-sheet__meta-card">
                <span>Vendedor</span>
                <strong>Por definir</strong>
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
                <p>{templateForm.commercial_terms}</p>
              </section>
              <section>
                <h3>Notas y autorizacion</h3>
                <p>El control documental se imprime junto al encabezado de cotizacion.</p>
                <p>{templateForm.acceptance_text}</p>
              </section>
            </div>
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
                    <button
                      className="primary-button"
                      disabled={selectedQuotation.status !== 'accepted'}
                      onClick={handleGenerateServiceOrder}
                      type="button"
                    >
                      Generar orden de servicio
                    </button>
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
                  <button
                    className="primary-button"
                    disabled={isQuotationTerminal(selectedQuotation)}
                    onClick={addDraftItem}
                    type="button"
                  >
                    + Agregar partida
                  </button>
                </div>
                {isQuotationTerminal(selectedQuotation) ? (
                  <div className="client-fiscal-note">
                    Esta cotizacion esta en estado terminal. Las partidas quedan bloqueadas para conservar el historico comercial.
                  </div>
                ) : null}

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
                        const form = editingItemForms[item.id];
                        const rowData = form || item;
                        const amounts = calculateLineAmounts(rowData);
                        const isSavingItem = savingItemIds.has(item.id);
                        const isEditing = Boolean(form);
                        return (
                          <div className="quotation-items-table__row" key={item.id}>
                            <span className="quote-line-concept">
                              {isEditing ? (
                                <>
                                  <input
                                    onChange={(event) => updateEditingItem(item.id, 'description', event.target.value)}
                                    type="text"
                                    value={form.description}
                                  />
                                  <input
                                    onChange={(event) => updateEditingItem(item.id, 'quotationLegend', event.target.value)}
                                    placeholder="Leyenda de cotizacion"
                                    type="text"
                                    value={form.quotationLegend || ''}
                                  />
                                  <select
                                    onChange={(event) => {
                                      const taxObject = event.target.value;
                                      updateEditingItem(item.id, 'taxObject', taxObject);
                                      updateEditingItem(item.id, 'taxRate', taxObject === 'iva_16' ? '16' : '0');
                                    }}
                                    value={form.taxObject || 'iva_16'}
                                  >
                                    <option value="iva_16">IVA 16%</option>
                                    <option value="iva_0">IVA 0%</option>
                                    <option value="exempt">Exento</option>
                                    <option value="not_subject">No objeto</option>
                                  </select>
                                </>
                              ) : (
                                <>
                                  <strong>{item.service_name}</strong>
                                  {item.quotation_legend ? <small>{item.quotation_legend}</small> : null}
                                  <small>Impuesto: {Number(item.tax_rate ?? 0)}%</small>
                                </>
                              )}
                            </span>
                            <span>
                              {isEditing ? (
                                <input
                                  min="1"
                                  onChange={(event) => updateEditingItem(item.id, 'quantity', event.target.value)}
                                  type="number"
                                  value={form.quantity}
                                />
                              ) : item.quantity}
                            </span>
                            <span>
                              {isEditing ? (
                                <input
                                  onChange={(event) => updateEditingItem(item.id, 'unit', event.target.value)}
                                  type="text"
                                  value={form.unit}
                                />
                              ) : item.unit || 'Servicio'}
                            </span>
                            <span>
                              {isEditing ? (
                                <input
                                  min="0"
                                  onChange={(event) => updateEditingItem(item.id, 'unitPrice', event.target.value)}
                                  step="0.01"
                                  type="number"
                                  value={form.unitPrice}
                                />
                              ) : formatMoney(item.unit_price)}
                            </span>
                            <span>
                              {isEditing ? (
                                <input
                                  min="0"
                                  onChange={(event) => updateEditingItem(item.id, 'discount', event.target.value)}
                                  step="0.01"
                                  type="number"
                                  value={form.discount}
                                />
                              ) : `${item.discount_percent ?? 0}%`}
                            </span>
                            <span>{formatMoney(amounts.subtotal)}</span>
                            <span className="clients-table__actions">
                              {isEditing ? (
                                <>
                                  <button
                                    className="table-button table-button--primary"
                                    disabled={isSavingItem}
                                    onClick={() => saveEditedQuotationItem(item.id)}
                                    type="button"
                                  >
                                    {isSavingItem ? 'Guardando...' : 'Guardar'}
                                  </button>
                                  <button
                                    className="table-button"
                                    disabled={isSavingItem}
                                    onClick={() => cancelEditQuotationItem(item.id)}
                                    type="button"
                                  >
                                    Cancelar
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    className="table-button"
                                    disabled={isQuotationTerminal(selectedQuotation)}
                                    onClick={() => startEditQuotationItem(item)}
                                    type="button"
                                  >
                                    Editar
                                  </button>
                                  <button
                                    className="table-button"
                                    disabled={isQuotationTerminal(selectedQuotation)}
                                    onClick={() => duplicateQuotationItem(item)}
                                    type="button"
                                  >
                                    Duplicar
                                  </button>
                                  <button
                                    className="table-button"
                                    disabled={isQuotationTerminal(selectedQuotation) || isSavingItem}
                                    onClick={() => deleteSavedQuotationItem(item)}
                                    type="button"
                                  >
                                    Eliminar
                                  </button>
                                </>
                              )}
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
                            <input
                              onChange={(event) => updateDraftItem(draft.id, 'quotationLegend', event.target.value)}
                              placeholder="Leyenda de cotizacion"
                              type="text"
                              value={draft.quotationLegend || ''}
                            />
                            <select
                              onChange={(event) => {
                                const taxObject = event.target.value;
                                updateDraftItem(draft.id, 'taxObject', taxObject);
                                updateDraftItem(draft.id, 'taxRate', taxObject === 'iva_16' ? '16' : '0');
                              }}
                              value={draft.taxObject || 'iva_16'}
                            >
                              <option value="iva_16">IVA 16%</option>
                              <option value="iva_0">IVA 0%</option>
                              <option value="exempt">Exento</option>
                              <option value="not_subject">No objeto</option>
                            </select>
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


export default QuotationsPage;
