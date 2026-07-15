import { X } from 'lucide-react';
import { useEffect, useRef } from 'react';

import InvoiceDraftView from './InvoiceDraftView.jsx';
import InvoiceWorkbenchSidebar from './InvoiceWorkbenchSidebar.jsx';

import './invoice-workbench.css';

export default function InvoiceWorkbenchModal({
  open,
  mode = 'create',
  quotation = null,
  invoice = null,
  draft = {},
  catalogByCode = new Map(),
  client = null,
  onConceptChange,
  onDraftChange,
  onClose,
  onSaveDraft,
  onIssue,
  isSaving = false,
  canIssue = false,
}) {
  const modalRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;

    modalRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose?.();
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () =>
      window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, open]);

  if (!open) return null;

  const title = quotation?.folio ||
    (invoice
      ? `${invoice.series || ''}-${invoice.folio || ''}`
          .replace(/^-|-$/g, '')
      : 'Nuevo prospecto');

  return (
    <div
      className="invoice-draft-modal-layer"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose?.();
        }
      }}
    >
      <section
        aria-labelledby="invoice-workbench-title"
        aria-modal="true"
        className="invoice-draft-modal"
        ref={modalRef}
        role="dialog"
        tabIndex={-1}
      >
        <header className="invoice-draft-modal__header">
          <div>
            <p>
              {mode === 'edit'
                ? 'Borrador de facturación'
                : 'Preparar factura'}
            </p>
            <h2 id="invoice-workbench-title">{title}</h2>
          </div>

          <button
            aria-label="Cerrar mesa de trabajo"
            className="invoice-draft-modal__close"
            disabled={isSaving}
            onClick={onClose}
            type="button"
          >
            <X size={20} />
          </button>
        </header>

        <div className="invoice-draft-modal__content">
          <div className="invoice-workbench-modal-layout">
            <main className="invoice-workbench-modal-main">
              <InvoiceDraftView
                catalogByCode={catalogByCode}
                client={client}
                draft={draft}
                onConceptChange={onConceptChange}
                onDraftChange={onDraftChange}
                quotation={quotation}
              />
            </main>

            <InvoiceWorkbenchSidebar
              invoice={invoice}
              isSaving={isSaving}
              onIssue={canIssue ? onIssue : undefined}
              onSaveDraft={onSaveDraft}
              quotation={quotation}
            />
          </div>
        </div>
      </section>
    </div>
  );
}