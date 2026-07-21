import React, { useMemo, useState } from 'react';
import {
  FileText,
  LayoutDashboard,
  RefreshCw,
  Search,
  Settings2,
} from 'lucide-react';

import InvoiceWorkbenchDialog from '../components/invoice-workbench/InvoiceWorkbenchDialog.jsx';
import useInvoiceWorkbenchController, {
  findOrderForQuotation,
} from '../components/invoice-workbench/useInvoiceWorkbenchController.js';
import {
  clearInvoiceWorkbenchContext,
  readInvoiceWorkbenchContext,
} from '../utils/invoiceWorkbenchContext.js';
import { formatMoney } from '../utils/formatters.js';

const MAIN_VIEWS = [
  { key: 'center', label: 'Centro de facturación', icon: FileText },
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'settings', label: 'Configuración', icon: Settings2 },
];

const ELIGIBLE_QUOTATION_STATUSES = new Set([
  'approved',
  'accepted',
  'authorized',
]);

const INVOICE_STATUS = {
  ready: {
    label: 'Lista para facturar',
    className: 'is-ready',
  },
  draft: {
    label: 'Borrador',
    className: 'is-draft',
  },
  review_required: {
    label: 'Revisión requerida',
    className: 'is-cancelled',
  },
  issuing: {
    label: 'Emitiendo',
    className: 'is-draft',
  },
  issued: {
    label: 'Emitida',
    className: 'is-stamped',
  },
  partially_paid: {
    label: 'Pago parcial',
    className: 'is-stamped',
  },
  paid: {
    label: 'Pagada',
    className: 'is-stamped',
  },
  overdue: {
    label: 'Vencida',
    className: 'is-cancelled',
  },
  issue_failed: {
    label: 'Error de emisión',
    className: 'is-cancelled',
  },
  cancelled: {
    label: 'Cancelada',
    className: 'is-cancelled',
  },
};

function isQuotationApproved(quotation) {
  return ELIGIBLE_QUOTATION_STATUSES.has(
    String(quotation?.status || '').trim().toLowerCase()
  );
}

function resolveInvoiceQuotationId(invoice, ordersById) {
  if (invoice?.quotation_id) return invoice.quotation_id;

  const serviceOrder = ordersById.get(invoice?.service_order_id);
  return serviceOrder?.quotation_id || null;
}

function invoicePriority(invoice) {
  const priorities = {
    issuing: 90,
    draft: 80,
    issue_failed: 75,
    issued: 70,
    partially_paid: 60,
    overdue: 55,
    paid: 50,
    pending: 40,
    cancelled: 10,
  };

  return priorities[invoice?.status] || 0;
}

function resolveWorkspaceStatus(invoice) {
  if (!invoice || invoice.status === 'cancelled') {
    return INVOICE_STATUS.ready;
  }

  if (invoice.review_required) {
    return INVOICE_STATUS.review_required;
  }

  return INVOICE_STATUS[invoice.status] || {
    label: invoice.status || 'Sin estado',
    className: 'is-draft',
  };
}

function BillingPage() {
  const [activeView, setActiveView] = useState('center');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const initialContext = useMemo(
    () => readInvoiceWorkbenchContext(window.location),
    []
  );
  const {
    catalogByCode,
    clientsById,
    closeWorkspace,
    dashboard,
    downloadFiscalXml: handleDownloadFiscalXml,
    downloadInstitutionalPdf: handleDownloadInstitutionalPdf,
    error,
    facturamaStatus,
    invoices,
    isLoading,
    isSaving,
    issueWorkspaceInvoice: handleIssueInvoice,
    loadBillingData,
    notice,
    openWorkspace,
    ordersById,
    quotations,
    quotationsById,
    refreshFacturamaStatus,
    saveSettings,
    saveWorkspaceDraft: handleSaveWorkspaceDraft,
    selectedClient,
    selectedInvoice,
    selectedQuotation,
    serviceOrders,
    setSettings,
    settings,
    updateWorkspaceConcept,
    updateWorkspaceDraft,
    workspaceDraft,
    workspaceOpen,
    workspaceOriginElement,
  } = useInvoiceWorkbenchController({
    initialContext,
    onIssuerConfigurationRequired: () => setActiveView('settings'),
  });

  const invoiceByQuotationId = useMemo(() => {
    const result = new Map();

    for (const invoice of invoices) {
      const quotationId = resolveInvoiceQuotationId(invoice, ordersById);
      if (!quotationId) continue;

      const key = String(quotationId);
      const current = result.get(key);

      if (!current || invoicePriority(invoice) > invoicePriority(current)) {
        result.set(key, invoice);
      }
    }

    return result;
  }, [invoices, ordersById]);

  const workspaceRows = useMemo(() => {
    const rows = quotations
      .filter(isQuotationApproved)
      .map((quotation) => {
        const serviceOrder = findOrderForQuotation(
          serviceOrders,
          quotation.id
        );
        if (!serviceOrder) return null;

        const invoice =
          invoiceByQuotationId.get(String(quotation.id)) || null;
        const client = clientsById.get(quotation.client_id) || null;
        const status = resolveWorkspaceStatus(invoice);

        return {
          key: `quotation-${quotation.id}`,
          quotation,
          invoice,
          client,
          serviceOrder,
          status,
          amount: invoice?.total ?? quotation.total ?? 0,
        };
      })
      .filter(Boolean);

    const representedInvoiceIds = new Set(
      rows.map((row) => row.invoice?.id).filter(Boolean)
    );

    for (const invoice of invoices) {
      if (representedInvoiceIds.has(invoice.id)) continue;
      if (invoice.status === 'cancelled') continue;

      const serviceOrder = ordersById.get(invoice.service_order_id) || null;
      const quotationId = resolveInvoiceQuotationId(invoice, ordersById);
      const quotation = quotationsById.get(quotationId) || null;
      const client = clientsById.get(invoice.client_id) || null;

      rows.push({
        key: `invoice-${invoice.id}`,
        quotation,
        invoice,
        client,
        serviceOrder,
        status: resolveWorkspaceStatus(invoice),
        amount: invoice.total ?? quotation?.total ?? 0,
      });
    }

    return rows.sort((a, b) => {
      const priorityDifference =
        invoicePriority(b.invoice) - invoicePriority(a.invoice);
      if (priorityDifference !== 0) return priorityDifference;

      const aFolio = a.quotation?.folio || a.invoice?.folio || '';
      const bFolio = b.quotation?.folio || b.invoice?.folio || '';
      return String(aFolio).localeCompare(String(bFolio));
    });
  }, [
    clientsById,
    invoiceByQuotationId,
    invoices,
    ordersById,
    quotations,
    quotationsById,
    serviceOrders,
  ]);

  const visibleRows = useMemo(() => {
    const term = search.trim().toLowerCase();

    return workspaceRows.filter((row) => {
      if (
        statusFilter !== 'all' &&
        row.status.label !== statusFilter
      ) {
        return false;
      }

      if (!term) return true;

      return [
        row.quotation?.folio,
        row.invoice?.folio,
        row.invoice?.cfdi_uuid,
        row.client?.commercial_name,
        row.client?.legal_name,
        row.client?.rfc,
        row.serviceOrder?.work_order_number,
        row.status.label,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(term);
    });
  }, [search, statusFilter, workspaceRows]);

  const metrics = useMemo(() => {
    const count = (predicate) => workspaceRows.filter(predicate).length;

    return {
      ready: count((row) => row.status.label === 'Lista para facturar'),
      drafts: count((row) =>
        ['Borrador', 'Revisión requerida', 'Error de emisión'].includes(
          row.status.label
        )
      ),
      issued: count((row) =>
        ['Emitida', 'Pago parcial', 'Pagada', 'Vencida'].includes(
          row.status.label
        )
      ),
      review: count((row) => row.status.label === 'Revisión requerida'),
    };
  }, [workspaceRows]);

  function handleCloseWorkspace() {
    clearInvoiceWorkbenchContext();
    closeWorkspace();
  }

  function handleSaveSettings(event) {
    event.preventDefault();
    saveSettings();
  }

  return (
    <section className="module-workspace">
      <div className="module-workspace__hero">
        <span className="module-workspace__icon">
          <FileText size={28} />
        </span>
        <div>
          <p>Módulo MYC SYSTEM</p>
          <h1>Centro de facturación</h1>
          <span>
            Cada cotización elegible concentra su borrador, CFDI, pagos,
            cobranza, documentos e historial en un solo expediente.
          </span>
        </div>
      </div>

      {error ? (
        <div className="form-error dashboard-error">{error}</div>
      ) : null}
      {notice ? (
        <div className="form-success dashboard-success">{notice}</div>
      ) : null}

      <section className="clients-list-panel">
        <div className="settings-tabs" role="tablist" aria-label="Facturación">
          {MAIN_VIEWS.map((view) => {
            const Icon = view.icon;
            return (
              <button
                aria-selected={activeView === view.key}
                className={`settings-tab ${
                  activeView === view.key ? 'is-active' : ''
                }`}
                key={view.key}
                onClick={() => setActiveView(view.key)}
                role="tab"
                type="button"
              >
                <Icon size={16} />
                {view.label}
              </button>
            );
          })}
        </div>

        {activeView === 'center' ? (
          <section className="dashboard-section-block invoice-quotation-workspace">
            <div className="section-heading">
              <div>
                <p>Operación financiera</p>
                <h2>Expedientes de facturación</h2>
                <span className="section-heading__description">
                  Selecciona una cotización para abrir su centro de trabajo.
                </span>
              </div>
              <div className="toolbar-actions">
                <mark
                  className={`status-pill ${
                    facturamaStatus?.connected ? 'is-success' : 'is-danger'
                  }`}
                >
                  Servicio de timbrado {facturamaStatus?.connected ? 'conectado' : 'sin conexión'}
                </mark>
                <button
                  className="table-button"
                  disabled={isLoading}
                  onClick={() => {
                    loadBillingData();
                    refreshFacturamaStatus();
                  }}
                  type="button"
                >
                  <RefreshCw size={16} />
                  Actualizar
                </button>
              </div>
            </div>

            <div className="invoice-workspace-metrics">
              <article className="invoice-workspace-metric is-ready">
                <div>
                  <span>Listas para facturar</span>
                  <strong>{metrics.ready}</strong>
                </div>
              </article>
              <article className="invoice-workspace-metric is-draft">
                <div>
                  <span>En preparación</span>
                  <strong>{metrics.drafts}</strong>
                </div>
              </article>
              <article className="invoice-workspace-metric is-stamped">
                <div>
                  <span>Emitidas</span>
                  <strong>{metrics.issued}</strong>
                </div>
              </article>
              <article className="invoice-workspace-metric is-cancelled">
                <div>
                  <span>Revisión requerida</span>
                  <strong>{metrics.review}</strong>
                </div>
              </article>
            </div>

            <section className="invoice-quotation-list">
              <div className="invoice-section-heading">
                <div>
                  <p>Centro de trabajo</p>
                  <h2>Cotizaciones aprobadas y expedientes activos</h2>
                </div>
                <span>
                  {visibleRows.length} registro
                  {visibleRows.length === 1 ? '' : 's'}
                </span>
              </div>

              <div className="toolbar-actions invoice-workspace-filters">
                <label className="invoice-search">
                  <Search aria-hidden="true" size={17} />
                  <input
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Buscar por cotización, factura, cliente, RFC, OT o UUID..."
                    value={search}
                  />
                </label>

                <label className="invoice-status-filter">
                  <span className="invoice-status-filter__label">
                    Filtrar por estado
                  </span>

                  <select
                    className="invoice-status-filter__select"
                    onChange={(event) => setStatusFilter(event.target.value)}
                    value={statusFilter}
                  >
                    <option value="all">Todos los estados</option>

                    {Array.from(
                      new Set(workspaceRows.map((row) => row.status.label))
                    ).map((label) => (
                      <option
                        key={label}
                        value={label}
                      >
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="invoice-workspace-table-wrapper">
                <div className="invoice-workspace-table">
                  <div
                    aria-hidden="true"
                    className="invoice-workspace-table__header"
                  >
                    <span>Estado</span>
                    <span>Documento</span>
                    <span>Cliente</span>
                    <span>Orden</span>
                    <span>Importe</span>
                  </div>

                  <div className="invoice-workspace-table__body">
                    {isLoading ? (
                      <p className="empty-state">
                        Cargando centro de facturación...
                      </p>
                    ) : null}

                    {!isLoading && !visibleRows.length ? (
                      <p className="empty-state">
                        No hay expedientes que coincidan con los filtros.
                      </p>
                    ) : null}

                    {!isLoading
                      ? visibleRows.map((row) => {
                          const document =
                            row.invoice?.folio ||
                            row.quotation?.folio ||
                            'Sin folio';
                          const clientName =
                            row.client?.commercial_name ||
                            row.client?.legal_name ||
                            `Cliente #${
                              row.quotation?.client_id ||
                              row.invoice?.client_id ||
                              '-'
                            }`;

                          return (
                            <article
                              className={`invoice-workspace-row ${row.status.className}`}
                              key={row.key}
                              onClick={(event) =>
                                openWorkspace(row, event.currentTarget)
                              }
                              onKeyDown={(event) => {
                                if (
                                  event.key !== 'Enter' &&
                                  event.key !== ' '
                                ) {
                                  return;
                                }

                                event.preventDefault();
                                openWorkspace(row, event.currentTarget);
                              }}
                              role="button"
                              tabIndex={0}
                            >
                              <div
                                className="invoice-workspace-row__status"
                                data-label="Estado"
                              >
                                <span className="invoice-billing-status">
                                  <i aria-hidden="true" />
                                  {row.status.label}
                                </span>
                              </div>

                              <div
                                className="invoice-workspace-row__folio"
                                data-label="Documento"
                              >
                                <strong>{document}</strong>
                                {row.invoice?.cfdi_uuid ? (
                                  <span>{row.invoice.cfdi_uuid}</span>
                                ) : (
                                  <span>
                                    {row.invoice
                                      ? 'Expediente creado'
                                      : 'Cotización elegible'}
                                  </span>
                                )}
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
                                  {row.serviceOrder?.work_order_number || '-'}
                                </span>
                              </div>

                              <div
                                className="invoice-workspace-row__amount"
                                data-label="Importe"
                              >
                                <strong>{formatMoney(row.amount)}</strong>
                              </div>
                            </article>
                          );
                        })
                      : null}
                  </div>
                </div>
              </div>

              <footer className="invoice-workspace-table__footer">
                <span>
                  Cada fila abre el expediente completo de esa operación.
                </span>
                <strong>
                  La preparación, emisión, pagos y documentos vivirán dentro
                  del expediente.
                </strong>
              </footer>
            </section>
          </section>
        ) : null}

        {activeView === 'dashboard' ? (
          <section className="dashboard-section-block">
            <div className="section-heading">
              <div>
                <p>Resumen financiero</p>
                <h2>Panorama de facturación</h2>
              </div>
              <mark className="status-pill">
                {isLoading ? 'Actualizando' : 'Información actual'}
              </mark>
            </div>

            <div className="operations-band dashboard-executive-grid--compact">
              <article className="operations-band__metric">
                <span>Facturas pendientes</span>
                <strong>{dashboard?.facturas_pendientes ?? '-'}</strong>
              </article>
              <article className="operations-band__metric">
                <span>Facturas vencidas</span>
                <strong>{dashboard?.facturas_vencidas ?? '-'}</strong>
              </article>
              <article className="operations-band__metric">
                <span>Cobrado del mes</span>
                <strong>
                  {formatMoney(dashboard?.total_cobrado_mes ?? 0)}
                </strong>
              </article>
              <article className="operations-band__metric">
                <span>Por cobrar</span>
                <strong>
                  {formatMoney(dashboard?.saldo_pendiente_total ?? 0)}
                </strong>
              </article>
              <article className="operations-band__metric">
                <span>Facturado del mes</span>
                <strong>
                  {formatMoney(dashboard?.total_facturado_mes ?? 0)}
                </strong>
              </article>
              <article className="operations-band__metric">
                <span>Pagos de hoy</span>
                <strong>{formatMoney(dashboard?.pagos_hoy ?? 0)}</strong>
              </article>
            </div>
          </section>
        ) : null}

        {activeView === 'settings' && settings ? (
          <section className="module-workspace__panel">
            <div className="section-heading">
              <div>
                <p>Parámetros operativos</p>
                <h2>Configuración de facturación</h2>
              </div>
              <Settings2 size={22} />
            </div>

            <form
              className="client-form client-form--modal"
              onSubmit={handleSaveSettings}
            >
              <label>
                <span>Serie interna default</span>
                <input
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      default_series: event.target.value,
                    }))
                  }
                  value={settings.default_series || ''}
                />
                <small>Solo identifica registros internos; la emisión fiscal usa la serie MYCF.</small>
              </label>
              <label>
                <span>Siguiente folio</span>
                <input
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      next_sequence: Number(event.target.value || 1),
                    }))
                  }
                  value={settings.next_sequence || 1}
                />
              </label>
              <label>
                <span>IVA default</span>
                <input
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      default_tax_rate: Number(event.target.value || 16),
                    }))
                  }
                  value={settings.default_tax_rate || 16}
                />
              </label>
              <label>
                <span>Moneda default</span>
                <input
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      default_currency: event.target.value,
                    }))
                  }
                  value={settings.default_currency || 'MXN'}
                />
              </label>
              <label>
                <span>Días de crédito</span>
                <input
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      default_credit_days: Number(event.target.value || 0),
                    }))
                  }
                  value={settings.default_credit_days || 0}
                />
              </label>
              <label>
                <span>Razón social MYC</span>
                <input
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      emitter_data: {
                        ...(current.emitter_data || {}),
                        legal_name: event.target.value,
                      },
                    }))
                  }
                  value={settings.emitter_data?.legal_name || ''}
                />
              </label>
              <label>
                <span>RFC MYC</span>
                <input
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      emitter_data: {
                        ...(current.emitter_data || {}),
                        rfc: event.target.value,
                      },
                    }))
                  }
                  value={settings.emitter_data?.rfc || ''}
                />
              </label>
              <label>
                <span>Lugar de expedición</span>
                <input
                  inputMode="numeric"
                  maxLength={5}
                  onChange={(event) => setSettings((current) => ({ ...current, emitter_data: { ...(current.emitter_data || {}), expedition_place: event.target.value.replace(/\D/g, '').slice(0, 5) } }))}
                  placeholder="Código postal de expedición"
                  value={settings.emitter_data?.expedition_place || ''}
                />
              </label>
              <label>
                <span>Correos de cobranza</span>
                <textarea
                  onChange={(event) =>
                    setSettings((current) => ({
                      ...current,
                      billing_emails: {
                        items: event.target.value
                          .split(',')
                          .map((item) => item.trim())
                          .filter(Boolean),
                      },
                    }))
                  }
                  value={(settings.billing_emails?.items || []).join(', ')}
                />
              </label>
              <button
                className="primary-button"
                disabled={isSaving}
                type="submit"
              >
                {isSaving ? 'Guardando...' : 'Guardar configuración'}
              </button>
            </form>
          </section>
        ) : null}

        {activeView === 'settings' && !settings && !isLoading ? (
          <p className="empty-state">
            No fue posible cargar la configuración de facturación.
          </p>
        ) : null}
      </section>

      <InvoiceWorkbenchDialog
        catalogByCode={catalogByCode}
        client={selectedClient}
        draft={workspaceDraft}
        invoice={selectedInvoice}
        isSaving={isSaving}
        canIssue={Boolean(
          selectedInvoice &&
            ['draft', 'issue_failed'].includes(selectedInvoice.status) &&
            facturamaStatus?.connected
        )}
        issueBlockedReason={
          facturamaStatus?.connected
            ? ''
            : 'No es posible emitir porque el servicio de timbrado no está conectado.'
        }
        onClose={handleCloseWorkspace}
        onConceptChange={updateWorkspaceConcept}
        onDraftChange={updateWorkspaceDraft}
        onDownloadFiscalXml={handleDownloadFiscalXml}
        onDownloadInstitutionalPdf={handleDownloadInstitutionalPdf}
        onIssue={handleIssueInvoice}
        onSaveDraft={handleSaveWorkspaceDraft}
        open={workspaceOpen}
        originElement={workspaceOriginElement}
        quotation={selectedQuotation}
      />
    </section>
  );
}

export default BillingPage;
