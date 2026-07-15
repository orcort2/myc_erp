import React, { useEffect, useMemo, useState } from 'react';

import InvoiceWorkbenchDialog from '../components/invoice-workbench/InvoiceWorkbenchDialog.jsx';
import { buildInvoiceWorkbenchDraft } from '../components/invoice-workbench/invoiceWorkbenchDraft.js';

import {
  changeInvoiceStatus,
  confirmInvoiceReview,
  createCreditNote,
  createInvoice,
  getInvoice,
  getInvoiceDashboard,
  getInvoicePdfUrl,
  getInvoicePaymentReceiptPdfUrl,
  getInvoiceSettings,
  listAccountsReceivable,
  listClients,
  listInvoicePayments,
  listInvoices,
  listQuotations,
  listSatCatalogs,
  listReleasedUninvoiced,
  listServiceOrders,
  registerInvoicePayment,
  updateInvoice,
  updateInvoiceSettings,
} from '../services/api.js';
import { formatDate, formatMoney } from '../utils/formatters.js';

const BILLING_TABS = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'workbench', label: 'Mesa de trabajo' },
  { key: 'invoices', label: 'Facturas' },
  { key: 'payments', label: 'Pagos' },
  { key: 'receivable', label: 'Cuentas por cobrar' },
  { key: 'creditNotes', label: 'Notas de crédito' },
  { key: 'settings', label: 'Configuración' },
];

function emptyInvoiceForm() {
  return {
    clientId: '',
    fiscalClientId: '',
    serviceOrderId: '',
    quotationId: '',
    issuedOn: new Date().toISOString().slice(0, 10),
    dueOn: '',
    paymentMethod: 'PUE',
    paymentForm: 'Transferencia',
    usageCfdi: 'G03',
    currency: 'MXN',
    creditDays: 0,
    observations: '',
    internalComments: '',
    items: [],
  };
}

const ELIGIBLE_QUOTATION_STATUSES = new Set([
  'approved',
  'accepted',
  'authorized',
]);

function isQuotationApproved(quotation) {
  return ELIGIBLE_QUOTATION_STATUSES.has(
    String(quotation?.status || '').trim().toLowerCase()
  );
}

function findOrderForQuotation(serviceOrders, quotationId) {
  return serviceOrders.find(
    (order) =>
      order.is_active !== false &&
      String(order.quotation_id) === String(quotationId)
  ) || null;
}


function resolveInvoiceQuotationId(invoice, ordersById) {
  if (invoice?.quotation_id) {
    return invoice.quotation_id;
  }

  const serviceOrder = ordersById.get(invoice?.service_order_id);
  return serviceOrder?.quotation_id || null;
}

function invoicePriority(invoice) {
  const priorities = {
    draft: 60,
    pending: 50,
    issued: 40,
    partially_paid: 30,
    overdue: 25,
    paid: 20,
    cancelled: 10,
  };

  return priorities[invoice?.status] || 0;
}

function quotationItemsToInvoiceItems(quotation, draft) {
  return (quotation?.items || [])
    .filter((item) => item.is_active !== false)
    .map((item) => {
      const fiscal = draft?.concepts?.[item.id] || {};
      const rateCode = fiscal.taxRate?.code;
      const taxRate = rateCode ? Number(rateCode) * 100 : Number(item.tax_rate || 16);

      return {
        quotation_item_id: item.id,
        description: item.description || item.service_name || 'Servicio de calibracion',
        quantity: Number(item.quantity || 1),
        unit: item.unit || 'Servicio',
        sat_unit: fiscal.unit?.code || item.sat_unit || 'E48',
        sat_key: fiscal.productService?.code || item.sat_key || '81141504',
        unit_price: Number(item.unit_price || 0),
        discount_total: Number(item.discount_total || 0),
        tax_rate: taxRate,
        notes: item.notes || null,
        service_type: item.service_type || item.service_name || null,
        source_type: 'quotation',
      };
    });
}


function BillingPage() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [dashboard, setDashboard] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [payments, setPayments] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [releasedUninvoiced, setReleasedUninvoiced] = useState([]);
  const [clients, setClients] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [satCatalogs, setSatCatalogs] = useState([]);
  const [settings, setSettings] = useState(null);
  const [invoiceForm, setInvoiceForm] = useState(emptyInvoiceForm());
  const [paymentForm, setPaymentForm] = useState({ invoiceId: '', paidOn: new Date().toISOString().slice(0, 10), amount: '', bankName: '', reference: '', paymentMethod: 'PUE', paymentForm: 'Transferencia', notes: '' });
  const [creditNoteForm, setCreditNoteForm] = useState({ invoiceId: '', issuedOn: new Date().toISOString().slice(0, 10), reason: '', subtotal: '0.00', taxTotal: '0.00', total: '0.00', status: 'draft', observations: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [workbenchOpen, setWorkbenchOpen] = useState(false);
  const [selectedQuotation, setSelectedQuotation] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [workbenchDraft, setWorkbenchDraft] = useState({});
  const [workbenchSearch, setWorkbenchSearch] = useState('');
  const [workbenchOriginElement, setWorkbenchOriginElement] = useState(null);

  const clientsById = useMemo(() => new Map(clients.map((item) => [item.id, item])), [clients]);
  const ordersById = useMemo(() => new Map(serviceOrders.map((item) => [item.id, item])), [serviceOrders]);
  const quotationsById = useMemo(() => new Map(quotations.map((item) => [item.id, item])), [quotations]);
  const catalogByCode = useMemo(() => new Map(satCatalogs.map((item) => [item.code, item])), [satCatalogs]);
  const draftInvoices = useMemo(() => invoices.filter((invoice) => invoice.status === 'draft'), [invoices]);
  const issuedInvoices = useMemo(() => invoices.filter((invoice) => invoice.status !== 'draft'), [invoices]);

  const invoiceByQuotationId = useMemo(() => {
    const result = new Map();

    for (const invoice of invoices) {
      const quotationId = resolveInvoiceQuotationId(
        invoice,
        ordersById
      );

      if (!quotationId) continue;

      const key = String(quotationId);
      const current = result.get(key);

      if (
        !current ||
        invoicePriority(invoice) > invoicePriority(current)
      ) {
        result.set(key, invoice);
      }
    }

    return result;
  }, [invoices, ordersById]);

  const workbenchProspects = useMemo(() => {
    return quotations
      .filter(isQuotationApproved)
      .map((quotation) => {
        const serviceOrder = findOrderForQuotation(
          serviceOrders,
          quotation.id
        );

        if (!serviceOrder) return null;

        const invoice =
          invoiceByQuotationId.get(String(quotation.id)) || null;

        return {
          key: `quotation-${quotation.id}`,
          quotation,
          invoice,
          client: clientsById.get(quotation.client_id),
          serviceOrder,
        };
      })
      .filter(Boolean);
  }, [
    clientsById,
    invoiceByQuotationId,
    quotations,
    serviceOrders,
  ]);

  const orphanDrafts = useMemo(() => {
    const representedInvoiceIds = new Set(
      workbenchProspects
        .map((row) => row.invoice?.id)
        .filter(Boolean)
    );

    return draftInvoices
      .filter((invoice) => !representedInvoiceIds.has(invoice.id))
      .map((invoice) => {
        const serviceOrder =
          ordersById.get(invoice.service_order_id) || null;
        const resolvedQuotationId = resolveInvoiceQuotationId(
          invoice,
          ordersById
        );
        const quotation =
          quotationsById.get(resolvedQuotationId) || null;

        return {
          key: `invoice-${invoice.id}`,
          quotation,
          invoice,
          client: clientsById.get(invoice.client_id),
          serviceOrder,
        };
      });
  }, [
    clientsById,
    draftInvoices,
    ordersById,
    quotationsById,
    workbenchProspects,
  ]);

  const visibleWorkbenchRows = useMemo(() => {
    const term = workbenchSearch.trim().toLowerCase();
    const rows = [...workbenchProspects, ...orphanDrafts];

    if (!term) return rows;

    return rows.filter((row) => [
      row.invoice?.folio,
      row.quotation?.folio,
      row.client?.commercial_name,
      row.client?.legal_name,
      row.client?.rfc,
      row.serviceOrder?.work_order_number,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(term));
  }, [orphanDrafts, workbenchProspects, workbenchSearch]);

  const readyProspectsCount = useMemo(
    () =>
      workbenchProspects.filter(
        (row) => !row.invoice || row.invoice.status === 'cancelled'
      ).length,
    [workbenchProspects]
  );

  const draftProspectsCount = useMemo(
    () =>
      workbenchProspects.filter(
        (row) => row.invoice?.status === 'draft'
      ).length + orphanDrafts.length,
    [orphanDrafts.length, workbenchProspects]
  );

  useEffect(() => {
    loadBillingData();
  }, []);

  async function loadBillingData() {
    setIsLoading(true);
    setError('');
    try {
      const [
        dashboardResult,
        invoicesResult,
        paymentsResult,
        accountsResult,
        releasedResult,
        clientsResult,
        ordersResult,
        quotationsResult,
        catalogsResult,
        settingsResult,
      ] = await Promise.all([
        getInvoiceDashboard(),
        listInvoices(),
        listInvoicePayments(),
        listAccountsReceivable(),
        listReleasedUninvoiced(),
        listClients(),
        listServiceOrders(),
        listQuotations(),
        listSatCatalogs(),
        getInvoiceSettings(),
      ]);
      setDashboard(dashboardResult);
      setInvoices(invoicesResult);
      setPayments(paymentsResult);
      setAccounts(accountsResult);
      setReleasedUninvoiced(releasedResult);
      setClients(clientsResult);
      setServiceOrders(ordersResult);
      setQuotations(quotationsResult);
      setSatCatalogs(catalogsResult);
      setSettings(settingsResult);

      const storedOrderId = window.localStorage.getItem('myc_billing_order_id');
      if (storedOrderId) {
        const order = ordersResult.find((item) => String(item.id) === String(storedOrderId));
        const quotation = order
          ? quotationsResult.find((item) => String(item.id) === String(order.quotation_id))
          : null;

        if (quotation) {
          const client = clientsResult.find((item) => item.id === quotation.client_id);
          setSelectedQuotation(quotation);
          setSelectedInvoice(null);
          setWorkbenchDraft(await buildInvoiceWorkbenchDraft(quotation, client));
          setWorkbenchOpen(true);
        }

        window.localStorage.removeItem('myc_billing_order_id');
        setActiveTab('workbench');
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  function updateInvoiceForm(field, value) {
    setInvoiceForm((current) => ({ ...current, [field]: value }));
  }

  function updateWorkbenchDraft(key, value) {
    setWorkbenchDraft((current) => ({ ...current, [key]: value }));
  }

  function updateWorkbenchConcept(conceptId, key, value) {
    setWorkbenchDraft((current) => ({
      ...current,
      concepts: {
        ...(current.concepts || {}),
        [conceptId]: { ...(current.concepts?.[conceptId] || {}), [key]: value },
      },
    }));
  }

  function closeWorkbench() {
    setWorkbenchOpen(false);
    setSelectedQuotation(null);
    setSelectedInvoice(null);
    setWorkbenchDraft({});
    setWorkbenchOriginElement(null);
  }

  async function openQuotationWorkbench(quotation, originElement = null) {
    const client = clientsById.get(quotation.client_id);
    setWorkbenchOriginElement(originElement);
    setSelectedQuotation(quotation);
    setSelectedInvoice(null);
    setWorkbenchDraft({});
    setWorkbenchOpen(true);
    setWorkbenchDraft(await buildInvoiceWorkbenchDraft(quotation, client));
  }

  async function openInvoiceWorkbench(
    invoiceSummary,
    originElement = null
  ) {
    setWorkbenchOriginElement(originElement);
    setIsSaving(true);
    setError('');
    try {
      const invoice = await getInvoice(invoiceSummary.id);
      const serviceOrder =
        ordersById.get(invoice.service_order_id) || null;
      const quotationId =
        invoice.quotation_id || serviceOrder?.quotation_id;
      const quotation =
        quotationsById.get(quotationId) || null;
      const client = clientsById.get(invoice.client_id);
      setSelectedInvoice(invoice);
      setSelectedQuotation(quotation);
      setWorkbenchDraft(await buildInvoiceWorkbenchDraft(quotation, client, invoice));
      setWorkbenchOpen(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSaveWorkbenchDraft() {
    if (!selectedQuotation) {
      setError('El borrador debe estar vinculado a una cotizacion aprobada.');
      return;
    }

    const serviceOrder = selectedInvoice?.service_order_id
      ? ordersById.get(selectedInvoice.service_order_id)
      : findOrderForQuotation(serviceOrders, selectedQuotation.id);

    if (!serviceOrder) {
      setError('La cotizacion todavia no tiene una orden de servicio vinculada.');
      return;
    }

    const client = clientsById.get(selectedQuotation.client_id);
    const payload = {
      client_id: selectedQuotation.client_id,
      fiscal_client_id: selectedInvoice?.fiscal_client_id || selectedQuotation.client_id,
      service_order_id: serviceOrder.id,
      quotation_id: selectedQuotation.id,
      issued_on: selectedInvoice?.issued_on || new Date().toISOString().slice(0, 10),
      due_on: selectedInvoice?.due_on || null,
      status: 'draft',
      payment_method: workbenchDraft.paymentMethod?.code || 'PUE',
      payment_form: workbenchDraft.paymentForm?.code || '03',
      usage_cfdi: workbenchDraft.cfdiUse?.code || client?.cfdi_use || 'G03',
      currency: workbenchDraft.currency?.code || selectedQuotation.currency || 'MXN',
      credit_days: selectedInvoice?.credit_days || 0,
      observations: selectedInvoice?.observations || null,
      internal_comments: selectedInvoice?.internal_comments || null,
      items: quotationItemsToInvoiceItems(selectedQuotation, workbenchDraft),
    };

    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      await (selectedInvoice
        ? updateInvoice(selectedInvoice.id, payload)
        : createInvoice(payload));
      setNotice(selectedInvoice ? 'Borrador actualizado' : 'Borrador creado');
      await loadBillingData();
      closeWorkbench();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleIssueFromWorkbench() {
    if (!selectedInvoice) {
      setError('Guarda el borrador antes de emitir.');
      return;
    }
    if (selectedInvoice.review_required) {
      setError('Confirma la revision del borrador antes de emitir.');
      return;
    }
    await moveInvoiceToIssued(selectedInvoice.id);
    closeWorkbench();
  }


  async function handleRegisterPayment(event) {
    event.preventDefault();
    if (!paymentForm.invoiceId) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      await registerInvoicePayment(Number(paymentForm.invoiceId), {
        paid_on: paymentForm.paidOn,
        amount: Number(paymentForm.amount || 0),
        bank_name: paymentForm.bankName || null,
        reference: paymentForm.reference || null,
        payment_method: paymentForm.paymentMethod || null,
        payment_form: paymentForm.paymentForm || null,
        notes: paymentForm.notes || null,
        status: 'pending',
      });
      setNotice('Pago registrado');
      setPaymentForm({ invoiceId: '', paidOn: new Date().toISOString().slice(0, 10), amount: '', bankName: '', reference: '', paymentMethod: 'PUE', paymentForm: 'Transferencia', notes: '' });
      await loadBillingData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCreateCreditNote(event) {
    event.preventDefault();
    if (!creditNoteForm.invoiceId) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      await createCreditNote(Number(creditNoteForm.invoiceId), {
        issued_on: creditNoteForm.issuedOn,
        reason: creditNoteForm.reason,
        subtotal: Number(creditNoteForm.subtotal || 0),
        tax_total: Number(creditNoteForm.taxTotal || 0),
        total: Number(creditNoteForm.total || 0),
        status: creditNoteForm.status,
        observations: creditNoteForm.observations || null,
      });
      setNotice('Nota de crédito registrada');
      setCreditNoteForm({ invoiceId: '', issuedOn: new Date().toISOString().slice(0, 10), reason: '', subtotal: '0.00', taxTotal: '0.00', total: '0.00', status: 'draft', observations: '' });
      await loadBillingData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleSaveSettings(event) {
    event.preventDefault();
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      await updateInvoiceSettings(settings);
      setNotice('Configuración guardada');
      await loadBillingData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleConfirmInvoiceReview(invoiceId) {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      await confirmInvoiceReview(invoiceId);
      setNotice('Borrador revisado y confirmado');
      await loadBillingData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function moveInvoiceToIssued(invoiceId) {
    setIsSaving(true);
    setError('');
    try {
      await changeInvoiceStatus(invoiceId, { status: 'issued' });
      setNotice('Factura emitida');
      await loadBillingData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="module-workspace">
      <div className="module-workspace__hero">
        <div>
          <p>Facturación</p>
          <h1>Facturas, pagos y cobranza</h1>
          <span>Control administrativo posterior a la liberación de certificados.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-success dashboard-success">{notice}</div> : null}

      <section className="settings-card">
        <div className="settings-tabs" role="tablist" aria-label="Facturación">
          {BILLING_TABS.map((tab) => (
            <button key={tab.key} className={`settings-tab ${activeTab === tab.key ? 'is-active' : ''}`} onClick={() => setActiveTab(tab.key)} type="button">
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'dashboard' ? (
          <section className="quotation-section">
            <div className="quotation-commercial-grid service-order-info-grid">
              <article><span>Facturas pendientes</span><strong>{dashboard?.facturas_pendientes ?? '-'}</strong></article>
              <article><span>Facturas vencidas</span><strong>{dashboard?.facturas_vencidas ?? '-'}</strong></article>
              <article><span>Cobrado mes</span><strong>{formatMoney(dashboard?.total_cobrado_mes ?? 0)}</strong></article>
              <article><span>Pendiente por cobrar</span><strong>{formatMoney(dashboard?.saldo_pendiente_total ?? 0)}</strong></article>
              <article><span>Total facturado mes</span><strong>{formatMoney(dashboard?.total_facturado_mes ?? 0)}</strong></article>
              <article><span>Pagos hoy</span><strong>{formatMoney(dashboard?.pagos_hoy ?? 0)}</strong></article>
            </div>
            <div className="quotation-section__title">
              <p>Servicios liberados sin factura</p>
              <h3>{releasedUninvoiced.length}</h3>
            </div>
            <div className="field-sheet-prep-list">
              {releasedUninvoiced.map((item) => (
                <article className="glass-card-mini" key={item.service_order_id}>
                  <strong>{item.client_name}</strong>
                  <span>OT {item.work_order_number || '-'}</span>
                  <small>{item.uninvoiced_certificates} certificados sin facturar</small>
                  <button className="table-button" onClick={() => {
                    setActiveTab('workbench');
                    updateInvoiceForm('serviceOrderId', String(item.service_order_id));
                  }} type="button">Crear factura</button>
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {activeTab === 'workbench' ? (
          <section className="invoice-quotation-workspace">
            <div className="invoice-workspace-metrics">
              <article className="invoice-workspace-metric is-ready"><div><span>Listas para facturar</span><strong>{readyProspectsCount}</strong></div></article>
              <article className="invoice-workspace-metric is-draft"><div><span>Borradores</span><strong>{draftProspectsCount}</strong></div></article>
              <article className="invoice-workspace-metric is-stamped"><div><span>Facturas emitidas</span><strong>{issuedInvoices.length}</strong></div></article>
              <article className="invoice-workspace-metric is-cancelled"><div><span>Revision requerida</span><strong>{draftInvoices.filter((invoice) => invoice.review_required).length}</strong></div></article>
            </div>

            <section className="invoice-quotation-list">
              <div className="invoice-section-heading">
                <div><p>Mesa de trabajo</p><h2>Cotizaciones y borradores</h2></div>
                <span>{visibleWorkbenchRows.length} registro{visibleWorkbenchRows.length === 1 ? '' : 's'}</span>
              </div>

              <label className="invoice-search">
                <input onChange={(event) => setWorkbenchSearch(event.target.value)} placeholder="Buscar por cotizacion, cliente, RFC, orden o folio..." value={workbenchSearch} />
              </label>

              <div className="invoice-workspace-table-wrapper">
                <div className="invoice-workspace-table">
                  <div aria-hidden="true" className="invoice-workspace-table__header"><span>Estado</span><span>Documento</span><span>Cliente</span><span>Orden</span><span>Importe</span></div>
                  <div className="invoice-workspace-table__body">
                    {isLoading ? <p className="empty-state">Cargando mesa de trabajo...</p> : null}
                    {!isLoading && !visibleWorkbenchRows.length ? <p className="empty-state">No hay cotizaciones habilitadas ni borradores que coincidan con la busqueda.</p> : null}
                    {!isLoading ? visibleWorkbenchRows.map((row) => {
                      const invoice = row.invoice;
                      const isDraft = invoice?.status === 'draft';
                      const requiresReview = Boolean(
                        invoice?.review_required
                      );
                      const isIssued = invoice &&
                        !['draft', 'cancelled'].includes(invoice.status);
                      const document =
                        row.quotation?.folio ||
                        invoice?.folio ||
                        'Sin folio';
                      const clientName =
                        row.client?.commercial_name ||
                        row.client?.legal_name ||
                        `Cliente #${
                          row.quotation?.client_id ||
                          invoice?.client_id ||
                          '-'
                        }`;
                      const amount =
                        invoice?.total ??
                        row.quotation?.total ??
                        0;
                      const statusLabel = requiresReview
                        ? 'Revisión requerida'
                        : isDraft
                          ? 'Borrador'
                          : isIssued
                            ? 'Emitida'
                            : 'Lista para facturar';
                      const statusClass = requiresReview
                        ? 'is-cancelled'
                        : isDraft
                          ? 'is-draft'
                          : isIssued
                            ? 'is-stamped'
                            : 'is-ready';

                      const openRow = (originElement) => {
                        if (isDraft) {
                          openInvoiceWorkbench(
                            invoice,
                            originElement
                          );
                          return;
                        }

                        if (!invoice || invoice.status === 'cancelled') {
                          openQuotationWorkbench(
                            row.quotation,
                            originElement
                          );
                        }
                      };

                      return (
                        <article
                          aria-disabled={isIssued ? 'true' : undefined}
                          className={`invoice-workspace-row ${statusClass}${
                            isIssued ? ' is-readonly' : ''
                          }`}
                          key={row.key}
                          onClick={(event) =>
                            openRow(event.currentTarget)
                          }
                          onKeyDown={(event) => {
                            if (
                              isIssued ||
                              (event.key !== 'Enter' &&
                                event.key !== ' ')
                            ) {
                              return;
                            }

                            event.preventDefault();
                            openRow(event.currentTarget);
                          }}
                          role="button"
                          tabIndex={isIssued ? -1 : 0}
                        >
                          <div
                            className="invoice-workspace-row__status"
                            data-label="Estado"
                          >
                            <span className="invoice-billing-status">
                              <i aria-hidden="true" />
                              {statusLabel}
                            </span>
                          </div>

                          <div
                            className="invoice-workspace-row__folio"
                            data-label="Documento"
                          >
                            <strong>{document}</strong>
                          </div>

                          <div
                            className="invoice-workspace-row__client"
                            data-label="Cliente"
                          >
                            <strong>{clientName}</strong>
                            {row.client?.rfc ? (
                              <span>{row.client.rfc}</span>
                            ) : null}
                          </div>

                          <div data-label="Orden">
                            <span>
                              {row.serviceOrder?.work_order_number ||
                                '-'}
                            </span>
                          </div>

                          <div
                            className="invoice-workspace-row__amount"
                            data-label="Importe"
                          >
                            <strong>{formatMoney(amount)}</strong>
                          </div>
                        </article>
                      );
                    }) : null}
                  </div>
                </div>
              </div>

              <footer className="invoice-workspace-table__footer"><span>Selecciona una cotizacion para preparar su factura o un borrador para continuarlo.</span><strong>Solo se habilitan cotizaciones aprobadas con orden de servicio generada.</strong></footer>
            </section>

            <InvoiceWorkbenchDialog
              canIssue={Boolean(selectedInvoice) && !selectedInvoice?.review_required}
              catalogByCode={catalogByCode}
              client={selectedQuotation ? clientsById.get(selectedQuotation.client_id) : selectedInvoice ? clientsById.get(selectedInvoice.client_id) : null}
              draft={workbenchDraft}
              invoice={selectedInvoice}
              isSaving={isSaving}
              originElement={workbenchOriginElement}
              onClose={closeWorkbench}
              onConceptChange={updateWorkbenchConcept}
              onDraftChange={updateWorkbenchDraft}
              onIssue={handleIssueFromWorkbench}
              onSaveDraft={handleSaveWorkbenchDraft}
              open={workbenchOpen}
              quotation={selectedQuotation}
            />
          </section>
        ) : null}

        {activeTab === 'invoices' ? (
          <>
            <section className="quotation-section">
              <div className="quotation-section__title">
                <p>Facturas</p>
                <h3>{isLoading ? 'Cargando...' : issuedInvoices.length}</h3>
              </div>
              <div className="table-shell">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Folio</th>
                      <th>Cliente</th>
                      <th>Orden</th>
                      <th>Fecha</th>
                      <th>Total</th>
                      <th>Saldo</th>
                      <th>Estado</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {issuedInvoices.map((invoice) => (
                      <tr key={invoice.id}>
                        <td>{invoice.series}-{invoice.folio}</td>
                        <td>{clientsById.get(invoice.client_id)?.commercial_name || clientsById.get(invoice.client_id)?.legal_name || '-'}</td>
                        <td>{ordersById.get(invoice.service_order_id)?.work_order_number || '-'}</td>
                        <td>{formatDate(invoice.issued_on)}</td>
                        <td>{formatMoney(invoice.total)}</td>
                        <td>{formatMoney(invoice.balance_due)}</td>
                        <td>{invoice.status}</td>
                        <td>
                          <a className="table-button" href={getInvoicePdfUrl(invoice.id)} rel="noreferrer" target="_blank">PDF</a>
                          {invoice.status === 'draft' || invoice.status === 'pending' ? (
                            <button className="table-button table-button--primary" disabled={isSaving} onClick={() => moveInvoiceToIssued(invoice.id)} type="button">Emitir</button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

          </>
        ) : null}

        {activeTab === 'payments' ? (
          <>
            <section className="quotation-section">
              <div className="quotation-section__title"><p>Pagos</p><h3>{payments.length}</h3></div>
              <div className="table-shell">
                <table className="table">
                  <thead><tr><th>Factura</th><th>Fecha</th><th>Monto</th><th>Banco</th><th>Referencia</th><th>Recibo</th></tr></thead>
                  <tbody>
                    {payments.map((payment) => (
                      <tr key={payment.id}>
                        <td>{payment.invoice_id}</td>
                        <td>{formatDate(payment.paid_on)}</td>
                        <td>{formatMoney(payment.amount)}</td>
                        <td>{payment.bank_name || '-'}</td>
                        <td>{payment.reference || '-'}</td>
                        <td><a className="table-button" href={getInvoicePaymentReceiptPdfUrl(payment.id)} rel="noreferrer" target="_blank">PDF</a></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            <section className="quotation-section">
              <div className="quotation-section__title"><p>Registrar pago</p><h3>Pago parcial o total</h3></div>
              <form className="client-form client-form--modal" onSubmit={handleRegisterPayment}>
                <label>
                  Factura
                  <select value={paymentForm.invoiceId} onChange={(event) => setPaymentForm((current) => ({ ...current, invoiceId: event.target.value }))}>
                    <option value="">Selecciona</option>
                    {invoices.map((invoice) => (
                      <option key={invoice.id} value={invoice.id}>{invoice.series}-{invoice.folio} · {formatMoney(invoice.balance_due)}</option>
                    ))}
                  </select>
                </label>
                <label><span>Fecha</span><input type="date" value={paymentForm.paidOn} onChange={(event) => setPaymentForm((current) => ({ ...current, paidOn: event.target.value }))} /></label>
                <label><span>Monto</span><input value={paymentForm.amount} onChange={(event) => setPaymentForm((current) => ({ ...current, amount: event.target.value }))} /></label>
                <label><span>Banco</span><input value={paymentForm.bankName} onChange={(event) => setPaymentForm((current) => ({ ...current, bankName: event.target.value }))} /></label>
                <label><span>Referencia</span><input value={paymentForm.reference} onChange={(event) => setPaymentForm((current) => ({ ...current, reference: event.target.value }))} /></label>
                <button className="primary-button" disabled={isSaving} type="submit">Registrar pago</button>
              </form>
            </section>
          </>
        ) : null}

        {activeTab === 'receivable' ? (
          <section className="quotation-section">
            <div className="quotation-section__title"><p>Cuentas por cobrar</p><h3>{accounts.length}</h3></div>
            <div className="table-shell">
              <table className="table">
                <thead><tr><th>Factura</th><th>Cliente</th><th>Saldo</th><th>Vencimiento</th><th>Antigüedad</th></tr></thead>
                <tbody>
                  {accounts.map((row) => (
                    <tr key={row.invoice_id}>
                      <td>{row.invoice_folio}</td>
                      <td>{row.client_name}</td>
                      <td>{formatMoney(row.balance_due)}</td>
                      <td>{formatDate(row.due_on)}</td>
                      <td>{row.aging_bucket}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}

        {activeTab === 'creditNotes' ? (
          <section className="quotation-section">
            <div className="quotation-section__title"><p>Notas de crédito</p><h3>Registro interno</h3></div>
            <form className="client-form client-form--modal" onSubmit={handleCreateCreditNote}>
              <label>
                Factura
                <select value={creditNoteForm.invoiceId} onChange={(event) => setCreditNoteForm((current) => ({ ...current, invoiceId: event.target.value }))}>
                  <option value="">Selecciona</option>
                  {invoices.map((invoice) => (
                    <option key={invoice.id} value={invoice.id}>{invoice.series}-{invoice.folio}</option>
                  ))}
                </select>
              </label>
              <label><span>Fecha</span><input type="date" value={creditNoteForm.issuedOn} onChange={(event) => setCreditNoteForm((current) => ({ ...current, issuedOn: event.target.value }))} /></label>
              <label><span>Motivo</span><textarea value={creditNoteForm.reason} onChange={(event) => setCreditNoteForm((current) => ({ ...current, reason: event.target.value }))} /></label>
              <label><span>Total</span><input value={creditNoteForm.total} onChange={(event) => setCreditNoteForm((current) => ({ ...current, total: event.target.value, subtotal: event.target.value }))} /></label>
              <button className="primary-button" disabled={isSaving} type="submit">Registrar nota</button>
            </form>
          </section>
        ) : null}

        {activeTab === 'settings' && settings ? (
          <section className="quotation-section">
            <div className="quotation-section__title"><p>Configuración</p><h3>Facturación</h3></div>
            <form className="client-form client-form--modal" onSubmit={handleSaveSettings}>
              <label><span>Serie default</span><input value={settings.default_series || ''} onChange={(event) => setSettings((current) => ({ ...current, default_series: event.target.value }))} /></label>
              <label><span>Siguiente folio</span><input value={settings.next_sequence || 1} onChange={(event) => setSettings((current) => ({ ...current, next_sequence: Number(event.target.value || 1) }))} /></label>
              <label><span>IVA default</span><input value={settings.default_tax_rate || 16} onChange={(event) => setSettings((current) => ({ ...current, default_tax_rate: Number(event.target.value || 16) }))} /></label>
              <label><span>Moneda default</span><input value={settings.default_currency || 'MXN'} onChange={(event) => setSettings((current) => ({ ...current, default_currency: event.target.value }))} /></label>
              <label><span>Días de crédito</span><input value={settings.default_credit_days || 0} onChange={(event) => setSettings((current) => ({ ...current, default_credit_days: Number(event.target.value || 0) }))} /></label>
              <label><span>Razón social MYC</span><input value={settings.emitter_data?.legal_name || ''} onChange={(event) => setSettings((current) => ({ ...current, emitter_data: { ...(current.emitter_data || {}), legal_name: event.target.value } }))} /></label>
              <label><span>RFC MYC</span><input value={settings.emitter_data?.rfc || ''} onChange={(event) => setSettings((current) => ({ ...current, emitter_data: { ...(current.emitter_data || {}), rfc: event.target.value } }))} /></label>
              <label><span>Correos cobranza</span><textarea value={(settings.billing_emails?.items || []).join(', ')} onChange={(event) => setSettings((current) => ({ ...current, billing_emails: { items: event.target.value.split(',').map((item) => item.trim()).filter(Boolean) } }))} /></label>
              <button className="primary-button" disabled={isSaving} type="submit">Guardar configuración</button>
            </form>
          </section>
        ) : null}
      </section>
    </section>
  );
}

export default BillingPage;
