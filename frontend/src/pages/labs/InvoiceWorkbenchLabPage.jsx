import { useEffect, useMemo, useRef, useState } from 'react';

import InvoiceWorkbenchDialog from '../../components/invoice-workbench/InvoiceWorkbenchDialog.jsx';
import InvoiceQuotationList from '../../components/invoice-workbench/InvoiceQuotationList.jsx';
import InvoiceWorkbenchHeader from '../../components/invoice-workbench/InvoiceWorkbenchHeader.jsx';
import InvoiceWorkbenchSidebar from '../../components/invoice-workbench/InvoiceWorkbenchSidebar.jsx';
import { buildInvoiceWorkbenchDraft } from '../../components/invoice-workbench/invoiceWorkbenchDraft.js';
import {
  listClients,
  listQuotations,
  listSatCatalogs,
} from '../../services/api.js';
import { normalizeKey } from '../../utils/formatters.js';

import '../../components/invoice-workbench/invoice-workbench.css';

export default function InvoiceWorkbenchLabPage() {
  const [catalogs, setCatalogs] = useState([]);
  const [clients, setClients] = useState([]);
  const [draft, setDraft] = useState({});
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [quotations, setQuotations] = useState([]);
  const [search, setSearch] = useState('');
  const [isDraftOpen, setIsDraftOpen] = useState(false);
  const [selectedQuotation, setSelectedQuotation] = useState(null);

  const draftRequestIdRef = useRef(0);
  const originRowRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    async function loadLabData() {
      setIsLoading(true);
      setError('');

      const [quotationResult, clientResult, catalogResult] =
        await Promise.allSettled([
          listQuotations(),
          listClients(),
          listSatCatalogs(),
        ]);

      if (!isMounted) return;

      if (quotationResult.status === 'fulfilled') {
        setQuotations(
          Array.isArray(quotationResult.value)
            ? quotationResult.value
            : []
        );
      } else {
        setError(
          quotationResult.reason?.message ||
            'No fue posible cargar las cotizaciones.'
        );
      }

      if (clientResult.status === 'fulfilled') {
        setClients(
          Array.isArray(clientResult.value)
            ? clientResult.value
            : []
        );
      }

      if (catalogResult.status === 'fulfilled') {
        setCatalogs(
          Array.isArray(catalogResult.value)
            ? catalogResult.value
            : []
        );
      } else {
        setError(
          (current) =>
            current ||
            'No fue posible consultar los catálogos SAT locales.'
        );
      }

      setIsLoading(false);
    }

    loadLabData();

    return () => {
      isMounted = false;
    };
  }, []);

  const clientsById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients]
  );

  const catalogByCode = useMemo(
    () => new Map(catalogs.map((catalog) => [catalog.code, catalog])),
    [catalogs]
  );

  const visibleQuotations = useMemo(() => {
    const term = normalizeKey(search);

    return quotations
      .filter((quotation) => {
        const client = clientsById.get(quotation.client_id);

        const searchable = [
          quotation.folio,
          quotation.status,
          quotation.issued_on,
          client?.commercial_name,
          client?.legal_name,
          client?.rfc,
        ].join(' ');

        return !term || normalizeKey(searchable).includes(term);
      })
      .map((quotation) => ({
        quotation,
        client: clientsById.get(quotation.client_id),
      }));
  }, [clientsById, quotations, search]);

  const selectedClient = selectedQuotation
    ? clientsById.get(selectedQuotation.client_id)
    : null;

  async function openDraft(quotation, originRow) {
    const requestId = draftRequestIdRef.current + 1;
    draftRequestIdRef.current = requestId;

    const client = clientsById.get(quotation.client_id);

    originRowRef.current = originRow || document.activeElement;
    setSelectedQuotation(quotation);
    setDraft({});
    setIsDraftOpen(true);

    const nextDraft = await buildInvoiceWorkbenchDraft(quotation, client);

    if (draftRequestIdRef.current !== requestId) return;

    setDraft(nextDraft);
  }

  function updateDraft(key, value) {
    setDraft((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function updateConcept(conceptId, key, value) {
    setDraft((current) => ({
      ...current,
      concepts: {
        ...(current.concepts || {}),
        [conceptId]: {
          ...(current.concepts?.[conceptId] || {}),
          [key]: value,
        },
      },
    }));
  }

  function closeDraft() {
    draftRequestIdRef.current += 1;
    setIsDraftOpen(false);
    setSelectedQuotation(null);
    setDraft({});
  }


  return (
    <main className="invoice-workbench-lab">
      <InvoiceWorkbenchSidebar
        catalogCount={catalogs.length}
        quotation={selectedQuotation}
        view={isDraftOpen ? 'draft' : 'list'}
      />

      <div className="invoice-workbench-lab__content">
        <InvoiceWorkbenchHeader
          view="list"
        />

        <InvoiceQuotationList
          error={error}
          isLoading={isLoading}
          onCreateDraft={openDraft}
          onSearchChange={setSearch}
          quotations={visibleQuotations}
          search={search}
          selectedQuotationId={isDraftOpen ? selectedQuotation?.id : null}
        />

        <InvoiceWorkbenchDialog
          catalogByCode={catalogByCode}
          client={selectedClient}
          draft={draft}
          onClose={closeDraft}
          onConceptChange={updateConcept}
          onDraftChange={updateDraft}
          open={isDraftOpen}
          originElement={originRowRef.current}
          quotation={selectedQuotation}
        />
      </div>
    </main>
  );
}
