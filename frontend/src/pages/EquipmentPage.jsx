import { Boxes } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import {
  equipmentStatusLabels,
  fieldSheetStatusLabels,
  certificateStatusLabels
} from '../constants/statuses.js';
import {
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders
} from '../services/api.js';
import { formatDateTime, getClientDisplayName } from '../utils/formatters.js';

function EquipmentPage() {
  const [equipment, setEquipment] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const ordersById = useMemo(
    () => new Map(serviceOrders.map((order) => [order.id, order])),
    [serviceOrders]
  );

  const clientsById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients]
  );

  const activeFieldSheetByEquipmentId = useMemo(() => {
    const map = new Map();
    fieldSheets
      .filter((sheet) => sheet.is_active !== false)
      .forEach((sheet) => {
        if (!map.has(sheet.equipment_id)) {
          map.set(sheet.equipment_id, sheet);
        }
      });
    return map;
  }, [fieldSheets]);

  const activeCertificateByEquipmentId = useMemo(() => {
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

  const displayedEquipment = useMemo(() => {
    if (activeTab === 'active') {
      return equipment.filter((item) => ['registered', 'realizing'].includes(item.status));
    }
    if (activeTab === 'ready') {
      return equipment.filter((item) => ['calibrated', 'labeled'].includes(item.status));
    }
    if (activeTab === 'closed') {
      return equipment.filter((item) => ['not_done', 'cancelled'].includes(item.status));
    }
    return equipment;
  }, [activeTab, equipment]);

  useEffect(() => {
    async function loadData() {
      setError('');
      setIsLoading(true);
      try {
        const [equipmentResult, ordersResult, clientsResult, fieldSheetsResult, certificatesResult] = await Promise.all([
          listEquipment(),
          listServiceOrders(),
          listClients(),
          listFieldSheets(),
          listCertificates()
        ]);
        setEquipment(Array.isArray(equipmentResult) ? equipmentResult : []);
        setServiceOrders(Array.isArray(ordersResult) ? ordersResult : []);
        setClients(Array.isArray(clientsResult) ? clientsResult : []);
        setFieldSheets(Array.isArray(fieldSheetsResult) ? fieldSheetsResult : []);
        setCertificates(Array.isArray(certificatesResult) ? certificatesResult : []);
      } catch (requestError) {
        setError(requestError.message);
      } finally {
        setIsLoading(false);
      }
    }

    loadData();
  }, []);

  return (
    <section className="module-workspace service-orders-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <Boxes size={28} />
        </span>
        <div>
          <p>Inventario operativo</p>
          <h1>Equipos</h1>
          <span>Consulta transversal de instrumentos vinculados a ordenes, hojas y certificados.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}

      <section className="operations-band certificates-summary" aria-label="Resumen de equipos">
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : equipment.length}</strong>
          <span>Total equipos</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : equipment.filter((item) => ['calibrated', 'labeled'].includes(item.status)).length}</strong>
          <span>Listos</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : activeCertificateByEquipmentId.size}</strong>
          <span>Con certificado</span>
        </div>
      </section>

      <div className="module-tabs" role="tablist" aria-label="Filtros de equipos">
        {[
          ['all', 'Todos'],
          ['active', 'Activos'],
          ['ready', 'Calibrados / Etiquetados'],
          ['closed', 'Terminales']
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
            <p>Listado de equipos</p>
            <h2>{isLoading ? 'Cargando...' : `${displayedEquipment.length} equipos`}</h2>
          </div>
        </div>
        <div className="clients-table certificates-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>Equipo</span>
            <span>Cliente</span>
            <span>Orden</span>
            <span>OT</span>
            <span>Marca / modelo</span>
            <span>Serie</span>
            <span>Estado</span>
            <span>Hoja</span>
            <span>Certificado</span>
          </div>
          {isLoading ? (
            <div className="clients-empty">Cargando equipos...</div>
          ) : displayedEquipment.length ? (
            displayedEquipment.map((item) => {
              const order = ordersById.get(item.service_order_id);
              const client = order ? clientsById.get(order.client_id) : null;
              const fieldSheet = activeFieldSheetByEquipmentId.get(item.id);
              const certificate = activeCertificateByEquipmentId.get(item.id);
              return (
                <div className="clients-table__row" key={item.id}>
                  <span>
                    <strong>{item.name}</strong>
                    <br />
                    <small>{formatDateTime(item.updated_at)}</small>
                  </span>
                  <span>{getClientDisplayName(client)}</span>
                  <span>{order?.folio || '-'}</span>
                  <span>{order?.work_order_number ? `OT ${order.work_order_number}` : '-'}</span>
                  <span>{[item.brand, item.model].filter(Boolean).join(' / ') || '-'}</span>
                  <span>{item.serial_number || '-'}</span>
                  <span>
                    <mark className={`quotation-status status-${item.status}`}>
                      {equipmentStatusLabels[item.status] ?? item.status}
                    </mark>
                  </span>
                  <span>
                    {fieldSheet ? (
                      <mark className={`quotation-status status-${fieldSheet.status}`}>
                        Hoja #{fieldSheet.id} · {fieldSheetStatusLabels[fieldSheet.status] ?? fieldSheet.status}
                      </mark>
                    ) : (
                      '-'
                    )}
                  </span>
                  <span>
                    {certificate ? (
                      <mark className={`quotation-status status-${certificate.status}`}>
                        {certificate.folio} · {certificateStatusLabels[certificate.status] ?? certificate.status}
                      </mark>
                    ) : (
                      '-'
                    )}
                  </span>
                </div>
              );
            })
          ) : (
            <div className="clients-empty">No hay equipos en esta vista.</div>
          )}
        </div>
      </section>
    </section>
  );
}

export default EquipmentPage;
