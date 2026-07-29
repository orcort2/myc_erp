import React, { useMemo } from 'react';
import { Download, FileText, ReceiptText } from 'lucide-react';

import InvoiceWorkbenchDialog from '../invoice-workbench/InvoiceWorkbenchDialog.jsx';
import { canIssueInvoiceAfterPayment } from '../invoice-workbench/invoicePaymentForm.js';
import useInvoiceWorkbenchController from '../invoice-workbench/useInvoiceWorkbenchController.js';
import { formatDate, formatMoney } from '../../utils/formatters.js';
import {
  formatInvoiceInternalFolio,
  getEtsInvoiceContextView,
} from './etsInvoicePresentation.js';

const NEXT_PHASE_CARDS = [
  'Notas de crédito',
  'Historial y documentos',
];

export default function EtsBillingTab({
  serviceOrderId,
  user = null,
  onPaymentRegistered,
}) {
  const initialContext = useMemo(
    () => ({ service_order_id: serviceOrderId }),
    [serviceOrderId]
  );
  const {
    catalogByCode,
    closeWorkspace,
    contextInvoice,
    contextLoading,
    contextResolved,
    downloadFiscalXml,
    downloadInstitutionalPdf,
    downloadPaymentReceipt,
    error,
    facturamaStatus,
    isSaving,
    issueWorkspaceInvoice,
    notice,
    openWorkspaceByContext,
    saveWorkspaceDraft,
    registerWorkspacePayment,
    selectedClient,
    selectedInvoice,
    selectedQuotation,
    updateWorkspaceConcept,
    updateWorkspaceDraft,
    workspaceDraft,
    workspaceOpen,
    workspaceOriginElement,
  } = useInvoiceWorkbenchController({
    initialContext,
    loadOverview: false,
    openInitialContext: false,
    onPaymentRegistered,
  });
  const canManagePayments = Boolean(
    user?.permissions?.includes('*') ||
      user?.permissions?.includes('payments.*') ||
      user?.permissions?.includes('payments.manage')
  );

  const invoice = contextInvoice;
  const contextView = getEtsInvoiceContextView({
    contextResolved,
    invoice,
  });
  const presentation = contextView.presentation;
  const internalFolio = contextResolved
    ? formatInvoiceInternalFolio(invoice)
    : '';

  function openWorkbench(event) {
    openWorkspaceByContext(initialContext, event.currentTarget);
  }

  return (
    <section className="quotation-section ets-billing-tab">
      <div className="quotation-section__title">
        <div>
          <p>Facturación</p>
          <h3>Resumen financiero del servicio</h3>
        </div>
        {!contextLoading && presentation ? (
          <mark className={`invoice-billing-status is-${presentation.kind}`}>
            <i aria-hidden="true" />
            {presentation.statusLabel}
          </mark>
        ) : null}
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-success dashboard-success">{notice}</div> : null}

      <div className="ets-billing-tab__context">
        {contextLoading || contextView.phase === 'loading' ? (
          <div
            aria-busy="true"
            aria-live="polite"
            className="ets-billing-tab__loading"
            role="status"
          >
            <ReceiptText aria-hidden="true" size={28} />
            <strong>Consultando la factura asociada al ETS...</strong>
          </div>
        ) : (
          <>
            <article className={`ets-invoice-summary is-${presentation.kind}`}>
              <div className="ets-invoice-summary__heading">
                <span className="ets-invoice-summary__icon">
                  <ReceiptText aria-hidden="true" size={24} />
                </span>
                <div>
                  <span>Factura asociada</span>
                  <strong>
                    {invoice
                      ? internalFolio || 'Expediente sin folio'
                      : 'No existe una factura para este servicio.'}
                  </strong>
                </div>
              </div>

              {invoice ? (
                <dl className="ets-invoice-summary__details">
                  <div>
                    <dt>Estado</dt>
                    <dd>{presentation.statusLabel}</dd>
                  </div>
                  {internalFolio ? (
                    <div><dt>Folio interno</dt><dd>{internalFolio}</dd></div>
                  ) : null}
                  {invoice.cfdi_uuid ? (
                    <div className="is-wide"><dt>UUID</dt><dd>{invoice.cfdi_uuid}</dd></div>
                  ) : null}
                  {invoice.issued_on ? (
                    <div><dt>Fecha de emisión</dt><dd>{formatDate(invoice.issued_on)}</dd></div>
                  ) : null}
                  {invoice.total != null ? (
                    <div><dt>Importe total</dt><dd>{formatMoney(invoice.total, invoice.currency || 'MXN')}</dd></div>
                  ) : null}
                </dl>
              ) : null}

              <div className="ets-invoice-summary__actions">
                <button
                  className="primary-button"
                  disabled={isSaving}
                  onClick={openWorkbench}
                  type="button"
                >
                  <FileText aria-hidden="true" size={16} />
                  {presentation.primaryActionLabel}
                </button>
                {presentation.canDownload ? (
                  <>
                    <button
                      className="table-button"
                      disabled={isSaving}
                      onClick={() => downloadInstitutionalPdf(invoice)}
                      type="button"
                    >
                      <Download aria-hidden="true" size={16} />
                      Descargar PDF MYC
                    </button>
                    <button
                      className="table-button"
                      disabled={isSaving}
                      onClick={() => downloadFiscalXml(invoice)}
                      type="button"
                    >
                      <Download aria-hidden="true" size={16} />
                      Descargar XML
                    </button>
                  </>
                ) : null}
              </div>
            </article>

            <div className="ets-billing-next-phase" aria-label="Funciones de próximas fases">
              {NEXT_PHASE_CARDS.map((title) => (
                <article key={title}>
                  <strong>{title}</strong>
                  <span>Disponible en la siguiente fase.</span>
                </article>
              ))}
            </div>
          </>
        )}
      </div>

      <InvoiceWorkbenchDialog
        catalogByCode={catalogByCode}
        client={selectedClient}
        draft={workspaceDraft}
        invoice={selectedInvoice}
        isSaving={isSaving}
        canIssue={Boolean(
          canIssueInvoiceAfterPayment(selectedInvoice) &&
            facturamaStatus?.connected
        )}
        canManagePayments={canManagePayments}
        issueBlockedReason={
          facturamaStatus?.connected
            ? ''
            : 'No es posible emitir porque el servicio de timbrado no está conectado.'
        }
        onClose={closeWorkspace}
        onConceptChange={updateWorkspaceConcept}
        onDraftChange={updateWorkspaceDraft}
        onDownloadFiscalXml={downloadFiscalXml}
        onDownloadInstitutionalPdf={downloadInstitutionalPdf}
        onDownloadPaymentReceipt={downloadPaymentReceipt}
        onIssue={issueWorkspaceInvoice}
        onRegisterPayment={registerWorkspacePayment}
        onSaveDraft={saveWorkspaceDraft}
        open={workspaceOpen}
        originElement={workspaceOriginElement}
        quotation={selectedQuotation}
      />
    </section>
  );
}
