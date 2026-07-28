import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  Activity,
  FileText,
  ReceiptText,
  X,
} from 'lucide-react';

import {
  createGenieSpringKeyframes,
  SIGNATURE_CLOSE_DURATION,
  SIGNATURE_ICON_FADE_DURATION,
} from '../signatures/signatureMorphAnimation.js';
import InvoiceDraftView from './InvoiceDraftView.jsx';
import InvoiceDetailView from './InvoiceDetailView.jsx';
import ActivityPanel from '../activity/ActivityPanel.jsx';

import './invoice-workbench.css';

const WORKSPACE_TABS = [
  {
    key: 'workbench',
    label: 'Mesa de trabajo',
    icon: FileText,
  },
  {
    key: 'invoice',
    label: 'Factura',
    icon: ReceiptText,
  },
  {
    key: 'activity',
    label: 'Actividad',
    icon: Activity,
  },
];

const INVOICE_STATUS_LABELS = {
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

function formatCurrency(value, currency = 'MXN') {
  const amount = Number(value || 0);

  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

function WorkspaceEmptyState({ title, description }) {
  return (
    <div className="invoice-workspace-empty">
      <FileText aria-hidden="true" size={30} />
      <strong>{title}</strong>
      <span>{description}</span>
    </div>
  );
}

function InvoiceWorkspaceSummary({ invoice, quotation, client }) {
  const status = invoice?.status || 'ready';
  const statusLabel =
    INVOICE_STATUS_LABELS[status] ||
    (invoice ? status : 'Lista para facturar');

  return (
    <div className="invoice-case-summary">
      <article>
        <span>Documento de origen</span>
        <strong>{quotation?.folio || 'Sin folio'}</strong>
      </article>

      <article>
        <span>Cliente</span>
        <strong>
          {client?.commercial_name ||
            client?.legal_name ||
            'Cliente sin nombre'}
        </strong>
      </article>

      <article>
        <span>Factura</span>
        <strong>
          {invoice
            ? `${invoice.series || ''}-${invoice.folio || ''}`.replace(
                /^-|-$|^$/,
                'Sin folio'
              )
            : 'Pendiente'}
        </strong>
      </article>

      <article>
        <span>Estado</span>
        <strong>{statusLabel}</strong>
      </article>

      <article>
        <span>Total</span>
        <strong>
          {formatCurrency(
            invoice?.total ?? quotation?.total ?? 0,
            invoice?.currency || quotation?.currency || 'MXN'
          )}
        </strong>
      </article>

      <article>
        <span>Saldo</span>
        <strong>
          {formatCurrency(
            invoice?.balance_due ?? invoice?.total ?? quotation?.total ?? 0,
            invoice?.currency || quotation?.currency || 'MXN'
          )}
        </strong>
      </article>
    </div>
  );
}

export default function InvoiceWorkbenchDialog({
  open,
  quotation,
  invoice = null,
  client,
  draft,
  catalogByCode,
  isSaving = false,
  canIssue = false,
  issueBlockedReason = '',
  originElement = null,
  onConceptChange,
  onDraftChange,
  onSaveDraft,
  onIssue,
  onGoToInvoice,
  onDownloadInstitutionalPdf,
  onDownloadFiscalXml,
  onClose,
}) {
  const [isClosing, setIsClosing] = useState(false);
  const [activeWorkspaceTab, setActiveWorkspaceTab] =
    useState('workbench');

  const closeTimerRef = useRef(null);
  const closeAnimationRef = useRef(null);
  const closeMetricsRef = useRef(null);
  const modalRef = useRef(null);

  const invoiceStatus = invoice?.status || null;
  const isIssued = useMemo(
    () =>
      [
        'issued',
        'partially_paid',
        'paid',
        'overdue',
        'cancelled',
      ].includes(invoiceStatus),
    [invoiceStatus]
  );

  const title =
    quotation?.folio ||
    invoice?.folio ||
    'Expediente sin folio';

  const headerLabel = invoice
    ? 'Expediente de facturación'
    : 'Nuevo expediente de facturación';

  useEffect(() => {
    if (!open || isClosing) return undefined;

    modalRef.current?.focus();

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        beginClose();
      }
    }

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isClosing, open]);

  useEffect(() => {
    if (!isClosing || !modalRef.current) return undefined;

    const animation = modalRef.current.animate(
      createGenieSpringKeyframes(closeMetricsRef.current),
      {
        duration: SIGNATURE_CLOSE_DURATION,
        easing: 'linear',
        fill: 'forwards',
      }
    );

    closeAnimationRef.current = animation;
    animation.finished.catch(() => {});

    return () => {
      animation.cancel();

      if (closeAnimationRef.current === animation) {
        closeAnimationRef.current = null;
      }
    };
  }, [isClosing]);

  useEffect(
    () => () => {
      window.clearTimeout(closeTimerRef.current);
      closeAnimationRef.current?.cancel();
    },
    []
  );

  useEffect(() => {
    if (!open) return;

    setIsClosing(false);

    if (!invoice) {
      setActiveWorkspaceTab('workbench');
    }
  }, [invoice, open]);

  if (!open || (!quotation && !invoice)) {
    return null;
  }

  function beginClose() {
    if (isClosing || isSaving) return;

    const modalRect = modalRef.current?.getBoundingClientRect();
    const originRect = originElement?.getBoundingClientRect?.();

    closeMetricsRef.current = {
      closeX:
        originRect && modalRect
          ? originRect.left +
            originRect.width / 2 -
            (modalRect.left + modalRect.width / 2)
          : 0,
      closeY:
        originRect && modalRect
          ? originRect.top +
            originRect.height / 2 -
            (modalRect.top + modalRect.height / 2)
          : 14,
      finalScaleX: 1,
      finalScaleY: 1,
    };

    setIsClosing(true);

    closeTimerRef.current = window.setTimeout(() => {
      setIsClosing(false);
      onClose?.();
      window.setTimeout(() => originElement?.focus?.(), 0);
    }, SIGNATURE_CLOSE_DURATION + SIGNATURE_ICON_FADE_DURATION);
  }

  function renderActiveWorkspace() {
    if (activeWorkspaceTab === 'workbench') {
      return (
        <InvoiceDraftView
          canIssue={false}
          issueBlockedReason={issueBlockedReason}
          catalogByCode={catalogByCode}
          client={client}
          draft={draft}
          invoice={invoice}
          isSaving={isSaving}
          onConceptChange={onConceptChange}
          onDraftChange={onDraftChange}
          onGoToInvoice={() => {
            setActiveWorkspaceTab('invoice');
            onGoToInvoice?.();
          }}
          onSaveDraft={onSaveDraft}
          quotation={quotation}
        />
      );
    }

    if (activeWorkspaceTab === 'invoice') {
      return (
        <InvoiceDetailView
          canEmit={canIssue}
          client={client}
          invoice={invoice}
          isSaving={isSaving}
          issueBlockedReason={issueBlockedReason}
          onIssue={onIssue}
          onDownloadInstitutionalPdf={onDownloadInstitutionalPdf}
          onDownloadFiscalXml={onDownloadFiscalXml}
        />
      );
    }

    if (activeWorkspaceTab === 'activity') {
      return (
        <ActivityPanel
          entityType="invoice"
          entityId={invoice?.id}
        />
      );
    }
    return null;
  }

  return createPortal(
    <div
      className={
        isClosing
          ? 'invoice-draft-modal-layer is-closing'
          : 'invoice-draft-modal-layer'
      }
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          beginClose();
        }
      }}
    >
      <section
        aria-labelledby="invoice-draft-modal-title"
        aria-modal="true"
        className={
          isClosing
            ? 'invoice-draft-modal invoice-draft-modal--workspace closing'
            : 'invoice-draft-modal invoice-draft-modal--workspace'
        }
        ref={modalRef}
        role="dialog"
        tabIndex={-1}
      >
        <header className="invoice-draft-modal__header">
          <div>
            <p>{headerLabel}</p>
            <h2 id="invoice-draft-modal-title">{title}</h2>
          </div>

          <button
            aria-label="Cerrar expediente de facturación"
            className="invoice-draft-modal__close"
            disabled={isClosing || isSaving}
            onClick={beginClose}
            type="button"
          >
            <X size={20} />
          </button>
        </header>

        <InvoiceWorkspaceSummary
          client={client}
          invoice={invoice}
          quotation={quotation}
        />

        <nav
          aria-label="Secciones del expediente de facturación"
          className="invoice-case-tabs"
          role="tablist"
        >
          {WORKSPACE_TABS.map((tab) => {
            const Icon = tab.icon;
            const disabled = tab.key !== 'workbench' && !invoice;

            return (
              <button
                aria-selected={activeWorkspaceTab === tab.key}
                className={
                  activeWorkspaceTab === tab.key
                    ? 'invoice-case-tab is-active'
                    : 'invoice-case-tab'
                }
                disabled={disabled}
                key={tab.key}
                onClick={() => setActiveWorkspaceTab(tab.key)}
                role="tab"
                type="button"
              >
                <Icon aria-hidden="true" size={17} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="invoice-draft-modal__content invoice-draft-modal__content--workspace">
          {renderActiveWorkspace()}
        </div>
      </section>
    </div>,
    document.body
  );
}
