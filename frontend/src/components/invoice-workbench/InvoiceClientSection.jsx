import { Building2 } from 'lucide-react';

import { getClientDisplayName } from '../../utils/formatters.js';
import SatCatalogField from './SatCatalogField.jsx';

export default function InvoiceClientSection({ catalogByCode, client, draft, onChange }) {
  const receiver = draft.receiver || {};
  return (
    <section className="invoice-draft-section">
      <div className="invoice-section-heading"><div><p>Datos del Cliente</p><h2>Receptor</h2></div><Building2 size={20} /></div>
      <div className="invoice-client-summary"><div><span>Razón social</span><strong>{receiver.legalName || getClientDisplayName(client)}</strong></div><div><span>RFC</span><strong>{receiver.rfc || client?.rfc || 'Sin RFC registrado'}</strong></div></div>
      <div className="invoice-sat-grid invoice-sat-grid--client">
        <SatCatalogField catalog={catalogByCode.get('fiscal_regimes')} catalogCode="fiscal_regimes" label="Régimen fiscal" onChange={(value) => onChange('fiscalRegime', value)} value={draft.fiscalRegime} />
        <SatCatalogField catalog={catalogByCode.get('postal_codes')} catalogCode="postal_codes" label="Código Postal Fiscal" onChange={(value) => onChange('fiscalPostalCode', value)} value={draft.fiscalPostalCode} />
      </div>
    </section>
  );
}
