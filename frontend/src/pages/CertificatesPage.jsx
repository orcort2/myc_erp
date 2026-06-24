import React, { useEffect, useMemo, useState } from 'react';
import { FileCheck2, X } from 'lucide-react';


import ConfirmDialog from '../components/ConfirmDialog.jsx';
import { emptyCertificateForm } from '../constants/forms.js';
import {
  equipmentStatusLabels,
  fieldSheetStatusLabels,
  certificateStatusLabels,
  certificateTypeLabels,
  certificateTabs,
  certificateActions,
  certificateTransitions,
  certificateReadyFieldSheetStatuses,
  certificateReadyEquipmentStatuses
} from '../constants/statuses.js';
import {
  changeCertificateStatus,
  createCertificate,
  deleteCertificate,
  getCertificate,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders,
  updateCertificate
} from '../services/api.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import { formatDate, formatDateTime, getClientDisplayName } from '../utils/formatters.js';

function CertificatesPage() {
  const [certificates, setCertificates] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [clients, setClients] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [selectedCertificate, setSelectedCertificate] = useState(null);
  const [certificateDetailTab, setCertificateDetailTab] = useState('info');
  const [certificateForm, setCertificateForm] = useState(emptyCertificateForm);
  const [certificateSourceSheet, setCertificateSourceSheet] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
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

  const activeCertificatesByFieldSheetId = useMemo(() => {
    const map = new Map();
    certificates
      .filter((certificate) => certificate.is_active !== false)
      .forEach((certificate) => {
        map.set(certificate.field_sheet_id, certificate);
      });
    return map;
  }, [certificates]);

  const pendingFieldSheets = useMemo(
    () =>
      fieldSheets.filter((sheet) => {
        const item = equipmentById.get(sheet.equipment_id);
        return (
          sheet.is_active !== false &&
          certificateReadyFieldSheetStatuses.has(sheet.status) &&
          certificateReadyEquipmentStatuses.has(item?.status) &&
          !activeCertificatesByFieldSheetId.has(sheet.id)
        );
      }),
    [activeCertificatesByFieldSheetId, equipmentById, fieldSheets]
  );

  const displayedCertificates = useMemo(() => {
    if (activeTab === 'review') {
      return certificates.filter((certificate) => certificate.status === 'quality_review');
    }
    if (activeTab === 'approved') {
      return certificates.filter((certificate) => certificate.status === 'approved');
    }
    if (activeTab === 'released') {
      return certificates.filter((certificate) => certificate.status === 'released');
    }
    return certificates;
  }, [activeTab, certificates]);

  async function loadCertificateData() {
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
    loadCertificateData();
  }, []);

  function getCertificateContext(certificate) {
    const order = ordersById.get(certificate.service_order_id);
    const item = equipmentById.get(certificate.equipment_id);
    const sheet = fieldSheetsById.get(certificate.field_sheet_id);
    const client = order ? clientsById.get(order.client_id) : null;
    return { client, item, order, sheet };
  }

  function getSheetContext(sheet) {
    const item = equipmentById.get(sheet.equipment_id);
    const order = item ? ordersById.get(item.service_order_id) : null;
    const client = order ? clientsById.get(order.client_id) : null;
    return { client, item, order };
  }

  function getCertificateCreationError(sheet) {
    const { item, order } = getSheetContext(sheet);
    if (!order) {
      return 'La hoja no tiene orden de servicio disponible.';
    }
    if (!certificateReadyFieldSheetStatuses.has(sheet.status)) {
      return 'La hoja debe estar completada, en revision o aprobada.';
    }
    if (!certificateReadyEquipmentStatuses.has(item?.status)) {
      return 'El equipo debe estar calibrado o etiquetado.';
    }
    if (activeCertificatesByFieldSheetId.has(sheet.id)) {
      return 'La hoja de campo ya tiene un certificado activo.';
    }
    return '';
  }

  function openCreateCertificate(sheet) {
    const validationError = getCertificateCreationError(sheet);
    if (validationError) {
      setError(validationError);
      return;
    }
    setCertificateSourceSheet(sheet);
    setCertificateForm(emptyCertificateForm);
    setIsCreateModalOpen(true);
    setError('');
    setNotice('');
  }

  function closeCreateCertificate() {
    setIsCreateModalOpen(false);
    setCertificateSourceSheet(null);
    setCertificateForm(emptyCertificateForm);
    setError('');
  }

  async function handleCreateCertificate(event) {
    event.preventDefault();
    if (!certificateSourceSheet) return;
    const { item, order } = getSheetContext(certificateSourceSheet);
    const validationError = getCertificateCreationError(certificateSourceSheet);
    if (validationError) {
      setError(validationError);
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const created = await createCertificate({
        service_order_id: order.id,
        equipment_id: item.id,
        field_sheet_id: certificateSourceSheet.id,
        certificate_type: certificateForm.certificateType,
        notes: certificateForm.notes.trim() || null
      });
      setNotice(`Certificado ${created.folio} creado`);
      closeCreateCertificate();
      await loadCertificateData();
      await openCertificateDetail(created);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function openCertificateDetail(certificate) {
    setError('');
    setNotice('');
    try {
      const fresh = await getCertificate(certificate.id);
      setSelectedCertificate(fresh);
      setCertificateForm({
        certificateType: fresh.certificate_type ?? 'trazable',
        notes: fresh.notes ?? ''
      });
      setCertificateDetailTab('info');
      setIsDetailOpen(true);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function closeCertificateDetail() {
    setIsDetailOpen(false);
    setSelectedCertificate(null);
    setCertificateForm(emptyCertificateForm);
    setCertificateDetailTab('info');
    setError('');
  }

  function updateCertificateForm(field, value) {
    setCertificateForm((current) => ({ ...current, [field]: value }));
  }

  async function saveCertificateNotes() {
    if (!selectedCertificate) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await updateCertificate(selectedCertificate.id, {
        notes: certificateForm.notes.trim() || null
      });
      setSelectedCertificate(updated);
      setCertificates((current) =>
        current.map((certificate) => (certificate.id === updated.id ? updated : certificate))
      );
      setNotice('Notas del certificado guardadas');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function isCertificateActionAllowed(certificate, action) {
    return certificateTransitions[certificate.status]?.has(action.nextStatus) ?? false;
  }

  async function handleCertificateAction(action) {
    if (!selectedCertificate) return;
    const nextLabel = certificateStatusLabels[action.nextStatus] ?? action.nextStatus;
    openConfirm({
      title: 'Confirmar cambio de certificado',
      message: `El certificado ${selectedCertificate.folio} cambiará a ${nextLabel}.`,
      confirmText: `Cambiar a ${nextLabel}`,
      variant: 'danger',
      onConfirm: async () => {
        setLoadingAction(action.key);
        setError('');
        setNotice('');
        try {
          const updated = await changeCertificateStatus(selectedCertificate.id, action.key);
          setSelectedCertificate(updated);
          setCertificates((current) =>
            current.map((certificate) => (certificate.id === updated.id ? updated : certificate))
          );
          setNotice(`Certificado ${updated.folio} actualizado a ${certificateStatusLabels[updated.status]}`);
          await loadCertificateData();
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setLoadingAction('');
        }
      }
    });
  }

  async function handleDeleteCertificateRecord() {
    if (!selectedCertificate) return;
    openConfirm({
      title: 'Dar de baja certificado',
      message: `Esta acción dará de baja el certificado ${selectedCertificate.folio}.\nNo se eliminará físicamente y es una acción administrativa distinta de suspender o cambiar estado.`,
      confirmText: 'Dar de baja certificado',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        try {
          await deleteCertificate(selectedCertificate.id);
          closeCertificateDetail();
          setNotice('Certificado dado de baja');
          await loadCertificateData();
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  const selectedContext = selectedCertificate ? getCertificateContext(selectedCertificate) : {};
  const selectedSheet = selectedContext.sheet;

  return (
    <section className="module-workspace certificates-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <FileCheck2 size={28} />
        </span>
        <div>
          <p>Calidad documental</p>
          <h1>Certificados</h1>
          <span>Generacion, revision, aprobacion y liberacion de certificados por equipo.</span>
        </div>
      </div>

      {error ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="operations-band certificates-summary" aria-label="Resumen de certificados">
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.length}</strong>
          <span>Total certificados</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.filter((certificate) => certificate.status === 'quality_review').length}</strong>
          <span>En revision</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : certificates.filter((certificate) => certificate.status === 'released').length}</strong>
          <span>Liberados</span>
        </div>
      </section>

      <div className="module-tabs" role="tablist" aria-label="Navegacion de certificados">
        {certificateTabs.map((tab) => (
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

      {activeTab === 'pending' ? (
        <section className="clients-list-panel">
          <div className="section-heading">
            <div>
              <p>Hojas listas</p>
              <h2>{isLoading ? 'Cargando...' : `${pendingFieldSheets.length} pendientes`}</h2>
            </div>
          </div>
          <div className="clients-table pending-certificates-table" aria-busy={isLoading}>
            <div className="clients-table__head">
              <span>Cliente</span>
              <span>Orden</span>
              <span>Equipo</span>
              <span>Hoja</span>
              <span>Estado hoja</span>
              <span>Estado equipo</span>
              <span>Acciones</span>
            </div>
            {isLoading ? (
              <div className="clients-empty">Cargando hojas disponibles...</div>
            ) : pendingFieldSheets.length ? (
              pendingFieldSheets.map((sheet) => {
                const { client, item, order } = getSheetContext(sheet);
                return (
                  <div className="clients-table__row" key={sheet.id}>
                    <span>{getClientDisplayName(client)}</span>
                    <span>{order?.folio || '-'}</span>
                    <span>{item?.name || '-'}</span>
                    <span>#{sheet.id}</span>
                    <span>
                      <mark className={`quotation-status status-${sheet.status}`}>
                        {fieldSheetStatusLabels[sheet.status] ?? sheet.status}
                      </mark>
                    </span>
                    <span>
                      <mark className={`quotation-status status-${item?.status}`}>
                        {equipmentStatusLabels[item?.status] ?? item?.status ?? '-'}
                      </mark>
                    </span>
                    <span className="clients-table__actions">
                      <button className="table-button table-button--primary" onClick={() => openCreateCertificate(sheet)} type="button">
                        Crear certificado
                      </button>
                    </span>
                  </div>
                );
              })
            ) : (
              <div className="clients-empty">No hay hojas de campo pendientes de certificado.</div>
            )}
          </div>
        </section>
      ) : (
        <section className="clients-list-panel">
          <div className="section-heading">
            <div>
              <p>Listado documental</p>
              <h2>{isLoading ? 'Cargando...' : `${displayedCertificates.length} certificados`}</h2>
            </div>
          </div>
          <div className="clients-table certificates-table" aria-busy={isLoading}>
            <div className="clients-table__head">
              <span>Folio</span>
              <span>Cliente</span>
              <span>Orden</span>
              <span>Equipo</span>
              <span>Tipo</span>
              <span>Estado</span>
              <span>Emision</span>
              <span>Liberacion</span>
              <span>Acciones</span>
            </div>
            {isLoading ? (
              <div className="clients-empty">Cargando certificados...</div>
            ) : displayedCertificates.length ? (
              displayedCertificates.map((certificate) => {
                const { client, item, order } = getCertificateContext(certificate);
                return (
                  <button className="clients-table__row quotation-row-button" key={certificate.id} onClick={() => openCertificateDetail(certificate)} type="button">
                    <span className="certificate-folio">{certificate.folio}</span>
                    <span>{getClientDisplayName(client)}</span>
                    <span>{order?.folio || '-'}</span>
                    <span>{item?.name || '-'}</span>
                    <span>{certificateTypeLabels[certificate.certificate_type] ?? certificate.certificate_type}</span>
                    <span>
                      <mark className={`quotation-status status-${certificate.status}`}>
                        {certificateStatusLabels[certificate.status] ?? certificate.status}
                      </mark>
                    </span>
                    <span>{formatDate(certificate.issued_on)}</span>
                    <span>{formatDate(certificate.released_on)}</span>
                    <span>Ver ficha</span>
                  </button>
                );
              })
            ) : (
              <div className="clients-empty">No hay certificados en esta vista.</div>
            )}
          </div>
        </section>
      )}

      {isCreateModalOpen && certificateSourceSheet ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal certificate-create-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Nuevo certificado</p>
                <h2>Crear desde hoja #{certificateSourceSheet.id}</h2>
              </div>
            </div>
            <form className="client-form client-form--modal" onSubmit={handleCreateCertificate}>
              <label>
                Tipo de certificado
                <select
                  onChange={(event) => updateCertificateForm('certificateType', event.target.value)}
                  value={certificateForm.certificateType}
                >
                  <option value="acreditado">Acreditado</option>
                  <option value="trazable">Trazable</option>
                </select>
              </label>
              <label className="form-field--wide">
                Notas
                <textarea
                  onChange={(event) => updateCertificateForm('notes', event.target.value)}
                  rows={4}
                  value={certificateForm.notes}
                />
              </label>
              <div className="client-form__actions client-form__actions--modal">
                <button className="icon-text-button" disabled={isSaving} onClick={closeCreateCertificate} type="button">
                  Cancelar
                </button>
                <button className="primary-button" disabled={isSaving} type="submit">
                  {isSaving ? 'Creando...' : 'Crear certificado'}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {isDetailOpen && selectedCertificate ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-detail-modal field-sheet-modal certificate-detail-modal" aria-modal="true" role="dialog">
            <div className="quotation-detail-header">
              <div>
                <p>Certificado</p>
                <h2 className="certificate-folio-heading">{selectedCertificate.folio}</h2>
                <span>
                  {certificateTypeLabels[selectedCertificate.certificate_type] ?? selectedCertificate.certificate_type}
                  {' · '}
                  {getClientDisplayName(selectedContext.client)}
                </span>
              </div>
              <mark className={`quotation-status quotation-status--large status-${selectedCertificate.status}`}>
                {certificateStatusLabels[selectedCertificate.status] ?? selectedCertificate.status}
              </mark>
              <button className="icon-text-button" onClick={closeCertificateDetail} type="button">
                Cerrar
              </button>
            </div>

            <div className="client-modal-tabs quotation-detail-tabs" role="tablist" aria-label="Detalle de certificado">
              {[
                ['info', 'Informacion'],
                ['technical', 'Datos tecnicos'],
                ['quality', 'Calidad'],
                ['history', 'Historial']
              ].map(([key, label]) => (
                <button
                  aria-selected={certificateDetailTab === key}
                  className={certificateDetailTab === key ? 'client-modal-tab is-active' : 'client-modal-tab'}
                  key={key}
                  onClick={() => setCertificateDetailTab(key)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>

            {certificateDetailTab === 'info' ? (
              <>
                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <p>Informacion documental</p>
                    <h3>Ficha de certificado</h3>
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
                      <span>Cliente</span>
                      <strong>{getClientDisplayName(selectedContext.client)}</strong>
                    </article>
                    <article>
                      <span>Orden de Servicio</span>
                      <strong>{selectedContext.order?.folio || '-'}</strong>
                    </article>
                    <article>
                      <span>Equipo</span>
                      <strong>{selectedContext.item?.name || '-'}</strong>
                    </article>
                    <article>
                      <span>Hoja de Campo</span>
                      <strong>#{selectedCertificate.field_sheet_id}</strong>
                    </article>
                    <article>
                      <span>Fecha emision</span>
                      <strong>{formatDate(selectedCertificate.issued_on)}</strong>
                    </article>
                    <article>
                      <span>Fecha liberacion</span>
                      <strong>{formatDate(selectedCertificate.released_on)}</strong>
                    </article>
                    <article>
                      <span>Estado</span>
                      <strong>{certificateStatusLabels[selectedCertificate.status] ?? selectedCertificate.status}</strong>
                    </article>
                  </div>
                </section>

                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <p>Notas</p>
                    <h3>Observaciones documentales</h3>
                  </div>
                  <label className="quotation-notes-field">
                    <textarea
                      disabled={['released', 'cancelled'].includes(selectedCertificate.status)}
                      onChange={(event) => updateCertificateForm('notes', event.target.value)}
                      rows={4}
                      value={certificateForm.notes}
                    />
                  </label>
                  <div className="quotation-detail-save">
                    <span>Las notas quedan bloqueadas al liberar o cancelar.</span>
                    <button className="primary-button" disabled={isSaving || ['released', 'cancelled'].includes(selectedCertificate.status)} onClick={saveCertificateNotes} type="button">
                      {isSaving ? 'Guardando...' : 'Guardar notas'}
                    </button>
                  </div>
                </section>
              </>
            ) : null}

            {certificateDetailTab === 'technical' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Datos tecnicos</p>
                  <h3>Hoja de campo en lectura</h3>
                </div>
                {selectedSheet ? (
                  <div className="field-sheet-form-grid read-only-grid">
                    <article>
                      <span>Condicion inicial</span>
                      <strong>{selectedSheet.initial_condition || '-'}</strong>
                    </article>
                    <article>
                      <span>Condicion final</span>
                      <strong>{selectedSheet.final_condition || '-'}</strong>
                    </article>
                    <article>
                      <span>Patron utilizado</span>
                      <strong>{selectedSheet.pattern_used || '-'}</strong>
                    </article>
                    <article>
                      <span>Resultados</span>
                      <strong>{selectedSheet.results || '-'}</strong>
                    </article>
                    <article>
                      <span>Observaciones</span>
                      <strong>{selectedSheet.observations || '-'}</strong>
                    </article>
                    <article>
                      <span>Evidencia / notas</span>
                      <strong>{selectedSheet.evidence_notes || '-'}</strong>
                    </article>
                    <article>
                      <span>Metodo</span>
                      <strong>{selectedSheet.method || '-'}</strong>
                    </article>
                    <article>
                      <span>Condiciones ambientales</span>
                      <strong>{selectedSheet.environmental_conditions || '-'}</strong>
                    </article>
                    <article className="form-field--wide">
                      <span>Notas del tecnico</span>
                      <strong>{selectedSheet.technician_notes || '-'}</strong>
                    </article>
                  </div>
                ) : (
                  <div className="clients-empty">No se encontro la hoja de campo vinculada.</div>
                )}
              </section>
            ) : null}

            {certificateDetailTab === 'quality' ? (
              <>
                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <p>Calidad</p>
                    <h3>Flujo de certificado</h3>
                  </div>
                  <div className="quotation-actions">
                    {certificateActions.map((action) => (
                      <button
                        className={action.key === 'release' ? 'table-button table-button--primary' : 'table-button'}
                        disabled={Boolean(loadingAction) || !isCertificateActionAllowed(selectedCertificate, action)}
                        key={action.key}
                        onClick={() => handleCertificateAction(action)}
                        type="button"
                      >
                        {loadingAction === action.key ? 'Procesando...' : action.label}
                      </button>
                    ))}
                  </div>
                </section>

                <section className="quotation-section danger-zone">
                  <div className="danger-zone__copy">
                    <p>Zona de baja</p>
                    <span>Esta acción da de baja el certificado sin borrarlo físicamente. No sustituye suspender ni cambiar estado.</span>
                  </div>
                  <button className="table-button table-button--danger" onClick={handleDeleteCertificateRecord} type="button">
                    Dar de baja certificado
                  </button>
                </section>
              </>
            ) : null}

            {certificateDetailTab === 'history' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Historial</p>
                  <h3>Eventos documentales</h3>
                </div>
                <div className="quotation-history-list">
                  <article>
                    <strong>Certificado creado</strong>
                    <span>{formatDateTime(selectedCertificate.created_at)}</span>
                  </article>
                  <article>
                    <strong>Ultima actualizacion</strong>
                    <span>{formatDateTime(selectedCertificate.updated_at)}</span>
                  </article>
                  <article>
                    <strong>Estado actual</strong>
                    <span>{certificateStatusLabels[selectedCertificate.status] ?? selectedCertificate.status}</span>
                  </article>
                  <article>
                    <strong>Orden de Servicio origen</strong>
                    <span>{selectedContext.order?.folio || '-'}</span>
                  </article>
                  <article>
                    <strong>Equipo origen</strong>
                    <span>{selectedContext.item?.name || '-'}</span>
                  </article>
                  <article>
                    <strong>Hoja de Campo origen</strong>
                    <span>#{selectedCertificate.field_sheet_id}</span>
                  </article>
                </div>
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



export default CertificatesPage;
