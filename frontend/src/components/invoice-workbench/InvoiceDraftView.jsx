import {
  Building2,
  FileText,
  PackageOpen,
  SlidersHorizontal,
} from 'lucide-react';
import { useState } from 'react';

import InvoiceAdvancedFiscalSection from './InvoiceAdvancedFiscalSection.jsx';
import InvoiceClientSection from './InvoiceClientSection.jsx';
import InvoiceConceptsSection from './InvoiceConceptsSection.jsx';
import InvoiceFiscalSection from './InvoiceFiscalSection.jsx';
import InvoiceSummaryPanel from './InvoiceSummaryPanel.jsx';
import InvoiceToolbar from './InvoiceToolbar.jsx';

const TABS = [
  {
    id: 'summary',
    label: 'Resumen',
    icon: FileText,
  },
  {
    id: 'receiver',
    label: 'Receptor y factura',
    icon: Building2,
  },
  {
    id: 'concepts',
    label: 'Conceptos',
    icon: PackageOpen,
  },
  {
    id: 'fiscal',
    label: 'Configuración fiscal',
    icon: SlidersHorizontal,
  },
];

export default function InvoiceDraftView({
  catalogByCode,
  client,
  draft,
  onConceptChange,
  onDraftChange,
  quotation,
  invoice = null,
  isSaving = false,
  onSaveDraft,
  onIssue,
  onGoToInvoice,
  canIssue = false,
  issueBlockedReason = '',
}) {
  const [activeTab, setActiveTab] = useState('summary');

  return (
    <section className="invoice-draft-view">
      <div className="invoice-draft-view__intro">
        <div>
          <p>Factura de ingreso</p>
          <h2>{quotation?.folio || 'Sin folio'}</h2>
          <span>
            Datos comerciales y fiscales del prospecto de factura.
          </span>
        </div>

        <div className="invoice-draft-view__status">
          <span>Estado de facturación</span>
          <strong>
            {invoice?.review_required
              ? 'Revisión requerida'
              : invoice
                ? 'Borrador guardado'
                : 'Prospecto en edición'}
          </strong>
        </div>
      </div>

      <nav
        aria-label="Secciones del precomprobante"
        className="invoice-draft-tabs"
      >
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;

          return (
            <button
              aria-current={isActive ? 'page' : undefined}
              className={isActive ? 'is-active' : ''}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="invoice-draft-tab-content">
        {activeTab === 'summary' ? (
          <div className="invoice-draft-summary-layout">
            <InvoiceSummaryPanel client={client} quotation={quotation} />
          </div>
        ) : null}

        {activeTab === 'receiver' ? (
          <div className="invoice-receiver-invoice-layout">
            <InvoiceClientSection
              catalogByCode={catalogByCode}
              client={client}
              draft={draft}
              onChange={onDraftChange}
            />

            <InvoiceFiscalSection
              catalogByCode={catalogByCode}
              draft={draft}
              invoice={invoice}
              onChange={onDraftChange}
            />
          </div>
        ) : null}

        {activeTab === 'concepts' ? (
          <InvoiceConceptsSection
            catalogByCode={catalogByCode}
            draft={draft}
            onChange={onConceptChange}
            quotation={quotation}
          />
        ) : null}

        {activeTab === 'fiscal' ? (
          <InvoiceAdvancedFiscalSection
            catalogByCode={catalogByCode}
            draft={draft}
            onConceptChange={onConceptChange}
            onDraftChange={onDraftChange}
            quotation={quotation}
          />
        ) : null}
      </div>

      <InvoiceToolbar
        canIssue={canIssue}
        issueBlockedReason={issueBlockedReason}
        isSaving={isSaving}
        onIssue={onIssue}
        onGoToInvoice={invoice ? onGoToInvoice : null}
        onSaveDraft={onSaveDraft}
      />
    </section>
  );
}
