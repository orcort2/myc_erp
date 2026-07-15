import { X } from 'lucide-react';

export default function InvoiceWorkbenchHeader({
  mode = 'create',
  quotation,
  invoice,
  onClose,
}) {
  return (
    <header className="invoice-workbench-header">
      <div>
        <p>
          {mode === 'edit'
            ? 'Borrador de factura'
            : 'Preparar factura'}
        </p>

        <h2>
          {invoice
            ? `Factura ${invoice.series ?? ''}-${invoice.folio ?? ''}`
            : quotation
              ? `Cotización ${quotation.folio ?? ''}`
              : 'Nuevo borrador'}
        </h2>
      </div>

      <button
        className="icon-button"
        onClick={onClose}
        type="button"
      >
        <X size={18} />
      </button>
    </header>
  );
}