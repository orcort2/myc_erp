import React, { useEffect, useMemo, useState } from 'react';

import {
  changeInvoiceStatus,
  createCreditNote,
  createInvoice,
  getInvoiceDashboard,
  getInvoicePdfUrl,
  getInvoicePaymentReceiptPdfUrl,
  getInvoiceSettings,
  listAccountsReceivable,
  listCertificates,
  listClients,
  listInvoicePayments,
  listInvoices,
  listReleasedUninvoiced,
  listServiceOrders,
  registerInvoicePayment,
  updateInvoiceSettings,
} from '../services/api.js';
import { formatDate, formatMoney } from '../utils/formatters.js';

const BILLING_TABS = [
  { key: 'dashboard', label: 'Dashboard' },
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

function buildSuggestedItems(orderId, certificates = []) {
  return certificates
    .filter((item) => String(item.service_order_id) === String(orderId) && item.status === 'released_to_client')
    .map((item) => ({
      certificate_id: item.id,
      equipment_id: item.equipment_id,
      description: `Servicio asociado a certificado ${item.expected_folio || item.folio}`,
      quantity: 1,
      unit: 'Servicio',
      sat_unit: 'E48',
      sat_key: '81141504',
      unit_price: '0.00',
      discount_total: '0.00',
      tax_rate: '16.00',
      notes: item.notes || '',
      service_type: item.certificate_type || 'calibracion',
      source_type: 'certificate',
    }));
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
  const [certificates, setCertificates] = useState([]);
  const [settings, setSettings] = useState(null);
  const [invoiceForm, setInvoiceForm] = useState(emptyInvoiceForm());
  const [paymentForm, setPaymentForm] = useState({ invoiceId: '', paidOn: new Date().toISOString().slice(0, 10), amount: '', bankName: '', reference: '', paymentMethod: 'PUE', paymentForm: 'Transferencia', notes: '' });
  const [creditNoteForm, setCreditNoteForm] = useState({ invoiceId: '', issuedOn: new Date().toISOString().slice(0, 10), reason: '', subtotal: '0.00', taxTotal: '0.00', total: '0.00', status: 'draft', observations: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const clientsById = useMemo(() => new Map(clients.map((item) => [item.id, item])), [clients]);
  const ordersById = useMemo(() => new Map(serviceOrders.map((item) => [item.id, item])), [serviceOrders]);

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
        certificatesResult,
        settingsResult,
      ] = await Promise.all([
        getInvoiceDashboard(),
        listInvoices(),
        listInvoicePayments(),
        listAccountsReceivable(),
        listReleasedUninvoiced(),
        listClients(),
        listServiceOrders(),
        listCertificates(),
        getInvoiceSettings(),
      ]);
      setDashboard(dashboardResult);
      setInvoices(invoicesResult);
      setPayments(paymentsResult);
      setAccounts(accountsResult);
      setReleasedUninvoiced(releasedResult);
      setClients(clientsResult);
      setServiceOrders(ordersResult);
      setCertificates(certificatesResult);
      setSettings(settingsResult);

      const storedOrderId = window.localStorage.getItem('myc_billing_order_id');
      if (storedOrderId) {
        updateInvoiceForm('serviceOrderId', storedOrderId);
        const order = ordersResult.find((item) => String(item.id) === String(storedOrderId));
        if (order) {
          setInvoiceForm((current) => ({
            ...current,
            serviceOrderId: storedOrderId,
            clientId: String(order.client_id),
            fiscalClientId: String(order.client_id),
            items: buildSuggestedItems(storedOrderId, certificatesResult),
          }));
        }
        window.localStorage.removeItem('myc_billing_order_id');
        setActiveTab('invoices');
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  function updateInvoiceForm(field, value) {
    setInvoiceForm((current) => {
      const next = { ...current, [field]: value };
      if (field === 'serviceOrderId') {
        const order = ordersById.get(Number(value));
        if (order) {
          next.clientId = String(order.client_id);
          next.fiscalClientId = String(order.client_id);
          next.items = buildSuggestedItems(value, certificates);
        }
      }
      return next;
    });
  }

  async function handleCreateInvoice(event) {
    event.preventDefault();
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      await createInvoice({
        client_id: Number(invoiceForm.clientId),
        fiscal_client_id: invoiceForm.fiscalClientId ? Number(invoiceForm.fiscalClientId) : null,
        service_order_id: invoiceForm.serviceOrderId ? Number(invoiceForm.serviceOrderId) : null,
        quotation_id: invoiceForm.quotationId ? Number(invoiceForm.quotationId) : null,
        issued_on: invoiceForm.issuedOn || null,
        due_on: invoiceForm.dueOn || null,
        status: 'draft',
        payment_method: invoiceForm.paymentMethod || null,
        payment_form: invoiceForm.paymentForm || null,
        usage_cfdi: invoiceForm.usageCfdi || null,
        currency: invoiceForm.currency || 'MXN',
        credit_days: Number(invoiceForm.creditDays || 0),
        observations: invoiceForm.observations || null,
        internal_comments: invoiceForm.internalComments || null,
        items: invoiceForm.items.map((item) => ({
          ...item,
          quantity: Number(item.quantity || 1),
          unit_price: Number(item.unit_price || 0),
          discount_total: Number(item.discount_total || 0),
          tax_rate: Number(item.tax_rate || 16),
        })),
      });
      setNotice('Factura creada');
      setInvoiceForm(emptyInvoiceForm());
      await loadBillingData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
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
                    setActiveTab('invoices');
                    updateInvoiceForm('serviceOrderId', String(item.service_order_id));
                  }} type="button">Crear factura</button>
                </article>
              ))}
            </div>
          </section>
        ) : null}

        {activeTab === 'invoices' ? (
          <>
            <section className="quotation-section">
              <div className="quotation-section__title">
                <p>Facturas</p>
                <h3>{isLoading ? 'Cargando...' : invoices.length}</h3>
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
                    {invoices.map((invoice) => (
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

            <section className="quotation-section">
              <div className="quotation-section__title">
                <p>Nueva factura</p>
                <h3>Prellenado desde certificados liberados</h3>
              </div>
              <form className="client-form client-form--modal" onSubmit={handleCreateInvoice}>
                <label>
                  Orden de servicio
                  <select value={invoiceForm.serviceOrderId} onChange={(event) => updateInvoiceForm('serviceOrderId', event.target.value)}>
                    <option value="">Selecciona</option>
                    {serviceOrders.map((order) => (
                      <option key={order.id} value={order.id}>OT {order.work_order_number} · {clientsById.get(order.client_id)?.commercial_name || clientsById.get(order.client_id)?.legal_name || '-'}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Cliente
                  <select value={invoiceForm.clientId} onChange={(event) => updateInvoiceForm('clientId', event.target.value)}>
                    <option value="">Selecciona</option>
                    {clients.map((client) => (
                      <option key={client.id} value={client.id}>{client.commercial_name || client.legal_name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Cliente fiscal
                  <select value={invoiceForm.fiscalClientId} onChange={(event) => updateInvoiceForm('fiscalClientId', event.target.value)}>
                    <option value="">Selecciona</option>
                    {clients.map((client) => (
                      <option key={client.id} value={client.id}>{client.legal_name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Emisión
                  <input type="date" value={invoiceForm.issuedOn} onChange={(event) => updateInvoiceForm('issuedOn', event.target.value)} />
                </label>
                <label>
                  Vencimiento
                  <input type="date" value={invoiceForm.dueOn} onChange={(event) => updateInvoiceForm('dueOn', event.target.value)} />
                </label>
                <label>
                  Método
                  <input type="text" value={invoiceForm.paymentMethod} onChange={(event) => updateInvoiceForm('paymentMethod', event.target.value)} />
                </label>
                <label>
                  Forma
                  <input type="text" value={invoiceForm.paymentForm} onChange={(event) => updateInvoiceForm('paymentForm', event.target.value)} />
                </label>
                <label>
                  Uso CFDI futuro
                  <input type="text" value={invoiceForm.usageCfdi} onChange={(event) => updateInvoiceForm('usageCfdi', event.target.value)} />
                </label>
                <label>
                  Observaciones
                  <textarea value={invoiceForm.observations} onChange={(event) => updateInvoiceForm('observations', event.target.value)} />
                </label>
                <div className="quotation-section__title">
                  <p>Conceptos sugeridos</p>
                  <h3>{invoiceForm.items.length}</h3>
                </div>
                {invoiceForm.items.map((item, index) => (
                  <div className="quotation-commercial-grid service-order-info-grid" key={`${item.certificate_id || 'free'}-${index}`}>
                    <article><span>Descripción</span><strong>{item.description}</strong></article>
                    <article><span>Certificado</span><strong>{certificates.find((certificate) => certificate.id === item.certificate_id)?.expected_folio || '-'}</strong></article>
                    <article>
                      <span>Precio</span>
                      <input value={item.unit_price} onChange={(event) => setInvoiceForm((current) => ({
                        ...current,
                        items: current.items.map((row, rowIndex) => rowIndex === index ? { ...row, unit_price: event.target.value } : row),
                      }))} />
                    </article>
                  </div>
                ))}
                <button className="primary-button" disabled={isSaving} type="submit">{isSaving ? 'Guardando...' : 'Crear factura'}</button>
              </form>
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
