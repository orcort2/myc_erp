import { FileUp, Send, UploadCloud } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import WorkOrderFlowGroups from '../components/WorkOrderFlowGroups.jsx';
import { certificateStatusLabels, certificateTypeLabels, fieldSheetStatusLabels } from '../constants/statuses.js';
import {
  bulkUploadCertificatePdfs,
  changeCertificateStatus,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders,
  uploadCertificatePdf
} from '../services/api.js';
import { getClientDisplayName } from '../utils/formatters.js';

const CAPTURE_UPLOAD_STATUSES = new Set(['expected', 'field_sheet_ready', 'capture_pending', 'capture_in_progress', 'pdf_uploaded', 'quality_rejected', 'correction_requested', 'returned_to_technician']);
const CAPTURE_SEND_STATUSES = new Set(['capture_in_progress', 'pdf_uploaded']);

export default function CapturePage() {
  const [certificates, setCertificates] = useState([]);
  const [orders, setOrders] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [clients, setClients] = useState([]);
  const [bulkOrderId, setBulkOrderId] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [loadingAction, setLoadingAction] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const ordersById = useMemo(() => new Map(orders.map((item) => [item.id, item])), [orders]);
  const equipmentById = useMemo(() => new Map(equipment.map((item) => [item.id, item])), [equipment]);
  const sheetsById = useMemo(() => new Map(fieldSheets.map((item) => [item.id, item])), [fieldSheets]);
  const clientsById = useMemo(() => new Map(clients.map((item) => [item.id, item])), [clients]);
  const captureCertificates = useMemo(() => certificates, [certificates]);
  const bulkEligibleOrderIds = useMemo(() => new Set(
    certificates
      .filter((item) => CAPTURE_UPLOAD_STATUSES.has(item.status) && !item.authenticated_pdf_path)
      .map((item) => String(item.service_order_id))
  ), [certificates]);

  async function loadData() {
    setError('');
    setIsLoading(true);
    try {
      const [certs, serviceOrders, equipmentItems, sheets, clientItems] = await Promise.all([
        listCertificates(), listServiceOrders(), listEquipment(), listFieldSheets(), listClients()
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

  useEffect(() => { loadData(); }, []);

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

  async function bulkUpload(event) {
    const files = event.target.files;
    if (!bulkOrderId || !files?.length) return;
    if (!bulkEligibleOrderIds.has(String(bulkOrderId))) {
      setError('Este ETS ya terminó Captura; los PDFs enviados no pueden reemplazarse desde esta etapa.');
      event.target.value = '';
      return;
    }
    setLoadingAction('bulk');
    setError('');
    try {
      const result = await bulkUploadCertificatePdfs(bulkOrderId, files);
      setNotice(`Carga masiva: ${result.matched} match, ${result.warnings} advertencias, ${result.mismatches} sin match`);
      await loadData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoadingAction('');
      event.target.value = '';
    }
  }

  function renderCertificate(certificate) {
    const order = ordersById.get(certificate.service_order_id);
    const item = equipmentById.get(certificate.equipment_id);
    const sheet = sheetsById.get(certificate.field_sheet_id);
    const client = order ? clientsById.get(order.client_id) : null;
    const busy = Boolean(loadingAction);
    return (
      <article className="flow-certificate-card" key={certificate.id}>
        <div className="flow-certificate-card__title">
          <div><span>Certificado</span><strong>{certificate.expected_folio ?? certificate.folio}</strong></div>
          <mark className={`quotation-status status-${certificate.status}`}>{certificateStatusLabels[certificate.status] ?? certificate.status}</mark>
        </div>
        <dl>
          <div><dt>Cliente</dt><dd>{getClientDisplayName(client)}</dd></div>
          <div><dt>Equipo</dt><dd>{item?.name ?? '-'}</dd></div>
          <div><dt>Serie</dt><dd>{item?.serial_number ?? item?.internal_id ?? '-'}</dd></div>
          <div><dt>Tipo</dt><dd>{certificateTypeLabels[certificate.certificate_type] ?? certificate.certificate_type}</dd></div>
          <div><dt>PDF</dt><dd>{certificate.final_pdf_original_filename ?? 'Sin PDF'}</dd></div>
          <div><dt>Hoja</dt><dd>{sheet ? `#${sheet.id} · ${fieldSheetStatusLabels[sheet.status] ?? sheet.status}` : '-'}</dd></div>
        </dl>
        <div className="toolbar-actions">
          {CAPTURE_UPLOAD_STATUSES.has(certificate.status) ? <label className="table-button">{certificate.status === 'correction_requested' || certificate.final_pdf_path ? 'Reemplazar PDF' : 'Subir PDF'}<input accept="application/pdf" hidden type="file" onChange={(event) => uploadPdf(certificate, event.target.files?.[0])} /></label> : null}
          {CAPTURE_SEND_STATUSES.has(certificate.status) ? <button className="table-button table-button--primary" disabled={busy || !certificate.final_pdf_path} onClick={() => runAction(certificate, 'send-to-quality', 'Enviado a Calidad')} type="button"><Send size={14} /> Enviar a Calidad</button> : null}
          {!CAPTURE_UPLOAD_STATUSES.has(certificate.status) && !CAPTURE_SEND_STATUSES.has(certificate.status) ? <span className="flow-action-complete">Enviado a Calidad</span> : null}
        </div>
      </article>
    );
  }

  return (
    <section className="module-workspace service-orders-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon"><FileUp size={28} /></span>
        <div><p>Certificados externos</p><h1>Captura</h1><span>Sube el PDF original o su corrección y envíalo a Calidad.</span></div>
      </div>
      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}
      <section className="operations-band certificates-summary">
        <div className="operations-band__metric"><strong>{isLoading ? '-' : captureCertificates.filter((item) => CAPTURE_UPLOAD_STATUSES.has(item.status) && !item.final_pdf_path).length}</strong><span>Pendientes captura</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : captureCertificates.filter((item) => item.status === 'capture_in_progress').length}</strong><span>En captura</span></div>
        <div className="operations-band__metric"><strong>{isLoading ? '-' : captureCertificates.filter((item) => item.status === 'ready_for_quality').length}</strong><span>Enviados a Calidad</span></div>
      </section>
      <section className="clients-list-panel">
        <div className="section-heading">
          <div><p>ETS y Órdenes de Trabajo</p><h2>{captureCertificates.length} certificados en Captura</h2></div>
          <div className="toolbar-actions">
            <select value={bulkOrderId} onChange={(event) => setBulkOrderId(event.target.value)}><option value="">Selecciona ETS para carga masiva</option>{orders.filter((order) => bulkEligibleOrderIds.has(String(order.id))).map((order) => <option key={order.id} value={order.id}>{order.folio}</option>)}</select>
            <label className="secondary-button"><UploadCloud size={16} /> PDFs masivos<input accept="application/pdf" disabled={!bulkOrderId || !bulkEligibleOrderIds.has(String(bulkOrderId)) || loadingAction === 'bulk'} hidden multiple type="file" onChange={bulkUpload} /></label>
          </div>
        </div>
        {isLoading ? <div className="clients-empty">Cargando certificados de Captura...</div> : (
          <WorkOrderFlowGroups
            emptyMessage="No hay certificados en Captura."
            equipmentById={equipmentById}
            getGroupState={(items) => items.every((item) => item.status === 'ready_for_quality') ? { label: 'LISTA', tone: 'approved' } : { label: 'EN PROCESO', tone: 'capture_in_progress' }}
            items={captureCertificates}
            orders={orders}
            renderItem={renderCertificate}
          />
        )}
      </section>
    </section>
  );
}
