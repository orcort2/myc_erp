import { useEffect, useMemo, useState } from 'react';

import {
  createInvoice,
  downloadInstitutionalInvoicePdf,
  downloadInvoiceFiscalXml,
  getClient,
  getFacturamaStatus,
  getInvoice,
  getInvoiceDashboard,
  getInvoiceSettings,
  getQuotation,
  getServiceOrder,
  issueInvoice,
  listClients,
  listInvoices,
  listQuotations,
  listSatCatalogs,
  listServiceOrders,
  updateInvoice,
  updateInvoiceSettings,
} from '../../services/api.js';
import { normalizeInvoiceWorkbenchContext } from '../../utils/invoiceWorkbenchContext.js';
import { buildInvoiceWorkbenchDraft } from './invoiceWorkbenchDraft.js';

export function findOrderForQuotation(serviceOrders, quotationId) {
  return (
    serviceOrders.find(
      (order) =>
        order.is_active !== false &&
        String(order.quotation_id) === String(quotationId)
    ) || null
  );
}

function quotationItemsToInvoiceItems(quotation, draft) {
  return (quotation?.items || [])
    .filter((item) => item.is_active !== false)
    .map((item) => {
      const fiscal = draft?.concepts?.[item.id] || {};
      const rateCode = fiscal.taxRate?.code;
      const taxRate = rateCode
        ? Number(rateCode) * 100
        : Number(item.tax_rate || 16);

      return {
        quotation_item_id: item.id,
        description:
          item.description ||
          item.service_name ||
          'Servicio de calibración',
        quantity: Number(item.quantity || 1),
        unit: item.unit || 'Servicio',
        sat_unit: fiscal.unit?.code || item.sat_unit || 'E48',
        sat_key:
          fiscal.productService?.code || item.sat_key || '81141504',
        unit_price: Number(item.unit_price || 0),
        discount_total: Number(item.discount_total || 0),
        tax_rate: taxRate,
        notes: item.notes || null,
        service_type: item.service_type || item.service_name || null,
        source_type: 'quotation',
      };
    });
}

function saveDownloadedFile({ blob, filename }, fallbackFilename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || fallbackFilename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export default function useInvoiceWorkbenchController({
  initialContext = null,
  loadOverview = true,
  openInitialContext = true,
  onIssuerConfigurationRequired,
} = {}) {
  const [dashboard, setDashboard] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [clients, setClients] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [satCatalogs, setSatCatalogs] = useState([]);
  const [settings, setSettings] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [workspaceOpen, setWorkspaceOpen] = useState(false);
  const [workspaceOriginElement, setWorkspaceOriginElement] = useState(null);
  const [selectedQuotation, setSelectedQuotation] = useState(null);
  const [selectedServiceOrder, setSelectedServiceOrder] = useState(null);
  const [selectedClient, setSelectedClient] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [contextInvoice, setContextInvoice] = useState(null);
  const [contextLoading, setContextLoading] = useState(Boolean(initialContext));
  const [contextResolved, setContextResolved] = useState(!initialContext);
  const [workspaceDraft, setWorkspaceDraft] = useState({});
  const [facturamaStatus, setFacturamaStatus] = useState(null);

  const clientsById = useMemo(
    () => new Map(clients.map((item) => [item.id, item])),
    [clients]
  );
  const ordersById = useMemo(
    () => new Map(serviceOrders.map((item) => [item.id, item])),
    [serviceOrders]
  );
  const quotationsById = useMemo(
    () => new Map(quotations.map((item) => [item.id, item])),
    [quotations]
  );
  const catalogByCode = useMemo(
    () => new Map(satCatalogs.map((item) => [item.code, item])),
    [satCatalogs]
  );

  useEffect(() => {
    let active = true;
    async function initialize() {
      await Promise.all([
        loadOverview ? loadBillingData() : loadWorkbenchDependencies(),
        refreshFacturamaStatus(),
      ]);
      if (active && initialContext) {
        if (openInitialContext) {
          await openWorkspaceByContext(initialContext);
        } else {
          await loadContextSummary(initialContext);
        }
      }
    }
    initialize();
    return () => {
      active = false;
    };
  }, []);

  async function refreshFacturamaStatus() {
    try {
      setFacturamaStatus(null);
      setFacturamaStatus(await getFacturamaStatus());
    } catch {
      setFacturamaStatus({ connected: false, status: 'network_error' });
    }
  }

  async function loadBillingData() {
    setIsLoading(true);
    setError('');
    try {
      const [
        dashboardResult,
        invoicesResult,
        clientsResult,
        ordersResult,
        quotationsResult,
        catalogsResult,
        settingsResult,
      ] = await Promise.all([
        getInvoiceDashboard(),
        listInvoices(),
        listClients(),
        listServiceOrders(),
        listQuotations(),
        listSatCatalogs(),
        getInvoiceSettings(),
      ]);
      setDashboard(dashboardResult);
      setInvoices(invoicesResult);
      setClients(clientsResult);
      setServiceOrders(ordersResult);
      setQuotations(quotationsResult);
      setSatCatalogs(catalogsResult);
      setSettings(settingsResult);
      return {
        invoices: invoicesResult,
        clients: clientsResult,
        serviceOrders: ordersResult,
        quotations: quotationsResult,
      };
    } catch (requestError) {
      setError(requestError.message);
      return null;
    } finally {
      setIsLoading(false);
    }
  }

  async function loadWorkbenchDependencies() {
    setIsLoading(true);
    setError('');
    try {
      const [catalogsResult, settingsResult] = await Promise.all([
        listSatCatalogs(),
        getInvoiceSettings(),
      ]);
      setSatCatalogs(catalogsResult);
      setSettings(settingsResult);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  function updateWorkspaceDraft(key, value) {
    setWorkspaceDraft((current) => ({ ...current, [key]: value }));
  }

  function updateWorkspaceConcept(conceptId, key, value) {
    setWorkspaceDraft((current) => ({
      ...current,
      concepts: {
        ...(current.concepts || {}),
        [conceptId]: {
          ...(current.concepts?.[conceptId] || {}),
          [key]: value,
        },
      },
    }));
  }

  function closeWorkspace() {
    setWorkspaceOpen(false);
    setSelectedQuotation(null);
    setSelectedServiceOrder(null);
    setSelectedClient(null);
    setSelectedInvoice(null);
    setWorkspaceDraft({});
    setWorkspaceOriginElement(null);
  }

  async function setWorkspaceSelection({ invoice, quotation, serviceOrder, client }) {
    if (!quotation) {
      throw new Error(
        'No fue posible localizar la cotización de origen del expediente.'
      );
    }
    setSelectedInvoice(invoice || null);
    setContextInvoice(invoice || null);
    setContextLoading(false);
    setContextResolved(true);
    setSelectedQuotation(quotation);
    setSelectedServiceOrder(serviceOrder || null);
    setSelectedClient(client || null);
    setWorkspaceDraft(
      await buildInvoiceWorkbenchDraft(quotation, client || null, invoice || null)
    );
    setWorkspaceOpen(true);
  }

  async function resolveContextSelection(context) {
    const normalized = normalizeInvoiceWorkbenchContext(context);
    if (!normalized) {
      throw new Error('No fue posible identificar el contexto de facturación.');
    }

    let invoice = null;
    let serviceOrder = null;
    if (normalized.invoice_id) {
      invoice = await getInvoice(normalized.invoice_id);
      if (invoice.service_order_id) {
        serviceOrder = await getServiceOrder(invoice.service_order_id);
      }
    } else {
      serviceOrder = await getServiceOrder(normalized.service_order_id);
      const contextualInvoices = await listInvoices({
        serviceOrderId: normalized.service_order_id,
      });
      invoice = contextualInvoices[0] || null;
    }
    const quotationId = invoice?.quotation_id || serviceOrder?.quotation_id;
    const quotation = quotationId ? await getQuotation(quotationId) : null;
    const clientId =
      invoice?.client_id || quotation?.client_id || serviceOrder?.client_id;
    const client = clientId ? await getClient(clientId) : null;

    return { invoice, quotation, serviceOrder, client };
  }

  async function loadContextSummary(context) {
    setError('');
    setNotice('');
    setContextLoading(true);
    setContextResolved(false);
    try {
      const selection = await resolveContextSelection(context);
      setContextInvoice(selection.invoice || null);
      return selection;
    } catch (requestError) {
      setContextInvoice(null);
      setError(requestError.message);
      return null;
    } finally {
      setContextLoading(false);
      setContextResolved(true);
    }
  }

  async function openWorkspace(row, originElement = null) {
    setWorkspaceOriginElement(originElement);
    setError('');
    setNotice('');
    setIsSaving(true);
    try {
      let invoice = row.invoice || null;
      let quotation = row.quotation || null;
      let serviceOrder = row.serviceOrder || null;
      if (invoice) {
        invoice = await getInvoice(invoice.id);
        serviceOrder =
          ordersById.get(invoice.service_order_id) ||
          serviceOrder ||
          (invoice.service_order_id
            ? await getServiceOrder(invoice.service_order_id)
            : null);
        const quotationId = invoice.quotation_id || serviceOrder?.quotation_id;
        quotation =
          quotationsById.get(quotationId) ||
          quotation ||
          (quotationId ? await getQuotation(quotationId) : null);
      }
      const clientId = invoice?.client_id || quotation?.client_id;
      const client =
        clientsById.get(clientId) || (clientId ? await getClient(clientId) : null);
      await setWorkspaceSelection({ invoice, quotation, serviceOrder, client });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function openWorkspaceByContext(context, originElement = null) {
    const normalized = normalizeInvoiceWorkbenchContext(context);
    if (!normalized) {
      setError('No fue posible identificar el contexto de facturación.');
      return false;
    }
    setWorkspaceOriginElement(originElement);
    setError('');
    setNotice('');
    setIsSaving(true);
    try {
      await setWorkspaceSelection(await resolveContextSelection(normalized));
      return true;
    } catch (requestError) {
      setError(requestError.message);
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  async function saveWorkspaceDraft() {
    if (!selectedQuotation) {
      setError('El expediente debe estar vinculado a una cotización aprobada.');
      return;
    }
    const serviceOrder =
      selectedServiceOrder ||
      (selectedInvoice?.service_order_id
        ? ordersById.get(selectedInvoice.service_order_id)
        : findOrderForQuotation(serviceOrders, selectedQuotation.id));
    if (!serviceOrder) {
      setError('La cotización todavía no tiene una orden de servicio vinculada.');
      return;
    }
    const client =
      clientsById.get(selectedQuotation.client_id) ||
      (await getClient(selectedQuotation.client_id));
    const payload = {
      client_id: selectedQuotation.client_id,
      fiscal_client_id:
        selectedInvoice?.fiscal_client_id || selectedQuotation.client_id,
      service_order_id: serviceOrder.id,
      quotation_id: selectedQuotation.id,
      issued_on:
        selectedInvoice?.issued_on || new Date().toISOString().slice(0, 10),
      due_on: selectedInvoice?.due_on || null,
      status: 'draft',
      payment_method: workspaceDraft.paymentMethod?.code || 'PUE',
      payment_form: workspaceDraft.paymentForm?.code || '03',
      usage_cfdi: workspaceDraft.cfdiUse?.code || client?.cfdi_use || 'G03',
      currency:
        workspaceDraft.currency?.code || selectedQuotation.currency || 'MXN',
      credit_days: selectedInvoice?.credit_days || 0,
      observations: selectedInvoice?.observations || null,
      internal_comments: selectedInvoice?.internal_comments || null,
      items: quotationItemsToInvoiceItems(selectedQuotation, workspaceDraft),
    };
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const savedInvoice = selectedInvoice
        ? await updateInvoice(selectedInvoice.id, payload)
        : await createInvoice(payload);
      setSelectedInvoice(savedInvoice);
      setContextInvoice(savedInvoice);
      setNotice('Borrador guardado correctamente.');
      if (loadOverview) {
        await loadBillingData();
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function getIssuerValidationError() {
    const emitter = settings?.emitter_data || {};
    if (!String(emitter.rfc || '').trim()) {
      return 'Configura el RFC del emisor antes de emitir.';
    }
    if (!/^\d{5}$/.test(String(emitter.expedition_place || '').trim())) {
      return 'Configura un lugar de expedición válido de 5 dígitos.';
    }
    return '';
  }

  async function issueWorkspaceInvoice(invoice) {
    if (!invoice) return;
    const issuerError = getIssuerValidationError();
    if (issuerError) {
      setError(issuerError);
      onIssuerConfigurationRequired?.();
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const issued = await issueInvoice(invoice.id);
      setSelectedInvoice(issued);
      setContextInvoice(issued);
      setInvoices((current) =>
        current.map((item) => (item.id === issued.id ? issued : item))
      );
      setNotice(
        issued.cfdi_uuid
          ? `CFDI emitido correctamente · UUID ${issued.cfdi_uuid}`
          : 'CFDI emitido correctamente.'
      );
      await refreshFacturamaStatus();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function downloadInstitutionalPdf(invoice) {
    if (!invoice) return;
    setIsSaving(true);
    setError('');
    try {
      const documentFile = await downloadInstitutionalInvoicePdf(invoice.id);
      saveDownloadedFile(
        documentFile,
        `Factura_MYC_${invoice.series}-${invoice.folio}.pdf`
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function downloadFiscalXml(invoice) {
    if (!invoice) return;
    setIsSaving(true);
    setError('');
    try {
      const documentFile = await downloadInvoiceFiscalXml(invoice.id);
      saveDownloadedFile(
        documentFile,
        `Factura_MYC_${invoice.series}-${invoice.folio}.xml`
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function saveSettings() {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      await updateInvoiceSettings(settings);
      setNotice('Configuración guardada.');
      await loadBillingData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  return {
    catalogByCode,
    clients,
    clientsById,
    closeWorkspace,
    contextInvoice,
    contextLoading,
    contextResolved,
    dashboard,
    downloadFiscalXml,
    downloadInstitutionalPdf,
    error,
    facturamaStatus,
    invoices,
    isLoading,
    isSaving,
    issueWorkspaceInvoice,
    loadContextSummary,
    loadBillingData,
    notice,
    openWorkspace,
    openWorkspaceByContext,
    ordersById,
    quotations,
    quotationsById,
    refreshFacturamaStatus,
    saveSettings,
    saveWorkspaceDraft,
    selectedClient,
    selectedInvoice,
    selectedQuotation,
    selectedServiceOrder,
    serviceOrders,
    setSettings,
    settings,
    updateWorkspaceConcept,
    updateWorkspaceDraft,
    workspaceDraft,
    workspaceOpen,
    workspaceOriginElement,
  };
}
