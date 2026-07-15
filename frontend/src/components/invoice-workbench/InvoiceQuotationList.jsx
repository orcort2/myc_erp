import {
  Ban,
  CheckCircle2,
  Clock3,
  FilePenLine,
  ReceiptText,
  Search,
} from 'lucide-react';

import { formatDate, formatMoney } from '../../utils/formatters.js';

const BILLING_STATUS = {
  ready: {
    label: 'Lista para facturar',
    className: 'is-ready',
  },
  draft: {
    label: 'Borrador',
    className: 'is-draft',
  },
  stamped: {
    label: 'Timbrada',
    className: 'is-stamped',
  },
  cancelled: {
    label: 'Cancelada',
    className: 'is-cancelled',
  },
};

function getBillingStatus() {
  /*
   * Por ahora todas las cotizaciones aceptadas disponibles
   * se consideran listas para facturar.
   *
   * Cuando exista persistencia de facturas, esta función deberá
   * resolver el estado real relacionado con la cotización.
   */
  return 'ready';
}

export default function InvoiceQuotationList({
  error,
  isLoading,
  onCreateDraft,
  onSearchChange,
  quotations,
  search,
  selectedQuotationId,
}) {
  const counters = quotations.reduce(
    (result, { quotation }) => {
      const billingStatus = getBillingStatus(quotation);

      result[billingStatus] += 1;

      return result;
    },
    {
      ready: 0,
      draft: 0,
      stamped: 0,
      cancelled: 0,
    }
  );

  function openQuotation(quotation, origin) {
    onCreateDraft(quotation, origin);
  }

  function handleRowKeyDown(event, quotation) {
    if (event.key !== 'Enter' && event.key !== ' ') return;

    event.preventDefault();
    openQuotation(quotation, event.currentTarget);
  }

  return (
    <section className="invoice-quotation-workspace">
      <div className="invoice-workspace-metrics">
        <article className="invoice-workspace-metric is-ready">
          <div>
            <span>Pendientes</span>
            <strong>{counters.ready}</strong>
          </div>

          <Clock3 size={20} />
        </article>

        <article className="invoice-workspace-metric is-draft">
          <div>
            <span>Borradores</span>
            <strong>{counters.draft}</strong>
          </div>

          <FilePenLine size={20} />
        </article>

        <article className="invoice-workspace-metric is-stamped">
          <div>
            <span>Timbradas</span>
            <strong>{counters.stamped}</strong>
          </div>

          <CheckCircle2 size={20} />
        </article>

        <article className="invoice-workspace-metric is-cancelled">
          <div>
            <span>Canceladas</span>
            <strong>{counters.cancelled}</strong>
          </div>

          <Ban size={20} />
        </article>
      </div>

      <section className="invoice-quotation-list">
        <div className="invoice-section-heading">
          <div>
            <p>Bandeja de facturación</p>
            <h2>Cotizaciones listas para facturar</h2>
          </div>

          <span>
            {quotations.length} registro
            {quotations.length === 1 ? '' : 's'}
          </span>
        </div>

        <label className="invoice-search">
          <Search size={17} />

          <input
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Buscar por cotización, cliente, RFC o estado..."
            value={search}
          />
        </label>

        {error ? <p className="form-error">{error}</p> : null}

        <div
          aria-busy={isLoading}
          className="invoice-workspace-table-wrapper"
        >
          <div className="invoice-workspace-table">
            <div
              aria-hidden="true"
              className="invoice-workspace-table__header"
            >
              <span>Estado</span>
              <span>Cotización</span>
              <span>Cliente</span>
              <span>Fecha</span>
              <span>Importe</span>
            </div>

            <div className="invoice-workspace-table__body">
              {isLoading ? (
                <p className="empty-state">
                  Cargando cotizaciones reales…
                </p>
              ) : null}

              {!isLoading && !quotations.length ? (
                <p className="empty-state">
                  No hay cotizaciones que coincidan con la búsqueda.
                </p>
              ) : null}

              {!isLoading
                ? quotations.map(({ quotation, client }) => {
                    const billingStatus = getBillingStatus(quotation);
                    const status =
                      BILLING_STATUS[billingStatus] ||
                      BILLING_STATUS.ready;

                    const clientName =
                      client?.commercial_name ||
                      client?.legal_name ||
                      `Cliente #${quotation.client_id}`;

                    return (
                      <article
                        aria-label={`Abrir cotización ${quotation.folio}`}
                        className={`invoice-workspace-row ${status.className}${selectedQuotationId === quotation.id ? ' is-draft-origin' : ''}`}
                        key={quotation.id}
                        onClick={(event) => openQuotation(quotation, event.currentTarget)}
                        onKeyDown={(event) =>
                          handleRowKeyDown(event, quotation)
                        }
                        role="button"
                        tabIndex={0}
                      >
                        <div
                          className="invoice-workspace-row__status"
                          data-label="Estado"
                        >
                          <span className="invoice-billing-status">
                            <i aria-hidden="true" />
                            {status.label}
                          </span>
                        </div>

                        <div
                          className="invoice-workspace-row__folio"
                          data-label="Cotización"
                        >
                          <ReceiptText size={16} />

                          <strong>{quotation.folio}</strong>
                        </div>

                        <div
                          className="invoice-workspace-row__client"
                          data-label="Cliente"
                        >
                          <strong>{clientName}</strong>

                          {client?.rfc ? <span>{client.rfc}</span> : null}
                        </div>

                        <div data-label="Fecha">
                          <span>{formatDate(quotation.issued_on)}</span>
                        </div>

                        <div
                          className="invoice-workspace-row__amount"
                          data-label="Importe"
                        >
                          <strong>{formatMoney(quotation.total)}</strong>
                        </div>
                      </article>
                    );
                  })
                : null}
            </div>
          </div>
        </div>

        <footer className="invoice-workspace-table__footer">
          <span>
            Haz clic sobre una fila para preparar el precomprobante.
          </span>

          <strong>
            Total visible: {quotations.length}
          </strong>
        </footer>
      </section>
    </section>
  );
}
