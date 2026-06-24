import { ShieldCheck } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import {
  equipmentStatusLabels,
  certificateStatusLabels,
  certificateTypeLabels,
  certificateTransitions,
  qualityTabs
} from '../constants/statuses.js';
import {
  changeCertificateStatus,
  getCertificate,
  listAuditLogs,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders
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
    if (activeTab === 'pending') {
      return certificates.filter((certificate) => ['generated', 'quality_review'].includes(certificate.status));
    }
    if (activeTab === 'review') {
      return certificates.filter((certificate) => certificate.status === 'quality_review');
    }
    if (activeTab === 'approved') {
      return certificates.filter((certificate) => certificate.status === 'approved');
    }
    if (activeTab === 'released') {
      return certificates.filter((certificate) => certificate.status === 'released');
    }
    if (activeTab === 'suspended') {
      return certificates.filter((certificate) => certificate.status === 'suspended');
    }
    return certificates;
  }, [activeTab, certificates]);

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
          <span>Revision formal, aprobacion y liberacion controlada de certificados.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary" aria-label="Resumen de calidad">
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.filter((certificate) => ['generated', 'quality_review'].includes(certificate.status)).length}</strong>
          <span>Pendientes calidad</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.filter((certificate) => certificate.status === 'approved').length}</strong>
          <span>Aprobados</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.filter((certificate) => certificate.status === 'released').length}</strong>
          <span>Liberados</span>
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
        <div className="clients-table quality-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>Folio</span>
            <span>Cliente</span>
            <span>Orden de Servicio</span>
            <span>Equipo</span>
            <span>Tecnico</span>
            <span>Fecha</span>
            <span>Estado</span>
          </div>
          {isLoading ? (
            <div className="clients-empty">Cargando certificados para calidad...</div>
          ) : displayedCertificates.length ? (
            displayedCertificates.map((certificate) => {
              const context = getCertificateContext(certificate);
              return (
                <button className="clients-table__row quotation-row-button" key={certificate.id} onClick={() => openQualityDetail(certificate)} type="button">
                  <span className="certificate-folio">{certificate.folio}</span>
                  <span>{getClientDisplayName(context.client)}</span>
                  <span>{context.order?.folio || '-'}</span>
                  <span>{context.item?.name || '-'}</span>
                  <span>{getTechnicianLabel(context.order)}</span>
                  <span>{formatDate(certificate.issued_on) !== '-' ? formatDate(certificate.issued_on) : formatDateTime(certificate.created_at)}</span>
                  <span>
                    <mark className={`quotation-status status-${certificate.status}`}>
                      {certificateStatusLabels[certificate.status] ?? certificate.status}
                    </mark>
                  </span>
                </button>
              );
            })
          ) : (
            <div className="clients-empty">No hay certificados en esta vista de calidad.</div>
          )}
        </div>
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
                      <strong>{selectedCertificate.folio}</strong>
                    </article>
                    <article>
                      <span>Tipo</span>
                      <strong>{certificateTypeLabels[selectedCertificate.certificate_type] ?? selectedCertificate.certificate_type}</strong>
                    </article>
                    <article>
                      <span>Estado</span>
                      <strong>{certificateStatusLabels[selectedCertificate.status] ?? selectedCertificate.status}</strong>
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
                    <button
                      className="table-button table-button--primary"
                      disabled={Boolean(loadingAction) || !canTransition(selectedCertificate, 'approved')}
                      onClick={() => handleQualityAction('approve', 'Aprobar')}
                      type="button"
                    >
                      {loadingAction === 'approveAprobar' ? 'Procesando...' : 'Aprobar'}
                    </button>
                    <button
                      className="table-button"
                      disabled={Boolean(loadingAction) || !['generated', 'quality_review'].includes(selectedCertificate.status)}
                      onClick={() => handleQualityAction('request-correction', 'Solicitar correccion', 'Correccion solicitada por calidad')}
                      type="button"
                    >
                      {loadingAction === 'request-correctionSolicitar correccion' ? 'Procesando...' : 'Solicitar correccion'}
                    </button>
                    <button
                      className="table-button"
                      disabled={Boolean(loadingAction) || !canTransition(selectedCertificate, 'suspended')}
                      onClick={() => handleQualityAction('suspend', 'Suspender')}
                      type="button"
                    >
                      {loadingAction === 'suspendSuspender' ? 'Procesando...' : 'Suspender'}
                    </button>
                    <button
                      className="table-button table-button--primary"
                      disabled={Boolean(loadingAction) || !canTransition(selectedCertificate, 'released')}
                      onClick={() => handleQualityAction('release', 'Liberar')}
                      type="button"
                    >
                      {loadingAction === 'releaseLiberar' ? 'Procesando...' : 'Liberar'}
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
