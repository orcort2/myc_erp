import SatCatalogField from './SatCatalogField.jsx';

export default function InvoiceFiscalSection({ catalogByCode, draft, invoice, onChange }) {
  const fields = [
    ['Uso CFDI', 'cfdi_uses', 'cfdiUse'],
    ['Forma de pago', 'payment_forms', 'paymentForm'],
    ['Método de pago', 'payment_methods', 'paymentMethod'],
    ['Moneda', 'currencies', 'currency'],
  ];
  const status = invoice?.review_required ? 'Revisión requerida' : invoice ? 'Borrador guardado' : 'Datos del cliente';
  return <section className="invoice-draft-section"><div className="invoice-section-heading"><div><p>Datos de la factura</p><h2>Información comercial</h2></div><span>{status}</span></div><div className="invoice-sat-grid">{fields.map(([label, catalogCode, key]) => <SatCatalogField catalog={catalogByCode.get(catalogCode)} catalogCode={catalogCode} key={key} label={label} onChange={(value) => onChange(key, value)} showAllOnOpen={catalogCode === 'cfdi_uses'} value={draft[key]} />)}</div></section>;
}
