import { PackageOpen } from 'lucide-react';

import { formatMoney } from '../../utils/formatters.js';
import SatCatalogField from './SatCatalogField.jsx';

export default function InvoiceConceptsSection({
  catalogByCode,
  draft,
  onChange,
  quotation,
}) {
  const items = Array.isArray(quotation?.items)
    ? quotation.items.filter((item) => item.is_active !== false)
    : [];

  return (
    <section className="invoice-draft-section">
      <div className="invoice-section-heading">
        <div>
          <p>Conceptos</p>
          <h2>Conceptos de facturación</h2>
        </div>

        <div className="invoice-section-heading__meta">
          <span>
            {items.length} partida{items.length === 1 ? '' : 's'}
          </span>
          <PackageOpen size={20} />
        </div>
      </div>

      {!items.length ? (
        <p className="empty-state">
          La cotización no tiene conceptos registrados.
        </p>
      ) : (
        <div className="invoice-concepts-list">
          {items.map((item, index) => {
            const itemDraft = draft.concepts?.[item.id] || {};

            return (
              <article
                className="invoice-concept-card"
                key={item.id}
              >
                <header className="invoice-concept-card__header">
                  <div className="invoice-concept-card__identity">
                    <span className="invoice-concept-card__number">
                      Partida {index + 1}
                    </span>

                    <div>
                      <strong>
                        {item.service_name || 'Concepto sin nombre'}
                      </strong>

                      <span>
                        {item.description || 'Sin descripción registrada'}
                      </span>
                    </div>
                  </div>

                  <div className="invoice-concept-card__header-total">
                    <span>Importe</span>
                    <strong>{formatMoney(item.total)}</strong>
                  </div>
                </header>

                <div className="invoice-concept-card__commercial">
                  <span>
                    <small>Cantidad</small>
                    <strong>{item.quantity}</strong>
                  </span>

                  <span>
                    <small>Valor unitario</small>
                    <strong>{formatMoney(item.unit_price)}</strong>
                  </span>

                  <span>
                    <small>Importe</small>
                    <strong>{formatMoney(item.total)}</strong>
                  </span>
                </div>

                <div className="invoice-concept-card__fiscal">
                  <SatCatalogField
                    catalog={catalogByCode.get('products_services')}
                    catalogCode="products_services"
                    label="Producto / Servicio SAT"
                    onChange={(value) =>
                      onChange(item.id, 'productService', value)
                    }
                    value={
                      itemDraft.productService ||
                      (item.sat_key ? { code: item.sat_key } : null)
                    }
                  />

                  <SatCatalogField
                    catalog={catalogByCode.get('units')}
                    catalogCode="units"
                    label="Unidad SAT"
                    onChange={(value) =>
                      onChange(item.id, 'unit', value)
                    }
                    value={
                      itemDraft.unit ||
                      (item.sat_unit ? { code: item.sat_unit } : null)
                    }
                  />
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}