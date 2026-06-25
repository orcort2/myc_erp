import { BadgeCheck } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';

import { emptyCertificateForm } from '../constants/forms.js';
import {
  certificateReadyEquipmentStatuses,
  certificateReadyFieldSheetStatuses,
  certificateStatusLabels,
  certificateTypeLabels,
  equipmentStatusLabels,
  fieldSheetStatusLabels
} from '../constants/statuses.js';
import {
  createCertificate,
  downloadFieldSheetPdf,
  getFieldSheetPdfUrl,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listServiceOrders
} from '../services/api.js';
import { formatDateTime, getClientDisplayName } from '../utils/formatters.js';

function FieldSheetsPage() {
  const [fieldSheets, setFieldSheets] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [serviceOrders, setServiceOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [certificateForm, setCertificateForm] = useState(emptyCertificateForm);
  const [selectedSheet, setSelectedSheet] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
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

  const activeCertificatesByFieldSheetId = useMemo(() => {
    const map = new Map();
    certificates
      .filter((certificate) => certificate.is_active !== false)
      .forEach((certificate) => {
        map.set(certificate.field_sheet_id, certificate);
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
      return fieldSheets.filter((sheet) => ['completed', 'under_review', 'approved'].includes(sheet.status));
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
        const [fieldSheetsResult, equipmentResult, ordersResult, clientsResult, certificatesResult] = await Promise.all([
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
    const certificate = activeCertificatesByFieldSheetId.get(sheet.id);
    return { item, order, client, certificate };
  }

  function openFieldSheetPdf(fieldSheetId, mode = 'view') {
    const pdfWindow = window.open(getFieldSheetPdfUrl(fieldSheetId), '_blank', 'noopener,noreferrer');
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

  function canCreateCertificate(sheet) {
    const { item, certificate } = getSheetContext(sheet);
    return (
      !certificate &&
      certificateReadyFieldSheetStatuses.has(sheet.status) &&
      certificateReadyEquipmentStatuses.has(item?.status)
    );
  }

  function openCreateCertificate(sheet) {
    if (!canCreateCertificate(sheet)) {
      setError('La hoja seleccionada no esta lista para certificado o ya tiene uno activo.');
      return;
    }
    setSelectedSheet(sheet);
    setCertificateForm(emptyCertificateForm);
    setIsCreateModalOpen(true);
    setError('');
  }

  function closeCreateCertificate() {
    setSelectedSheet(null);
    setCertificateForm(emptyCertificateForm);
    setIsCreateModalOpen(false);
  }

  async function handleCreateCertificate(event) {
    event.preventDefault();
    if (!selectedSheet) return;
    const { item, order } = getSheetContext(selectedSheet);
    if (!item || !order) {
      setError('La hoja no tiene contexto suficiente para crear certificado.');
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const created = await createCertificate({
        service_order_id: order.id,
        equipment_id: item.id,
        field_sheet_id: selectedSheet.id,
        certificate_type: certificateForm.certificateType,
        notes: certificateForm.notes.trim() || null
      });
      setCertificates((current) => [created, ...current]);
      setNotice(`Certificado ${created.folio} creado`);
      closeCreateCertificate();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
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
          <span>Consulta de plantillas, estados documentales, PDF tecnico y enlace a certificados.</span>
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
          <strong>{isLoading ? '-' : fieldSheets.filter((sheet) => ['completed', 'under_review', 'approved'].includes(sheet.status)).length}</strong>
          <span>Listas para certificado</span>
        </div>
        <div className="operations-band__metric">
          <strong>{isLoading ? '-' : activeCertificatesByFieldSheetId.size}</strong>
          <span>Con certificado</span>
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
            <span>Plantilla</span>
            <span>Estado</span>
            <span>Certificado</span>
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
                  <span>{sheet.template_key === 'electrica' ? 'Electrica' : 'General'}</span>
                  <span>
                    <mark className={`quotation-status status-${sheet.status}`}>
                      {fieldSheetStatusLabels[sheet.status] ?? sheet.status}
                    </mark>
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
                  <span>{formatDateTime(sheet.updated_at)}</span>
                  <span className="clients-table__actions">
                    <button className="table-button" onClick={() => openFieldSheetPdf(sheet.id, 'view')} type="button">
                      Ver PDF
                    </button>
                    <button className="table-button" onClick={() => handleDownloadPdf(sheet)} type="button">
                      Descargar
                    </button>
                    <button className="table-button" onClick={() => openFieldSheetPdf(sheet.id, 'print')} type="button">
                      Imprimir
                    </button>
                    <button className="table-button table-button--primary" disabled={!canCreateCertificate(sheet)} onClick={() => openCreateCertificate(sheet)} type="button">
                      {certificate ? 'Certificado creado' : 'Crear certificado'}
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

      {isCreateModalOpen && selectedSheet ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal certificate-create-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Nuevo certificado</p>
                <h2>Crear desde hoja #{selectedSheet.id}</h2>
              </div>
            </div>
            <form className="client-form client-form--modal" onSubmit={handleCreateCertificate}>
              <label>
                Tipo de certificado
                <select
                  value={certificateForm.certificateType}
                  onChange={(event) => setCertificateForm((current) => ({ ...current, certificateType: event.target.value }))}
                >
                  <option value="acreditado">{certificateTypeLabels.acreditado}</option>
                  <option value="trazable">{certificateTypeLabels.trazable}</option>
                </select>
              </label>
              <label className="form-field--wide">
                Notas
                <textarea
                  rows={4}
                  value={certificateForm.notes}
                  onChange={(event) => setCertificateForm((current) => ({ ...current, notes: event.target.value }))}
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
    </section>
  );
}

export default FieldSheetsPage;
