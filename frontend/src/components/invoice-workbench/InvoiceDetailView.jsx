import {
  AlertTriangle,
  CheckCircle2,
  FileCode2,
  FileText,
  ReceiptText,
  ShieldCheck,
} from 'lucide-react';

const STATUS_LABELS = {
  draft: 'Borrador',
  pending: 'Pendiente',
  issuing: 'Emitiendo',
  issued: 'Emitida',
  issue_failed: 'Error de emisión',
  partially_paid: 'Pago parcial',
  paid: 'Pagada',
  overdue: 'Vencida',
  cancelled: 'Cancelada',
  credit_note: 'Nota de crédito',
};

const ISSUED_STATUSES = new Set([
  'issued',
  'partially_paid',
  'paid',
  'overdue',
  'cancelled',
]);

function formatMoney(value, currency = 'MXN') {
  const amount = Number(value || 0);

  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: currency || 'MXN',
    minimumFractionDigits: 2,
  }).format(amount);
}

function formatDate(value, includeTime = false) {
  if (!value) return 'Pendiente';

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat('es-MX', {
    dateStyle: 'medium',
    ...(includeTime ? { timeStyle: 'short' } : {}),
  }).format(parsed);
}

function getInvoiceLabel(invoice) {
  const series = String(invoice?.series || '').trim();
  const folio = String(invoice?.folio || '').trim();

  if (series && folio) return `${series}-${folio}`;
  return series || folio || 'Factura sin folio';
}

function DetailField({ label, value, className = '' }) {
  return (
    <article className={className}>
      <span>{label}</span>
      <strong>{value ?? '—'}</strong>
    </article>
  );
}

function EmptyInvoiceState() {
  return (
    <div className="invoice-workspace-empty">
      <ReceiptText aria-hidden="true" size={32} />
      <strong>Guarda primero el borrador</strong>
      <span>
        La información fiscal y las acciones de emisión se habilitarán
        cuando exista una factura interna vinculada al expediente.
      </span>
    </div>
  );
}

export default function InvoiceDetailView({
  invoice,
  client = null,
  canEmit = false,
  isSaving = false,
  issueBlockedReason = '',
  onIssue,
  onDownloadInstitutionalPdf,
  onDownloadFiscalXml,
}) {
  if (!invoice) {
    return <EmptyInvoiceState />;
  }

  const status = invoice.status || 'draft';
  const isIssued = ISSUED_STATUSES.has(status);
  const canShowIssue = ['draft', 'issue_failed'].includes(status);
  const hasXml = Boolean(invoice.facturama_xml_path);
  const currency = invoice.currency || 'MXN';
  const receiverName =
    client?.commercial_name ||
    client?.legal_name ||
    invoice.fiscal_snapshot?.receiver_legal_name ||
    'Cliente sin nombre';
  const receiverRfc =
    invoice.fiscal_snapshot?.receiver_rfc ||
    client?.rfc ||
    'Sin RFC';

  return (
    <section className="invoice-detail-view">
      <header className="invoice-case-panel__heading">
        <div>
          <p>Comprobante fiscal</p>
          <h3>{getInvoiceLabel(invoice)}</h3>
        </div>

        <div className="invoice-case-panel__heading-actions">
          <div className="invoice-detail-documents invoice-detail-documents--header">
            <button
              className="table-button"
              disabled={isSaving || !onDownloadInstitutionalPdf}
              onClick={() => onDownloadInstitutionalPdf?.(invoice)}
              type="button"
            >
              <FileText size={16} />
              Descargar PDF
            </button>

            <button
              className="table-button"
              disabled={isSaving || !hasXml || !onDownloadFiscalXml}
              onClick={() => onDownloadFiscalXml?.(invoice)}
              title={hasXml ? 'Descargar XML fiscal' : 'El XML fiscal aún no está disponible.'}
              type="button"
            >
              <FileCode2 size={16} />
              Descargar XML
            </button>
          </div>

          <span
            className={`invoice-case-status invoice-case-status--${status}`}
          >
            {STATUS_LABELS[status] || status}
          </span>
        </div>
      </header>

      {invoice.review_required ? (
        <div className="invoice-detail-alert invoice-detail-alert--warning">
          <AlertTriangle aria-hidden="true" size={20} />
          <div>
            <strong>Revisión requerida</strong>
            <span>
              {invoice.draft_reason ||
                'El origen del borrador cambió. Revisa la Mesa de trabajo antes de emitir.'}
            </span>
          </div>
        </div>
      ) : null}

      {status === 'issue_failed' ? (
        <div className="invoice-detail-alert invoice-detail-alert--error">
          <AlertTriangle aria-hidden="true" size={20} />
          <div>
            <strong>No fue posible emitir el CFDI</strong>
            <span>
              Revisa la información fiscal y vuelve a intentar. La
              factura permanece disponible como borrador.
            </span>
          </div>
        </div>
      ) : null}

      {isIssued ? (
        <div className="invoice-case-success">
          <CheckCircle2 aria-hidden="true" size={28} />
          <div>
            <strong>CFDI emitido correctamente</strong>
            <span>
              El comprobante cuenta con UUID y sus documentos fiscales.
            </span>
          </div>
        </div>
      ) : null}

      <section className="invoice-detail-section">
        <div className="invoice-detail-section__heading">
          <div>
            <p>Identificación</p>
            <h4>Datos del comprobante</h4>
          </div>
          <ShieldCheck aria-hidden="true" size={20} />
        </div>

        <div className="invoice-case-detail-grid">
          <DetailField
            className="invoice-detail-field--wide"
            label="UUID fiscal"
            value={invoice.cfdi_uuid || 'Pendiente de timbrado'}
          />
          <DetailField
            label="Fecha de emisión"
            value={formatDate(invoice.issued_on)}
          />
          <DetailField
            label="Fecha de timbrado"
            value={formatDate(invoice.stamped_at, true)}
          />
          <DetailField
            label="UUID interno"
            value={invoice.internal_uuid || '—'}
          />
        </div>
      </section>

      <section className="invoice-detail-section">
        <div className="invoice-detail-section__heading">
          <div>
            <p>Receptor y condiciones</p>
            <h4>Información fiscal</h4>
          </div>
          <FileText aria-hidden="true" size={20} />
        </div>

        <div className="invoice-case-detail-grid">
          <DetailField
            className="invoice-detail-field--wide"
            label="Receptor"
            value={receiverName}
          />
          <DetailField label="RFC" value={receiverRfc} />
          <DetailField
            label="Uso CFDI"
            value={invoice.usage_cfdi || 'Sin definir'}
          />
          <DetailField
            label="Método de pago"
            value={invoice.payment_method || 'Sin definir'}
          />
          <DetailField
            label="Forma de pago"
            value={invoice.payment_form || 'Sin definir'}
          />
          <DetailField label="Moneda" value={currency} />
          <DetailField
            label="Días de crédito"
            value={`${Number(invoice.credit_days || 0)} días`}
          />
          <DetailField
            label="Vencimiento"
            value={formatDate(invoice.due_on)}
          />
        </div>
      </section>

      <section className="invoice-detail-section">
        <div className="invoice-detail-section__heading">
          <div>
            <p>Importes</p>
            <h4>Resumen financiero</h4>
          </div>
          <ReceiptText aria-hidden="true" size={20} />
        </div>

        <div className="invoice-detail-totals">
          <DetailField
            label="Subtotal"
            value={formatMoney(invoice.subtotal, currency)}
          />
          <DetailField
            label="Descuento"
            value={formatMoney(invoice.discount_total, currency)}
          />
          <DetailField
            label="Impuestos"
            value={formatMoney(invoice.tax_total, currency)}
          />
          <DetailField
            label="Retenciones"
            value={formatMoney(invoice.withholding_total, currency)}
          />
          <DetailField
            className="invoice-detail-total--primary"
            label="Total"
            value={formatMoney(invoice.total, currency)}
          />
          <DetailField
            label="Pagado"
            value={formatMoney(invoice.amount_paid, currency)}
          />
          <DetailField
            className="invoice-detail-total--balance"
            label="Saldo"
            value={formatMoney(invoice.balance_due, currency)}
          />
        </div>
      </section>

      <section className="invoice-detail-section">
        <div className="invoice-detail-section__heading">
          <div>
            <p>Conceptos</p>
            <h4>
              {invoice.items?.length || 0} concepto
              {invoice.items?.length === 1 ? '' : 's'}
            </h4>
          </div>
          <FileCode2 aria-hidden="true" size={20} />
        </div>

        {!invoice.items?.length ? (
          <p className="empty-state">
            Esta factura no tiene conceptos registrados.
          </p>
        ) : (
          <div className="invoice-detail-items">
            <div
              aria-hidden="true"
              className="invoice-detail-items__header"
            >
              <span>Descripción</span>
              <span>Clave SAT</span>
              <span>Unidad</span>
              <span>Cantidad</span>
              <span>Precio</span>
              <span>Total</span>
            </div>

            {invoice.items.map((item) => (
              <article className="invoice-detail-item" key={item.id}>
                <div>
                  <strong>{item.description}</strong>
                  {item.notes ? <span>{item.notes}</span> : null}
                </div>
                <span>{item.sat_key || '—'}</span>
                <span>{item.sat_unit || item.unit || '—'}</span>
                <span>{Number(item.quantity || 0)}</span>
                <span>{formatMoney(item.unit_price, currency)}</span>
                <strong>{formatMoney(item.line_total, currency)}</strong>
              </article>
            ))}
          </div>
        )}
      </section>

      {canShowIssue ? (
        <section className="invoice-case-actions">
          <div>
            <strong>Emitir CFDI</strong>
            <span>
              El servicio de timbrado validará y sellará el comprobante.
            </span>
          </div>

          <button
            className="primary-button"
            disabled={
              isSaving ||
              invoice.review_required ||
              !canEmit ||
              !onIssue
            }
            onClick={() => onIssue?.(invoice)}
            type="button"
          >
            {isSaving
              ? 'Generando comprobante…'
              : 'Emitir CFDI de prueba'}
          </button>

          {invoice.review_required ||
          !canEmit ||
          issueBlockedReason ? (
            <p className="form-error">
              {invoice.review_required
                ? 'Debes confirmar la revisión del borrador antes de emitir.'
                : issueBlockedReason ||
                  'El servicio de timbrado no está disponible.'}
            </p>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}
