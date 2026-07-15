import { formatMoney, getClientDisplayName } from '../../utils/formatters.js';

export default function InvoiceSummaryPanel({ client, quotation }) {
  return <aside className="invoice-summary-panel">
    <p>Resumen</p>
    <h2>Precomprobante</h2>
    <div className="invoice-summary-panel__details">
      <span>Origen</span>
      <strong>{quotation?.folio || 'Cotización sin folio'}</strong>
      <span>Receptor</span>
      <strong>{getClientDisplayName(client)}</strong>
    </div>
    <div><span>Subtotal</span><strong>{formatMoney(quotation?.subtotal)}</strong></div>
    <div><span>IVA</span><strong>{formatMoney(quotation?.tax_total)}</strong></div>
    <div className="invoice-summary-panel__total"><span>Total</span><strong>{formatMoney(quotation?.total)}</strong></div>
    <small>Vista condensada de la cotización. Este Lab no calcula ni guarda importes fiscales.</small>
  </aside>;
}
