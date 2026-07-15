import {
  CheckCircle2,
  Database,
  FilePenLine,
  ReceiptText,
} from 'lucide-react';

export default function InvoiceWorkbenchSidebar({
  quotation,
  invoice,
  isSaving = false,
  onSaveDraft,
  onIssue,
}) {
  const documentLabel = invoice
    ? `${invoice.series || ''}-${invoice.folio || ''}`.replace(/^-|-$/g, '')
    : quotation?.folio || 'Sin folio';

  const requiresReview = Boolean(invoice?.review_required);

  return (
    <aside className="invoice-workbench-sidebar">
      <div className="invoice-workbench-sidebar__brand">
        <span>MYC SYSTEM</span>
        <strong>ERP</strong>
      </div>

      <div className="invoice-workbench-sidebar__module">
        <ReceiptText size={18} />

        <div>
          <span>Módulo</span>
          <strong>Facturación</strong>
        </div>
      </div>

      <nav
        aria-label="Estado del documento"
        className="invoice-workbench-sidebar__nav"
      >
        <div className="is-active">
          <FilePenLine size={17} />
          <span>
            {requiresReview ? 'Revisión requerida' : 'Borrador'}
          </span>
        </div>

        <div>
          <CheckCircle2 size={17} />
          <span>Pendiente de emisión</span>
        </div>
      </nav>

      <div className="invoice-workbench-sidebar__source">
        <Database size={16} />

        <div>
          <strong>Origen del documento</strong>
          <span>
            {invoice ? 'Borrador guardado' : 'Cotización aprobada'}
          </span>
        </div>
      </div>

      <div className="invoice-workbench-sidebar__selection">
        <span>
          {invoice ? 'Factura seleccionada' : 'Cotización seleccionada'}
        </span>

        <strong>{documentLabel}</strong>
      </div>

      <section className="invoice-sidebar-actions">
        <button
          className="primary-button"
          disabled={isSaving || !onSaveDraft}
          onClick={onSaveDraft}
          type="button"
        >
          {isSaving ? 'Guardando...' : 'Guardar borrador'}
        </button>

        <button
          className="table-button"
          disabled={isSaving || requiresReview || !onIssue}
          onClick={onIssue}
          type="button"
        >
          Emitir
        </button>
      </section>
    </aside>
  );
}