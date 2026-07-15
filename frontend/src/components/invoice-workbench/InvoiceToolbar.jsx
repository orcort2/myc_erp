export default function InvoiceToolbar({
  isSaving = false,
  onSaveDraft,
  onIssue,
  onGoToInvoice,
  onCancel,
  canIssue = false,
  issueBlockedReason = '',
}) {
  return (
    <section className="invoice-toolbar">
      <div>
        <p>Acciones</p>
        <span>
          Guarda el borrador antes de emitir la factura.
        </span>
      </div>

      <div>
        <button
          className="table-button"
          disabled={isSaving || !onSaveDraft}
          onClick={onSaveDraft}
          type="button"
        >
          {isSaving ? 'Guardando...' : 'Guardar borrador'}
        </button>

        {onGoToInvoice ? <button className="primary-button" disabled={isSaving} onClick={onGoToInvoice} type="button">Ir a factura</button> : null}
        {!onGoToInvoice ? <><button className="primary-button" disabled={isSaving || !canIssue || !onIssue} onClick={onIssue} type="button">{isSaving ? 'Emitiendo CFDI…' : 'Emitir CFDI de prueba'}</button>{issueBlockedReason ? <small>{issueBlockedReason}</small> : null}</> : null}

        <button
          className="table-button table-button--danger"
          disabled={isSaving || !onCancel}
          onClick={onCancel}
          type="button"
        >
          Cancelar
        </button>
      </div>
    </section>
  );
}
