import { BadgeCheck } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import {
  certificateStatusLabels,
  fieldSheetStatusLabels
} from '../constants/statuses.js';
import {
  downloadFieldSheetPdf,
  getFieldSheetPdfUrl,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders
} from '../services/api.js';
import { formatDateTime, getClientDisplayName } from '../utils/formatters.js';
import { getFieldSheetTemplateLabel } from '../utils/fieldSheets.js';

function FieldSheetsPage() {
  const [fieldSheets, setFieldSheets] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const equipmentById = useMemo(
    () => new Map(equipment.map((item) => [item.id, item])),
    [equipment]
  );

  const ordersById = useMemo(
    () => new Map(serviceOrders.map((order) => [order.id, order])),
    [serviceOrders]
  );

  const clientsById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients]
  );

  const activeCertificatesByEquipmentId = useMemo(() => {
    const map = new Map();

    certificates
      .filter((certificate) => certificate.is_active !== false)
      .forEach((certificate) => {
        if (!map.has(certificate.equipment_id)) {
          map.set(certificate.equipment_id, certificate);
        }
      });

    return map;
  }, [certificates]);

  const displayedFieldSheets = useMemo(() => {
    if (activeTab === 'draft') {
      return fieldSheets.filter((sheet) => sheet.status === 'draft');
    }

    if (activeTab === 'progress') {
      return fieldSheets.filter((sheet) => sheet.status === 'in_progress');
    }

    if (activeTab === 'review') {
      return fieldSheets.filter((sheet) =>
        ['completed', 'under_review', 'approved'].includes(sheet.status)
      );
    }

    if (activeTab === 'cancelled') {
      return fieldSheets.filter((sheet) => sheet.status === 'cancelled');
    }

    return fieldSheets;
  }, [activeTab, fieldSheets]);

  useEffect(() => {
    async function loadData() {
      setError('');
      setIsLoading(true);

      try {
        const [
          fieldSheetsResult,
          equipmentResult,
          ordersResult,
          clientsResult,
          certificatesResult
        ] = await Promise.all([
          listFieldSheets(),
          listEquipment(),
          listServiceOrders(),
          listClients(),
          listCertificates()
        ]);

        setFieldSheets(Array.isArray(fieldSheetsResult) ? fieldSheetsResult : []);
        setEquipment(Array.isArray(equipmentResult) ? equipmentResult : []);
        setServiceOrders(Array.isArray(ordersResult) ? ordersResult : []);
        setClients(Array.isArray(clientsResult) ? clientsResult : []);
        setCertificates(Array.isArray(certificatesResult) ? certificatesResult : []);
      } catch (requestError) {
        setError(requestError.message);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, []);

  function getSheetContext(sheet) {
    const item = equipmentById.get(sheet.equipment_id);
    const order = item ? ordersById.get(item.service_order_id) : null;
    const client = order ? clientsById.get(order.client_id) : null;
    const certificate = item ? activeCertificatesByEquipmentId.get(item.id) : null;

    return { item, order, client, certificate };
  }

  function openFieldSheetPdf(fieldSheetId, mode = 'view') {
    const pdfWindow = window.open(
      getFieldSheetPdfUrl(fieldSheetId),
      '_blank',
      'noopener,noreferrer'
    );

    if (mode === 'print' && pdfWindow) {
      pdfWindow.addEventListener('load', () => {
        pdfWindow.focus();
        pdfWindow.print();
      });
    }
  }

  async function handleDownloadPdf(sheet) {
    setError('');
    setNotice('');

    try {
      const { item } = getSheetContext(sheet);
      const { blob, filename } = await downloadFieldSheetPdf(
        sheet.id,
        sheet.work_order_number,
        item?.name || `hoja-${sheet.id}`
      );

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = url;
      link.download = filename;

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      URL.revokeObjectURL(url);

      setNotice(`PDF ${filename} generado correctamente`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  return (
    <section className="module-workspace service-orders-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <BadgeCheck size={28} />
        </span>

        <div>
          <p>Trazabilidad tecnica</p>
          <h1>Hojas de campo</h1>
          <span>
            Consulta de hojas, estado documental, PDF tecnico y folio reservado.
          </span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary" aria-label="Resumen de hojas">
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : fieldSheets.length}</strong>
          <span>Total hojas</span>
        </div>

        <div className="operations-band__metric">
          <strong>
            {isLoading
              ? '-'
              : fieldSheets.filter((sheet) =>
                  ['completed', 'under_review', 'approved'].includes(sheet.status)
                ).length}
          </strong>
          <span>Listas para captura</span>
        </div>

        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.length}</strong>
          <span>Certificados esperados</span>
        </div>
      </section>

      <div className="module-tabs" role="tablist" aria-label="Filtros de hojas de campo">
        {[
          ['all', 'Todas'],
          ['draft', 'Borrador'],
          ['progress', 'En proceso'],
          ['review', 'Completadas / Revision'],
          ['cancelled', 'Canceladas']
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-selected={activeTab === key}
            className={activeTab === key ? 'module-tab is-active' : 'module-tab'}
            onClick={() => setActiveTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Listado de hojas</p>
            <h2>{isLoading ? 'Cargando...' : `${displayedFieldSheets.length} hojas`}</h2>
          </div>
        </div>

        <div className="clients-table certificates-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>OT</span>
            <span>Orden</span>
            <span>Cliente</span>
            <span>Equipo</span>
            <span>Folio certificado</span>
            <span>Plantilla</span>
            <span>Estado hoja</span>
            <span>Estado certificado</span>
            <span>Actualizado</span>
            <span>Acciones</span>
          </div>

          {isLoading ? (
            <div className="clients-empty">Cargando hojas de campo...</div>
          ) : displayedFieldSheets.length ? (
            displayedFieldSheets.map((sheet) => {
              const { item, order, client, certificate } = getSheetContext(sheet);

              return (
                <div className="clients-table__row" key={sheet.id}>
                  <span>{sheet.work_order_number ? `OT ${sheet.work_order_number}` : '-'}</span>
                  <span>{order?.folio || '-'}</span>
                  <span>{getClientDisplayName(client)}</span>
                  <span>{item?.name || '-'}</span>
                  <span>{certificate?.expected_folio || certificate?.folio || '-'}</span>
                  <span>{getFieldSheetTemplateLabel(sheet.template_key)}</span>

                  <span>
                    <mark className={`quotation-status status-${sheet.status}`}>
                      {fieldSheetStatusLabels[sheet.status] ?? sheet.status}
                    </mark>
                  </span>

                  <span>
                    {certificate ? (
                      <mark className={`quotation-status status-${certificate.status}`}>
                        {certificateStatusLabels[certificate.status] ?? certificate.status}
                      </mark>
                    ) : (
                      '-'
                    )}
                  </span>

                  <span>{formatDateTime(sheet.updated_at)}</span>

                  <span className="clients-table__actions">
                    <button
                      className="table-button"
                      onClick={() => openFieldSheetPdf(sheet.id, 'view')}
                      type="button"
                    >
                      Ver PDF
                    </button>

                    <button
                      className="table-button"
                      onClick={() => handleDownloadPdf(sheet)}
                      type="button"
                    >
                      Descargar
                    </button>

                    <button
                      className="table-button"
                      onClick={() => openFieldSheetPdf(sheet.id, 'print')}
                      type="button"
                    >
                      Imprimir
                    </button>
                  </span>
                </div>
              );
            })
          ) : (
            <div className="clients-empty">No hay hojas de campo en esta vista.</div>
          )}
        </div>
      </section>
    </section>
  );
}

export default FieldSheetsPage;
