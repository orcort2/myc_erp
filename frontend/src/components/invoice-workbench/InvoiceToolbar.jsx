export default function InvoiceToolbar({
  isSaving = false,
  onSaveDraft,
  onIssue,
  onCancel,
  canIssue = false,
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

        <button
          className="primary-button"
          disabled={isSaving || !canIssue || !onIssue}
          onClick={onIssue}
          type="button"
        >
          Emitir
        </button>

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