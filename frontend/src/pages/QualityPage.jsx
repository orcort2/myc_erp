import { ShieldCheck } from 'lucide-react';
import React, { useEffect, useMemo, useRef, useState } from 'react';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import WorkOrderFlowGroups from '../components/WorkOrderFlowGroups.jsx';
import {
  equipmentStatusLabels,
  certificateStatusLabels,
  certificateTypeLabels,
  certificateTransitions
} from '../constants/statuses.js';
import {
  authenticateCertificate,
  changeCertificateStatus,
  downloadCaptureMaster,
  getCertificate,
  listAuditLogs,
  listCertificates,
  listCaptureMasterReadiness,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders
} from '../services/api.js';
import { formatDate, formatDateTime, getClientDisplayName } from '../utils/formatters.js';
import { getSequentialNavigationState } from '../utils/sequentialNavigation.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import { itemBelongsToWorkOrder } from '../utils/workOrderGroups.js';

function getTechnicianLabel(order) {
  return order?.technician_id ? `#${order.technician_id}` : 'Por asignar';
}

function getAuditStatusValue(values) {
  if (!values || typeof values !== 'object') {
    return '-';
  }
  return values.status || values.is_active || '-';
}

function formatAuditAction(action) {
  return String(action || '-')
    .replaceAll('.', ' / ')
    .replaceAll('_', ' ');
}

function QualityPage() {
  const [certificates, setCertificates] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [clients, setClients] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [masterReadiness, setMasterReadiness] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [selectedCertificate, setSelectedCertificate] = useState(null);
  const [detailNavigationIds, setDetailNavigationIds] = useState([]);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailLoadError, setDetailLoadError] = useState('');
  const [failedNavigationId, setFailedNavigationId] = useState(null);
  const [detailTab, setDetailTab] = useState('certificate');
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadingAction, setLoadingAction] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [correctionRequest, setCorrectionRequest] = useState(null);
  const [correctionReason, setCorrectionReason] = useState('');
  const detailRequestIdRef = useRef(0);
  const detailLoadingRef = useRef(false);
  const { confirmDialog, openConfirm, closeConfirm, handleConfirm } = useConfirmDialog();

  const clientsById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients]
  );

  const ordersById = useMemo(
    () => new Map(serviceOrders.map((order) => [order.id, order])),
    [serviceOrders]
  );

  const equipmentById = useMemo(
    () => new Map(equipment.map((item) => [item.id, item])),
    [equipment]
  );

  const fieldSheetsById = useMemo(
    () => new Map(fieldSheets.map((sheet) => [sheet.id, sheet])),
    [fieldSheets]
  );

  const readinessByCertificateId = useMemo(
    () => new Map(masterReadiness.map((item) => [item.certificate_id, item])),
    [masterReadiness]
  );

  const displayedCertificates = useMemo(() => {
    const qualityFlowCertificates = certificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated', 'quality_approved', 'approved'].includes(certificate.status));
    if (activeTab === 'pending') {
      return qualityFlowCertificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated'].includes(certificate.status));
    }
    if (activeTab === 'review') {
      return qualityFlowCertificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated'].includes(certificate.status));
    }
    if (activeTab === 'approved') {
      return qualityFlowCertificates.filter((certificate) => ['quality_approved', 'approved'].includes(certificate.status));
    }
    return qualityFlowCertificates;
  }, [activeTab, certificates]);

  const qualityTabs = [
    { key: 'pending', label: 'Pendientes' },
    { key: 'review', label: 'En revisión' },
    { key: 'approved', label: 'Aprobados' }
  ];

  async function loadQualityData() {
    setError('');
    setIsLoading(true);
    try {
      const [certificatesResult, ordersResult, equipmentResult, fieldSheetsResult, clientsResult, readinessResult] = await Promise.all([
        listCertificates(),
        listServiceOrders(),
        listEquipment(),
        listFieldSheets(),
        listClients(),
        listCaptureMasterReadiness()
      ]);
      setCertificates(Array.isArray(certificatesResult) ? certificatesResult : []);
      setServiceOrders(Array.isArray(ordersResult) ? ordersResult : []);
      setEquipment(Array.isArray(equipmentResult) ? equipmentResult : []);
      setFieldSheets(Array.isArray(fieldSheetsResult) ? fieldSheetsResult : []);
      setClients(Array.isArray(clientsResult) ? clientsResult : []);
      setMasterReadiness(Array.isArray(readinessResult) ? readinessResult : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadQualityData();
  }, []);

  function getCertificateContext(certificate) {
    const order = ordersById.get(certificate.service_order_id);
    const item = equipmentById.get(certificate.equipment_id);
    const sheet = fieldSheetsById.get(certificate.field_sheet_id);
    const client = order ? clientsById.get(order.client_id) : null;
    return { client, item, order, sheet };
  }

  async function loadCertificateDetail(certificateId, { openModal = false, resetTab = false } = {}) {
    if (detailLoadingRef.current) return false;
    const requestId = detailRequestIdRef.current + 1;
    detailRequestIdRef.current = requestId;
    detailLoadingRef.current = true;
    setIsDetailLoading(true);
    setDetailLoadError('');
    setFailedNavigationId(null);
    try {
      const [freshCertificate, logs] = await Promise.all([
        getCertificate(certificateId),
        listAuditLogs({ entity: 'certificates', entity_id: certificateId, limit: 100 })
      ]);
      if (detailRequestIdRef.current !== requestId) return false;
      setSelectedCertificate(freshCertificate);
      setAuditLogs(Array.isArray(logs) ? logs : []);
      if (resetTab) setDetailTab('certificate');
      if (openModal) setIsDetailOpen(true);
      return true;
    } catch (requestError) {
      if (detailRequestIdRef.current !== requestId) return false;
      if (openModal) {
        setError(requestError.message);
      } else {
        setDetailLoadError('No fue posible cargar el certificado.');
        setFailedNavigationId(certificateId);
      }
      return false;
    } finally {
      if (detailRequestIdRef.current === requestId) {
        detailLoadingRef.current = false;
        setIsDetailLoading(false);
      }
    }
  }

  async function openQualityDetail(certificate, groupContext = {}) {
    setError('');
    setNotice('');
    const workOrder = groupContext.workOrder;
    const sameWorkOrder = workOrder
      ? displayedCertificates.filter((candidate) => itemBelongsToWorkOrder(candidate, workOrder, equipmentById))
      : [];
    const sameOrder = displayedCertificates.filter((candidate) => Number(candidate.service_order_id) === Number(certificate.service_order_id));
    const contextualCertificates = sameWorkOrder.length ? sameWorkOrder : sameOrder.length ? sameOrder : displayedCertificates;
    setDetailNavigationIds(contextualCertificates.map((candidate) => candidate.id));
    await loadCertificateDetail(certificate.id, { openModal: true, resetTab: true });
  }

  async function navigateCertificate(direction) {
    if (!selectedCertificate || detailLoadingRef.current || isDetailLoading || loadingAction) return;
    const navigation = getSequentialNavigationState(detailNavigationIds, selectedCertificate.id);
    const targetId = direction === 'next' ? navigation.nextId : navigation.previousId;
    if (targetId == null) return;
    await loadCertificateDetail(targetId);
  }

  function closeQualityDetail() {
    detailRequestIdRef.current += 1;
    detailLoadingRef.current = false;
    setSelectedCertificate(null);
    setDetailNavigationIds([]);
    setAuditLogs([]);
    setIsDetailLoading(false);
    setDetailLoadError('');
    setFailedNavigationId(null);
    setDetailTab('certificate');
    setIsDetailOpen(false);
    setError('');
  }

  function canTransition(certificate, nextStatus) {
    return certificateTransitions[certificate.status]?.has(nextStatus) ?? false;
  }

  async function handleQualityAction(actionKey, label, comment = null) {
    if (!selectedCertificate) return;
    openConfirm({
      title: 'Confirmar accion de calidad',
      message: `El certificado ${selectedCertificate.folio} cambiará mediante la acción "${label}".`,
      confirmText: label,
      variant: 'danger',
      onConfirm: async () => {
        setLoadingAction(actionKey + label);
        setError('');
        setNotice('');
        try {
          const updated = await changeCertificateStatus(selectedCertificate.id, actionKey, comment);
          const logs = await listAuditLogs({ entity: 'certificates', entity_id: updated.id, limit: 100 });
          setSelectedCertificate(updated);
          setAuditLogs(Array.isArray(logs) ? logs : []);
          setCertificates((current) =>
            current.map((certificate) => (certificate.id === updated.id ? updated : certificate))
          );
          setNotice(`Certificado ${updated.folio} actualizado a ${certificateStatusLabels[updated.status] ?? updated.status}`);
          await loadQualityData();
          await loadCertificateDetail(updated.id);
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setLoadingAction('');
        }
      }
    });
  }

  async function runQualityOperation(actionKey, operation, successMessage) {
    if (!selectedCertificate) return;
    setLoadingAction(actionKey);
    setError('');
    setNotice('');
    try {
      const updated = await operation();
      setCertificates((current) => current.map((item) => item.id === updated.id ? updated : item));
      setNotice(successMessage);
      setSelectedCertificate(updated);
      await loadQualityData();
      await loadCertificateDetail(updated.id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoadingAction('');
    }
  }

  async function confirmCorrectionRequest() {
    const reason = correctionReason.trim();
    if (!correctionRequest || !reason) {
      setError('El comentario de corrección es obligatorio.');
      return;
    }
    setLoadingAction('request-correction');
    setError('');
    try {
      const updated = await changeCertificateStatus(correctionRequest.id, 'request-correction', reason);
      setCertificates((current) => current.map((item) => item.id === updated.id ? updated : item));
      setCorrectionRequest(null);
      setCorrectionReason('');
      setNotice(`Certificado ${updated.folio} regresado a Captura para corrección`);
      await loadQualityData();
      await loadCertificateDetail(updated.id);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoadingAction('');
    }
  }

  async function handleDownloadMaster(certificate) {
    setError('');
    try {
      const readiness = readinessByCertificateId.get(certificate.id);
      const { blob, filename } = await downloadCaptureMaster(certificate.id, readiness?.master?.filename);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 60 * 1000);
      setNotice(`Master ${filename} descargado para revisión.`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  const selectedContext = selectedCertificate ? getCertificateContext(selectedCertificate) : {};
  const selectedOrder = selectedContext.order;
  const selectedEquipment = selectedContext.item;
  const selectedFieldSheet = selectedContext.sheet;
  const selectedWorkOrder = selectedOrder?.work_orders?.find((workOrder) => Number(workOrder.id) === Number(selectedEquipment?.work_order_id));
  const selectedWorkOrderNumber = selectedWorkOrder?.work_order_number ?? selectedEquipment?.work_order_number ?? selectedOrder?.work_order_number;
  const selectedMasterReadiness = selectedCertificate ? readinessByCertificateId.get(selectedCertificate.id) : null;
  const selectedNavigation = getSequentialNavigationState(detailNavigationIds, selectedCertificate?.id);
  const previousCertificateDisabled = isDetailLoading || Boolean(loadingAction) || selectedNavigation.previousId == null;
  const nextCertificateDisabled = isDetailLoading || Boolean(loadingAction) || selectedNavigation.nextId == null;

  return (
    <section className="module-workspace quality-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <ShieldCheck size={28} />
        </span>
        <div>
          <p>Supervision transversal</p>
          <h1>Calidad</h1>
          <span>Revisión de Masters XLSX identificados, advertencias y diferencias antes de aprobar.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary" aria-label="Resumen de calidad">
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated'].includes(certificate.status)).length}</strong>
          <span>Pendientes calidad</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.filter((certificate) => ['quality_approved', 'approved'].includes(certificate.status)).length}</strong>
          <span>Aprobados</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.filter((certificate) => certificate.authenticated_pdf_path).length}</strong>
          <span>Autenticados</span>
        </div>
      </section>

      <div className="module-tabs module-tabs--five" role="tablist" aria-label="Navegacion de calidad">
        {qualityTabs.map((tab) => (
          <button
            aria-selected={activeTab === tab.key}
            className={activeTab === tab.key ? 'module-tab is-active' : 'module-tab'}
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Control de calidad</p>
            <h2>{isLoading ? 'Cargando...' : `${displayedCertificates.length} certificados`}</h2>
          </div>
        </div>
        {isLoading ? <div className="clients-empty">Cargando certificados para Calidad...</div> : (
          <WorkOrderFlowGroups
            emptyMessage="No hay certificados en esta vista de Calidad."
            equipmentById={equipmentById}
            getGroupState={(items) => items.every((item) => ['quality_approved', 'approved'].includes(item.status)) ? { label: 'APROBADA', tone: 'approved' } : { label: 'EN REVISIÓN', tone: 'quality_review' }}
            items={displayedCertificates}
            orders={serviceOrders}
            renderItem={(certificate, groupContext) => {
              const context = getCertificateContext(certificate);
              const readiness = readinessByCertificateId.get(certificate.id);
              return <button className="flow-certificate-card flow-certificate-card--button" key={certificate.id} onClick={() => openQualityDetail(certificate, groupContext)} type="button"><div className="flow-certificate-card__title"><div><span>Certificado</span><strong>{certificate.folio}</strong></div><mark className={`quotation-status status-${certificate.status}`}>{certificateStatusLabels[certificate.status] ?? certificate.status}</mark></div><dl><div><dt>Cliente</dt><dd>{getClientDisplayName(context.client)}</dd></div><div><dt>Equipo</dt><dd>{context.item?.name || '-'}</dd></div><div><dt>Técnico</dt><dd>{getTechnicianLabel(context.order)}</dd></div><div><dt>Fecha</dt><dd>{formatDate(certificate.issued_on) !== '-' ? formatDate(certificate.issued_on) : formatDateTime(certificate.created_at)}</dd></div><div><dt>Master</dt><dd>{readiness?.identified ? 'Identificado' : 'Pendiente'}</dd></div><div><dt>Alertas</dt><dd>{readiness?.warnings?.length || 0}</dd></div><div><dt>Diferencias</dt><dd>{readiness?.mismatches?.length || 0}</dd></div></dl></button>;
            }}
          />
        )}
      </section>

      {isDetailOpen && selectedCertificate ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-detail-modal field-sheet-modal certificate-detail-modal" aria-modal="true" role="dialog">
            <div className="client-modal-header">
              <div>
                <p>Revision de Calidad</p>
                <h2>{isDetailLoading ? 'Cargando certificado...' : 'Revisión de certificado'}</h2>
                {!isDetailLoading ? <span>{getClientDisplayName(selectedContext.client)} · {selectedOrder?.folio || '-'} · {selectedWorkOrderNumber ? `OT-${selectedWorkOrderNumber}` : 'OT sin asignar'}</span> : null}
              </div>
              {!isDetailLoading ? <mark className={`quotation-status quotation-status--large status-${selectedCertificate.status}`}>{certificateStatusLabels[selectedCertificate.status] ?? selectedCertificate.status}</mark> : null}
              <div className="client-modal-navigator">
                <button aria-label="Certificado anterior" disabled={previousCertificateDisabled} onClick={() => navigateCertificate('previous')} type="button">◀</button>
                <strong>{isDetailLoading ? 'Cargando…' : selectedCertificate.folio}</strong>
                <button aria-label="Certificado siguiente" disabled={nextCertificateDisabled} onClick={() => navigateCertificate('next')} type="button">▶</button>
                <button aria-label="Cerrar modal" disabled={isDetailLoading || Boolean(loadingAction)} onClick={closeQualityDetail} type="button">✕</button>
              </div>
            </div>

            {detailLoadError ? <div className="form-error dashboard-error" role="alert"><span>{detailLoadError}</span>{failedNavigationId ? <button className="table-button" disabled={isDetailLoading} onClick={() => loadCertificateDetail(failedNavigationId)} type="button">Reintentar</button> : null}</div> : null}

            {isDetailLoading ? <div className="clients-empty" role="status">Cargando datos del certificado...</div> : (
              <>

            <div className="client-modal-tabs quotation-detail-tabs" role="tablist" aria-label="Ficha de calidad">
              {[
                ['certificate', 'Certificado'],
                ['field-sheet', 'Hoja de Campo'],
                ['equipment', 'Equipo'],
                ['history', 'Historial']
              ].map(([key, label]) => (
                <button
                  aria-selected={detailTab === key}
                  className={detailTab === key ? 'client-modal-tab is-active' : 'client-modal-tab'}
                  key={key}
                  onClick={() => setDetailTab(key)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>

            {detailTab === 'certificate' ? (
              <>
                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <p>Certificado</p>
                    <h3>Revision documental</h3>
                  </div>
                  <div className="quotation-commercial-grid service-order-info-grid">
                    <article>
                      <span>Folio</span>
                      <strong>{selectedCertificate.expected_folio ?? selectedCertificate.folio}</strong>
                    </article>
                    <article>
                      <span>Tipo</span>
                      <strong>{certificateTypeLabels[selectedCertificate.certificate_type] ?? selectedCertificate.certificate_type}</strong>
                    </article>
                    <article>
                      <span>Estado</span>
                      <strong>{certificateStatusLabels[selectedCertificate.status] ?? selectedCertificate.status}</strong>
                    </article>
                    <article>
                      <span>ETS</span>
                      <strong>{selectedOrder?.folio || '-'}</strong>
                    </article>
                    <article>
                      <span>Orden de Trabajo</span>
                      <strong>{selectedWorkOrderNumber ? `OT-${selectedWorkOrderNumber}` : '-'}</strong>
                    </article>
                    <article>
                      <span>Master XLSX</span>
                      <strong>{selectedMasterReadiness?.master?.filename || 'Pendiente'}</strong>
                    </article>
                    <article>
                      <span>Advertencias</span>
                      <strong>{selectedMasterReadiness?.warnings?.length || 0}</strong>
                    </article>
                    <article>
                      <span>Diferencias bloqueantes</span>
                      <strong>{selectedMasterReadiness?.mismatches?.length || 0}</strong>
                    </article>
                    <article>
                      <span>Enviado a Calidad</span>
                      <strong>{formatDateTime(selectedCertificate.sent_to_quality_at)} · {selectedCertificate.sent_to_quality_by_id ? `#${selectedCertificate.sent_to_quality_by_id}` : 'Sistema'}</strong>
                    </article>
                    <article>
                      <span>Revisión de Calidad</span>
                      <strong>{formatDateTime(selectedCertificate.quality_reviewed_at)} · {selectedCertificate.quality_reviewed_by_id ? `#${selectedCertificate.quality_reviewed_by_id}` : 'Pendiente'}</strong>
                    </article>
                    <article>
                      <span>Autenticación</span>
                      <strong>{formatDateTime(selectedCertificate.authenticated_pdf_generated_at)} · {selectedCertificate.authenticated_by_id ? `#${selectedCertificate.authenticated_by_id}` : 'Pendiente'}</strong>
                    </article>
                    <article className="form-field--wide">
                      <span>Notas</span>
                      <strong>{selectedCertificate.notes || '-'}</strong>
                    </article>
                  </div>
                  {selectedMasterReadiness?.warnings?.length ? <div className="match-details-panel"><strong>Advertencias no bloqueantes</strong><ul>{selectedMasterReadiness.warnings.map((item) => <li key={item.field}>{item.field}: {item.status}</li>)}</ul></div> : null}
                  {selectedMasterReadiness?.mismatches?.length ? <div className="form-error"><strong>Diferencias bloqueantes</strong><ul>{selectedMasterReadiness.mismatches.map((item) => <li key={item.field}>{item.field}: {item.status}</li>)}</ul></div> : null}
                </section>

                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <p>Acciones de Calidad</p>
                    <h3>Control de aprobacion</h3>
                  </div>
                  <div className="toolbar-actions quality-actions">
                    <button className="table-button table-button--primary" disabled={!selectedMasterReadiness?.identified} onClick={() => handleDownloadMaster(selectedCertificate)} type="button">Descargar Master XLSX</button>
                    <button
                      className="table-button table-button--primary"
                      disabled={Boolean(loadingAction) || !canTransition(selectedCertificate, 'quality_approved') || !selectedMasterReadiness?.ready}
                      onClick={() => handleQualityAction('quality-approve', 'Aprobar Master')}
                      type="button"
                    >
                      {loadingAction === 'quality-approveAprobar Master' ? 'Procesando...' : 'Aprobar Master'}
                    </button>
                    <button
                      className="table-button"
                      disabled={Boolean(loadingAction) || !['ready_for_quality', 'quality_review', 'match_validated', 'quality_approved'].includes(selectedCertificate.status)}
                      onClick={() => { setCorrectionRequest(selectedCertificate); setCorrectionReason(''); }}
                      type="button"
                    >
                      Rechazar / regresar a Captura
                    </button>
                    <button
                      className="table-button table-button--primary"
                      disabled={Boolean(loadingAction) || !['quality_approved', 'approved'].includes(selectedCertificate.status)}
                      onClick={() => runQualityOperation('authenticate', () => authenticateCertificate(selectedCertificate.id), 'Certificado autenticado y enviado a Certificados')}
                      type="button"
                    >
                      {loadingAction === 'authenticate' ? 'Autenticando...' : 'Autenticar / Sellar'}
                    </button>
                  </div>
                </section>
              </>
            ) : null}

            {detailTab === 'field-sheet' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Hoja de Campo</p>
                  <h3>Base tecnica para calidad</h3>
                </div>
                {selectedFieldSheet ? (
                  <div className="field-sheet-form-grid read-only-grid">
                    <article>
                      <span>Condicion inicial</span>
                      <strong>{selectedFieldSheet.initial_condition || '-'}</strong>
                    </article>
                    <article>
                      <span>Condicion final</span>
                      <strong>{selectedFieldSheet.final_condition || '-'}</strong>
                    </article>
                    <article>
                      <span>Patron</span>
                      <strong>{selectedFieldSheet.pattern_used || '-'}</strong>
                    </article>
                    <article>
                      <span>Resultados</span>
                      <strong>{selectedFieldSheet.results || '-'}</strong>
                    </article>
                    <article>
                      <span>Observaciones</span>
                      <strong>{selectedFieldSheet.observations || '-'}</strong>
                    </article>
                    <article>
                      <span>Metodo</span>
                      <strong>{selectedFieldSheet.method || '-'}</strong>
                    </article>
                    <article className="form-field--wide">
                      <span>Condiciones ambientales</span>
                      <strong>{selectedFieldSheet.environmental_conditions || '-'}</strong>
                    </article>
                  </div>
                ) : (
                  <div className="clients-empty">No se encontro la hoja de campo vinculada.</div>
                )}
              </section>
            ) : null}

            {detailTab === 'equipment' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Equipo</p>
                  <h3>Contexto del instrumento</h3>
                </div>
                {selectedEquipment ? (
                  <div className="quotation-commercial-grid service-order-info-grid">
                    <article>
                      <span>Nombre</span>
                      <strong>{selectedEquipment.name || '-'}</strong>
                    </article>
                    <article>
                      <span>Marca</span>
                      <strong>{selectedEquipment.brand || '-'}</strong>
                    </article>
                    <article>
                      <span>Modelo</span>
                      <strong>{selectedEquipment.model || '-'}</strong>
                    </article>
                    <article>
                      <span>Serie</span>
                      <strong>{selectedEquipment.serial_number || '-'}</strong>
                    </article>
                    <article>
                      <span>Estado</span>
                      <strong>{equipmentStatusLabels[selectedEquipment.status] ?? selectedEquipment.status}</strong>
                    </article>
                  </div>
                ) : (
                  <div className="clients-empty">No se encontro el equipo vinculado.</div>
                )}
              </section>
            ) : null}

            {detailTab === 'history' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Historial</p>
                  <h3>Audit logs del certificado</h3>
                </div>
                {auditLogs.length ? (
                  <div className="clients-table audit-log-table">
                    <div className="clients-table__head">
                      <span>Fecha</span>
                      <span>Usuario</span>
                      <span>Accion</span>
                      <span>Estado anterior</span>
                      <span>Estado nuevo</span>
                    </div>
                    {auditLogs.map((log) => (
                      <div className="clients-table__row" key={log.id}>
                        <span>{formatDateTime(log.created_at)}</span>
                        <span>{log.user_name || (log.user_id ? `#${log.user_id}` : 'Sistema')}</span>
                        <span>{formatAuditAction(log.action)}</span>
                        <span>{getAuditStatusValue(log.previous_values)}</span>
                        <span>{getAuditStatusValue(log.new_values)}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="clients-empty">Sin audit logs expuestos para este certificado.</div>
                )}
              </section>
            ) : null}
              </>
            )}
          </section>
        </div>
      ) : null}

      {correctionRequest ? (
        <div className="modal-backdrop" role="presentation">
          <section aria-modal="true" className="client-modal confirm-dialog" role="dialog">
            <div className="section-heading confirm-dialog__header"><div><p>Corrección requerida</p><h2>Describe las correcciones del Master XLSX</h2></div></div>
            <div className="confirm-dialog__body">
              <p>El comentario se conservará en el historial. La hoja vinculada no cambiará de estado.</p>
              <textarea autoFocus className="form-textarea" onChange={(event) => setCorrectionReason(event.target.value)} placeholder="Describe los errores y la corrección requerida" rows={5} value={correctionReason} />
            </div>
            <div className="confirm-dialog__actions">
              <button className="confirm-dialog__cancel" disabled={Boolean(loadingAction)} onClick={() => { setCorrectionRequest(null); setCorrectionReason(''); }} type="button">Cancelar</button>
              <button className="confirm-dialog__confirm" disabled={Boolean(loadingAction) || !correctionReason.trim()} onClick={confirmCorrectionRequest} type="button">{loadingAction ? 'Procesando...' : 'Regresar a Captura'}</button>
            </div>
          </section>
        </div>
      ) : null}

      <ConfirmDialog
        cancelText={confirmDialog?.cancelText}
        confirmText={confirmDialog?.confirmText}
        isLoading={Boolean(confirmDialog?.isConfirming)}
        isOpen={Boolean(confirmDialog)}
        message={confirmDialog?.message}
        onClose={closeConfirm}
        onConfirm={handleConfirm}
        title={confirmDialog?.title}
        variant={confirmDialog?.variant}
      />
    </section>
  );
}



export default QualityPage;
