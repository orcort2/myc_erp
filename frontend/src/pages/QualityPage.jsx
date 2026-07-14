import { ShieldCheck } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

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
  downloadOriginalCertificatePdf,
  getCertificate,
  listAuditLogs,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders,
  manualAcceptCertificateMatch,
  validateCertificatePdfMatch
} from '../services/api.js';
import { formatDate, formatDateTime, getClientDisplayName } from '../utils/formatters.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';

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
  const [activeTab, setActiveTab] = useState('pending');
  const [selectedCertificate, setSelectedCertificate] = useState(null);
  const [detailTab, setDetailTab] = useState('certificate');
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadingAction, setLoadingAction] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [correctionRequest, setCorrectionRequest] = useState(null);
  const [correctionReason, setCorrectionReason] = useState('');
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

  const displayedCertificates = useMemo(() => {
    const qualityFlowCertificates = certificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated', 'quality_approved'].includes(certificate.status));
    if (activeTab === 'pending') {
      return qualityFlowCertificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated'].includes(certificate.status));
    }
    if (activeTab === 'review') {
      return qualityFlowCertificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated'].includes(certificate.status));
    }
    if (activeTab === 'approved') {
      return qualityFlowCertificates.filter((certificate) => certificate.status === 'quality_approved');
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
      const [certificatesResult, ordersResult, equipmentResult, fieldSheetsResult, clientsResult] = await Promise.all([
        listCertificates(),
        listServiceOrders(),
        listEquipment(),
        listFieldSheets(),
        listClients()
      ]);
      setCertificates(Array.isArray(certificatesResult) ? certificatesResult : []);
      setServiceOrders(Array.isArray(ordersResult) ? ordersResult : []);
      setEquipment(Array.isArray(equipmentResult) ? equipmentResult : []);
      setFieldSheets(Array.isArray(fieldSheetsResult) ? fieldSheetsResult : []);
      setClients(Array.isArray(clientsResult) ? clientsResult : []);
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

  async function openQualityDetail(certificate) {
    setError('');
    setNotice('');
    try {
      const [freshCertificate, logs] = await Promise.all([
        getCertificate(certificate.id),
        listAuditLogs({ entity: 'certificates', entity_id: certificate.id, limit: 100 })
      ]);
      setSelectedCertificate(freshCertificate);
      setAuditLogs(Array.isArray(logs) ? logs : []);
      setDetailTab('certificate');
      setIsDetailOpen(true);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function closeQualityDetail() {
    setSelectedCertificate(null);
    setAuditLogs([]);
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
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setLoadingAction('');
        }
      }
    });
  }

  async function runQualityOperation(actionKey, operation, successMessage, { closeAfter = false } = {}) {
    if (!selectedCertificate) return;
    setLoadingAction(actionKey);
    setError('');
    setNotice('');
    try {
      const updated = await operation();
      setCertificates((current) => current.map((item) => item.id === updated.id ? updated : item));
      setNotice(successMessage);
      if (closeAfter) closeQualityDetail();
      else setSelectedCertificate(updated);
      await loadQualityData();
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
      closeQualityDetail();
      setNotice(`Certificado ${updated.folio} regresado a Captura para corrección`);
      await loadQualityData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoadingAction('');
    }
  }

  async function openOriginalPdf(certificate) {
    const pdfWindow = window.open('', '_blank');
    if (!pdfWindow) {
      setError('El navegador bloqueó la vista del PDF. Permite ventanas emergentes.');
      return;
    }
    try {
      const { blob } = await downloadOriginalCertificatePdf(certificate.id, certificate.final_pdf_original_filename);
      const url = URL.createObjectURL(blob);
      pdfWindow.location.replace(url);
      window.setTimeout(() => URL.revokeObjectURL(url), 5 * 60 * 1000);
    } catch (requestError) {
      pdfWindow.close();
      setError(requestError.message);
    }
  }

  const selectedContext = selectedCertificate ? getCertificateContext(selectedCertificate) : {};
  const selectedOrder = selectedContext.order;
  const selectedEquipment = selectedContext.item;
  const selectedFieldSheet = selectedContext.sheet;

  return (
    <section className="module-workspace quality-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <ShieldCheck size={28} />
        </span>
        <div>
          <p>Supervision transversal</p>
          <h1>Calidad</h1>
          <span>Revisión del PDF, validación, aprobación y autenticación de certificados.</span>
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
          <strong>{isLoading ? '-' : certificates.filter((certificate) => certificate.status === 'quality_approved').length}</strong>
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
            getGroupState={(items) => items.every((item) => item.status === 'quality_approved') ? { label: 'APROBADA', tone: 'approved' } : { label: 'EN REVISIÓN', tone: 'quality_review' }}
            items={displayedCertificates}
            orders={serviceOrders}
            renderItem={(certificate) => {
              const context = getCertificateContext(certificate);
              return <button className="flow-certificate-card flow-certificate-card--button" key={certificate.id} onClick={() => openQualityDetail(certificate)} type="button"><div className="flow-certificate-card__title"><div><span>Certificado</span><strong>{certificate.folio}</strong></div><mark className={`quotation-status status-${certificate.status}`}>{certificateStatusLabels[certificate.status] ?? certificate.status}</mark></div><dl><div><dt>Cliente</dt><dd>{getClientDisplayName(context.client)}</dd></div><div><dt>Equipo</dt><dd>{context.item?.name || '-'}</dd></div><div><dt>Técnico</dt><dd>{getTechnicianLabel(context.order)}</dd></div><div><dt>Fecha</dt><dd>{formatDate(certificate.issued_on) !== '-' ? formatDate(certificate.issued_on) : formatDateTime(certificate.created_at)}</dd></div><div><dt>PDF</dt><dd>{certificate.final_pdf_original_filename || 'Pendiente'}</dd></div><div><dt>Match</dt><dd>{certificate.match_status || 'pending'}</dd></div></dl></button>;
            }}
          />
        )}
      </section>

      {isDetailOpen && selectedCertificate ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-detail-modal field-sheet-modal certificate-detail-modal" aria-modal="true" role="dialog">
            <div className="quotation-detail-header">
              <div>
                <p>Revision de Calidad</p>
                <h2 className="certificate-folio-heading">{selectedCertificate.folio}</h2>
                <span>{getClientDisplayName(selectedContext.client)} · {selectedOrder?.folio || '-'}</span>
              </div>
              <mark className={`quotation-status quotation-status--large status-${selectedCertificate.status}`}>
                {certificateStatusLabels[selectedCertificate.status] ?? selectedCertificate.status}
              </mark>
              <button className="icon-text-button" onClick={closeQualityDetail} type="button">
                Cerrar
              </button>
            </div>

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
                      <span>PDF</span>
                      <strong>{selectedCertificate.final_pdf_original_filename || 'Pendiente'}</strong>
                    </article>
                    <article>
                      <span>Matching</span>
                      <strong>{selectedCertificate.match_status || 'pending'}</strong>
                    </article>
                    <article className="form-field--wide">
                      <span>Notas</span>
                      <strong>{selectedCertificate.notes || '-'}</strong>
                    </article>
                  </div>
                </section>

                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <p>Acciones de Calidad</p>
                    <h3>Control de aprobacion</h3>
                  </div>
                  <div className="toolbar-actions quality-actions">
                    <button className="table-button table-button--primary" disabled={!selectedCertificate.final_pdf_path} onClick={() => openOriginalPdf(selectedCertificate)} type="button">Revisar PDF</button>
                    <button className="table-button" disabled={Boolean(loadingAction) || !['ready_for_quality', 'quality_review'].includes(selectedCertificate.status)} onClick={() => runQualityOperation('validate-match', () => validateCertificatePdfMatch(selectedCertificate.id), 'Match validado por Calidad')} type="button">{loadingAction === 'validate-match' ? 'Validando...' : 'Validar match'}</button>
                    <button className="table-button" disabled={Boolean(loadingAction) || selectedCertificate.status !== 'match_validated' || !['mismatch', 'warning'].includes(selectedCertificate.match_status)} onClick={() => runQualityOperation('manual-match', () => manualAcceptCertificateMatch(selectedCertificate.id, 'Aceptado manualmente por Calidad'), 'Match aceptado manualmente')} type="button">Aceptar match manual</button>
                    <button
                      className="table-button table-button--primary"
                      disabled={Boolean(loadingAction) || !canTransition(selectedCertificate, 'quality_approved') || !['matched', 'warning', 'manual_accepted'].includes(selectedCertificate.match_status)}
                      onClick={() => handleQualityAction('quality-approve', 'Aprobar calidad')}
                      type="button"
                    >
                      {loadingAction === 'quality-approveAprobar calidad' ? 'Procesando...' : 'Aprobar calidad'}
                    </button>
                    <button
                      className="table-button"
                      disabled={Boolean(loadingAction) || !['ready_for_quality', 'quality_review', 'match_validated', 'quality_approved'].includes(selectedCertificate.status)}
                      onClick={() => { setCorrectionRequest(selectedCertificate); setCorrectionReason(''); }}
                      type="button"
                    >
                      Regresar a Captura
                    </button>
                    <button
                      className="table-button table-button--primary"
                      disabled={Boolean(loadingAction) || selectedCertificate.status !== 'quality_approved' || !selectedCertificate.final_pdf_path || !['matched', 'warning', 'manual_accepted'].includes(selectedCertificate.match_status)}
                      onClick={() => runQualityOperation('authenticate', () => authenticateCertificate(selectedCertificate.id), 'Certificado autenticado y enviado a Certificados', { closeAfter: true })}
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
          </section>
        </div>
      ) : null}

      {correctionRequest ? (
        <div className="modal-backdrop" role="presentation">
          <section aria-modal="true" className="client-modal confirm-dialog" role="dialog">
            <div className="section-heading confirm-dialog__header"><div><p>Corrección requerida</p><h2>Marca los errores del PDF</h2></div></div>
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
