import { SlidersHorizontal } from 'lucide-react';

import SatCatalogField from './SatCatalogField.jsx';

export default function InvoiceAdvancedFiscalSection({
  catalogByCode,
  draft,
  onConceptChange,
  onDraftChange,
  quotation,
}) {
  const items = Array.isArray(quotation?.items)
    ? quotation.items.filter((item) => item.is_active !== false)
    : [];

  const generalFields = [
    ['Tipo de comprobante', 'voucher_types', 'voucherType'],
    ['Exportación', 'exports', 'export'],
    ['País receptor', 'countries', 'country'],
    ['Tipo de relación', 'relation_types', 'relationType'],
  ];

  return (
    <section className="invoice-draft-section invoice-fiscal-settings">
      <div className="invoice-section-heading">
        <div>
          <p>Configuración fiscal</p>
          <h2>Valores automáticos del CFDI</h2>
        </div>

        <SlidersHorizontal size={20} />
      </div>

      <div className="invoice-fiscal-settings__intro">
        <strong>Configuración predeterminada de MYC</strong>
        <span>
          Estos valores se aplican automáticamente a facturas de ingreso.
          Sólo deben modificarse cuando exista una excepción fiscal.
        </span>
      </div>

      <div className="invoice-sat-grid">
        {generalFields.map(([label, catalogCode, key]) => (
          <SatCatalogField
            catalog={catalogByCode.get(catalogCode)}
            catalogCode={catalogCode}
            key={key}
            label={label}
            onChange={(value) => onDraftChange(key, value)}
            value={draft[key]}
          />
        ))}
      </div>

      {items.length ? (
        <div className="invoice-fiscal-settings__concepts">
          <div className="invoice-fiscal-settings__concepts-heading">
            <div>
              <p>Impuestos por concepto</p>
              <h3>Configuración aplicada</h3>
            </div>

            <span>{items.length} concepto{items.length === 1 ? '' : 's'}</span>
          </div>

          <div className="invoice-fiscal-settings__concept-list">
            {items.map((item) => {
              const value = draft.concepts?.[item.id] || {};

              return (
                <article
                  className="invoice-fiscal-settings__concept"
                  key={item.id}
                >
                  <header>
                    <div>
                      <strong>
                        {item.service_name || 'Concepto sin nombre'}
                      </strong>
                      <span>
                        {item.description || 'Sin descripción registrada'}
                      </span>
                    </div>
                  </header>

                  <div className="invoice-sat-grid invoice-sat-grid--advanced">
                    <SatCatalogField
                      catalog={catalogByCode.get('tax_objects')}
                      catalogCode="tax_objects"
                      label="Objeto de impuesto"
                      onChange={(next) =>
                        onConceptChange(item.id, 'taxObject', next)
                      }
                      value={value.taxObject}
                    />

                    <SatCatalogField
                      catalog={catalogByCode.get('taxes')}
                      catalogCode="taxes"
                      label="Impuesto"
                      onChange={(next) =>
                        onConceptChange(item.id, 'tax', next)
                      }
                      value={value.tax}
                    />

                    <SatCatalogField
                      catalog={catalogByCode.get('factor_types')}
                      catalogCode="factor_types"
                      label="Tipo de factor"
                      onChange={(next) =>
                        onConceptChange(item.id, 'factorType', next)
                      }
                      value={value.factorType}
                    />

                    <SatCatalogField
                      catalog={catalogByCode.get('tax_rates')}
                      catalogCode="tax_rates"
                      label="Tasa / Cuota"
                      onChange={(next) =>
                        onConceptChange(item.id, 'taxRate', next)
                      }
                      value={value.taxRate}
                    />
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}