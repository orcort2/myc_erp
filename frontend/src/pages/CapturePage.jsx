import { FileUp, Send, UploadCloud } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import {
  bulkUploadCertificatePdfs,
  changeCertificateStatus,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders,
  uploadCertificatePdf,
  validateCertificatePdfMatch
} from '../services/api.js';
import { certificateStatusLabels, certificateTypeLabels } from '../constants/statuses.js';
import { getClientDisplayName } from '../utils/formatters.js';

function statusText(value) {
  return certificateStatusLabels[value] ?? value ?? '-';
}

export default function CapturePage() {
  const [certificates, setCertificates] = useState([]);
  const [orders, setOrders] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [clients, setClients] = useState([]);
  const [selectedOrderId, setSelectedOrderId] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [loadingAction, setLoadingAction] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const ordersById = useMemo(() => new Map(orders.map((item) => [item.id, item])), [orders]);
  const equipmentById = useMemo(() => new Map(equipment.map((item) => [item.id, item])), [equipment]);
  const sheetsById = useMemo(() => new Map(fieldSheets.map((item) => [item.id, item])), [fieldSheets]);
  const clientsById = useMemo(() => new Map(clients.map((item) => [item.id, item])), [clients]);
  const displayedCertificates = useMemo(
    () => certificates.filter((item) => !selectedOrderId || String(item.service_order_id) === String(selectedOrderId)),
    [certificates, selectedOrderId]
  );

  async function loadData() {
    setError('');
    setIsLoading(true);
    try {
      const [certs, serviceOrders, equipmentItems, sheets, clientItems] = await Promise.all([
        listCertificates(),
        listServiceOrders(),
        listEquipment(),
        listFieldSheets(),
        listClients()
      ]);
      setCertificates(Array.isArray(certs) ? certs : []);
      setOrders(Array.isArray(serviceOrders) ? serviceOrders : []);
      setEquipment(Array.isArray(equipmentItems) ? equipmentItems : []);
      setFieldSheets(Array.isArray(sheets) ? sheets : []);
      setClients(Array.isArray(clientItems) ? clientItems : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function context(certificate) {
    const order = ordersById.get(certificate.service_order_id);
    const item = equipmentById.get(certificate.equipment_id);
    const sheet = sheetsById.get(certificate.field_sheet_id);
    const client = order ? clientsById.get(order.client_id) : null;
    return { order, item, sheet, client };
  }

  async function runAction(certificate, action, label) {
    setLoadingAction(`${certificate.id}-${action}`);
    setError('');
    setNotice('');
    try {
      await changeCertificateStatus(certificate.id, action);
      setNotice(`${label}: ${certificate.expected_folio ?? certificate.folio}`);
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoadingAction('');
    }
  }

  async function uploadPdf(certificate, file) {
    if (!file) return;
    setLoadingAction(`${certificate.id}-upload`);
    setError('');
    try {
      await uploadCertificatePdf(certificate.id, file);
      setNotice(`PDF cargado para ${certificate.expected_folio ?? certificate.folio}`);
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoadingAction('');
    }
  }

  async function validateMatch(certificate) {
    setLoadingAction(`${certificate.id}-match`);
    setError('');
    try {
      await validateCertificatePdfMatch(certificate.id);
      setNotice('Matching actualizado');
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoadingAction('');
    }
  }

  async function bulkUpload(event) {
    const files = event.target.files;
    if (!selectedOrderId || !files?.length) return;
    setLoadingAction('bulk');
    setError('');
    try {
      const result = await bulkUploadCertificatePdfs(selectedOrderId, files);
      setNotice(`Carga masiva: ${result.matched} matched, ${result.warnings} warnings, ${result.mismatches} mismatch`);
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoadingAction('');
      event.target.value = '';
    }
  }

  return (
    <section className="module-workspace service-orders-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon"><FileUp size={28} /></span>
        <div>
          <p>Certificados externos</p>
          <h1>Captura</h1>
          <span>Control de captura en Excel, envio a calidad y carga de PDFs finales.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary">
        <div className="operations-band__metric"><strong>{isLoading ? '-' : certificates.filter((item) => ['expected', 'field_sheet_ready', 'capture_pending'].includes(item.status)).length}</strong><span>Pendientes captura</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : certificates.filter((item) => item.status === 'capture_in_progress').length}</strong><span>En captura</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : certificates.filter((item) => item.status === 'pdf_uploaded').length}</strong><span>PDF subido</span></div>
      </section>

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Ordenes y certificados</p>
            <h2>{displayedCertificates.length} certificados esperados</h2>
          </div>
          <div className="toolbar-actions">
            <select value={selectedOrderId} onChange={(event) => setSelectedOrderId(event.target.value)}>
              <option value="">Todas las ordenes</option>
              {orders.map((order) => (
                <option key={order.id} value={order.id}>OT {order.work_order_number} - {order.folio}</option>
              ))}
            </select>
            <label className="secondary-button">
              <UploadCloud size={16} />
              PDFs masivos
              <input accept="application/pdf" multiple type="file" hidden onChange={bulkUpload} disabled={!selectedOrderId || loadingAction === 'bulk'} />
            </label>
          </div>
        </div>

        <div className="clients-table certificates-table">
          <div className="clients-table__head">
            <span>Folio</span>
            <span>Cliente</span>
            <span>Equipo</span>
            <span>Tipo</span>
            <span>Estado</span>
            <span>PDF / Match</span>
            <span>Hoja</span>
            <span>Acciones</span>
          </div>
          {displayedCertificates.length ? displayedCertificates.map((certificate) => {
            const { order, item, sheet, client } = context(certificate);
            return (
              <div className="clients-table__row" key={certificate.id}>
                <span><strong>{certificate.expected_folio ?? certificate.folio}</strong><br /><small>OT {order?.work_order_number ?? '-'}</small></span>
                <span>{client ? getClientDisplayName(client) : '-'}</span>
                <span>{item?.name ?? '-'}<br /><small>{item?.serial_number ?? item?.internal_id ?? ''}</small></span>
                <span>{certificateTypeLabels[certificate.certificate_type] ?? certificate.certificate_type}</span>
                <span><mark className={`quotation-status status-${certificate.status}`}>{statusText(certificate.status)}</mark></span>
                <span>{certificate.final_pdf_original_filename ?? 'Sin PDF'}<br /><small>{certificate.match_status ?? 'pending'}</small></span>
                <span>{sheet ? `#${sheet.id} ${sheet.status}` : '-'}</span>
                <span className="table-actions">
                  <button className="table-button" type="button" onClick={() => runAction(certificate, 'start-capture', 'Captura iniciada')} disabled={loadingAction !== ''}>
                    Iniciar
                  </button>
                  <button className="table-button" type="button" onClick={() => runAction(certificate, 'send-to-quality', 'Enviado a calidad')} disabled={loadingAction !== ''}>
                    <Send size={14} /> Calidad
                  </button>
                  <label className="table-button">
                    PDF
                    <input accept="application/pdf" hidden type="file" onChange={(event) => uploadPdf(certificate, event.target.files?.[0])} />
                  </label>
                  <button className="table-button" type="button" onClick={() => validateMatch(certificate)} disabled={loadingAction !== ''}>
                    Match
                  </button>
                </span>
              </div>
            );
          }) : (
            <div className="clients-empty">No hay certificados para captura.</div>
          )}
        </div>
      </section>
    </section>
  );
}
