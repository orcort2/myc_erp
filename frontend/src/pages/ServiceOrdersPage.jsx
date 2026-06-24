import { ClipboardList, X } from 'lucide-react';
import React, { useEffect, useMemo, useState } from 'react';
import mycLogo from '../assets/myc-logo.png';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import {
  emptyServiceOrderForm,
  emptyEquipmentForm,
  emptyFieldSheetForm
} from '../constants/forms.js';
import {
  serviceOrderStatusLabels,
  serviceOrderTransitions,
  serviceOrderActions,
  equipmentStatusLabels,
  equipmentTransitions,
  equipmentActions,
  fieldSheetStatusLabels,
  certificateReadyFieldSheetStatuses,
  certificateReadyEquipmentStatuses
} from '../constants/statuses.js';
import {
  changeEquipmentStatus,
  changeServiceOrderStatus,
  completeFieldSheet,
  createCertificate,
  createEquipment,
  createFieldSheet,
  deleteEquipment,
  deleteFieldSheet,
  deleteServiceOrder,
  getFieldSheet,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listQuotations,
  listServiceOrders,
  reviewFieldSheet,
  updateEquipment,
  updateFieldSheet,
  updateServiceOrder
} from '../services/api.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import {
  fieldSheetToForm,
  buildFieldSheetPayload,
  getFieldSheetCompletionErrors
} from '../utils/fieldSheets.js';
import { formatDate, getClientDisplayName } from '../utils/formatters.js';

function ServiceOrdersPage() {
  const [serviceOrders, setServiceOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedEquipmentForSheet, setSelectedEquipmentForSheet] = useState(null);
  const [selectedFieldSheet, setSelectedFieldSheet] = useState(null);
  const [orderForm, setOrderForm] = useState(emptyServiceOrderForm);
  const [equipmentForm, setEquipmentForm] = useState(emptyEquipmentForm);
  const [fieldSheetForm, setFieldSheetForm] = useState(emptyFieldSheetForm);
  const [fieldSheetCertificateType, setFieldSheetCertificateType] = useState('trazable');
  const [editingEquipmentId, setEditingEquipmentId] = useState(null);
  const [activeTab, setActiveTab] = useState('info');
  const [fieldSheetTab, setFieldSheetTab] = useState('info');
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isEquipmentModalOpen, setIsEquipmentModalOpen] = useState(false);
  const [isFieldSheetModalOpen, setIsFieldSheetModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const { confirmDialog, openConfirm, closeConfirm, handleConfirm } = useConfirmDialog();

  const clientsById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients]
  );

  const quotationsById = useMemo(
    () => new Map(quotations.map((quotation) => [quotation.id, quotation])),
    [quotations]
  );

  const selectedEquipment = useMemo(
    () => equipment.filter((item) => item.service_order_id === selectedOrder?.id),
    [equipment, selectedOrder]
  );

  const fieldSheetsByEquipmentId = useMemo(() => {
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

  const activeCertificatesByFieldSheetId = useMemo(() => {
    const map = new Map();
    certificates
      .filter((certificate) => certificate.is_active !== false)
      .forEach((certificate) => {
        map.set(certificate.field_sheet_id, certificate);
      });
    return map;
  }, [certificates]);

  async function loadServiceOrderData() {
    setError('');
    setIsLoading(true);
    try {
      const [ordersResult, clientsResult, quotationsResult, equipmentResult, fieldSheetResult, certificatesResult] = await Promise.all([
        listServiceOrders(),
        listClients(),
        listQuotations(),
        listEquipment(),
        listFieldSheets(),
        listCertificates()
      ]);
      setServiceOrders(Array.isArray(ordersResult) ? ordersResult : []);
      setClients(Array.isArray(clientsResult) ? clientsResult : []);
      setQuotations(Array.isArray(quotationsResult) ? quotationsResult : []);
      setEquipment(Array.isArray(equipmentResult) ? equipmentResult : []);
      setFieldSheets(Array.isArray(fieldSheetResult) ? fieldSheetResult : []);
      setCertificates(Array.isArray(certificatesResult) ? certificatesResult : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadServiceOrderData();
  }, []);

  function getOrderEquipmentCount(order) {
    return equipment.filter((item) => item.service_order_id === order.id && item.is_active !== false).length;
  }

  function openOrderDetail(order) {
    setSelectedOrder(order);
    setOrderForm({
      agendaDate: order.agenda_date ?? '',
      serviceDate: order.service_date ?? '',
      technicianId: order.technician_id ? String(order.technician_id) : '',
      requiresPayment: order.requires_payment !== false,
      notes: order.notes ?? ''
    });
    setActiveTab('info');
    setIsDetailOpen(true);
    setError('');
    setNotice('');
  }

  function closeOrderDetail() {
    setIsDetailOpen(false);
    setSelectedOrder(null);
    setSelectedEquipmentForSheet(null);
    setSelectedFieldSheet(null);
    setOrderForm(emptyServiceOrderForm);
    setEquipmentForm(emptyEquipmentForm);
    setFieldSheetForm(emptyFieldSheetForm);
    setEditingEquipmentId(null);
    setActiveTab('info');
    setFieldSheetTab('info');
    setError('');
  }

  function updateOrderForm(field, value) {
    setOrderForm((current) => ({ ...current, [field]: value }));
  }

  function updateEquipmentForm(field, value) {
    setEquipmentForm((current) => ({ ...current, [field]: value }));
  }

  async function handleOrderSubmit(event) {
    event.preventDefault();
    if (!selectedOrder) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await updateServiceOrder(selectedOrder.id, {
        agenda_date: orderForm.agendaDate || null,
        service_date: orderForm.serviceDate || null,
        technician_id: orderForm.technicianId ? Number(orderForm.technicianId) : null,
        requires_payment: Boolean(orderForm.requiresPayment),
        notes: orderForm.notes.trim() || null
      });
      setSelectedOrder(updated);
      setNotice(`Orden ${updated.folio} actualizada`);
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function isServiceOrderActionAllowed(order, action) {
    return serviceOrderTransitions[order.status]?.has(action.nextStatus) ?? false;
  }

  async function handleServiceOrderStatus(order, action) {
    const nextLabel = serviceOrderStatusLabels[action.nextStatus] ?? action.nextStatus;
    openConfirm({
      title: 'Confirmar cambio de estado',
      message: `La orden ${order.folio} cambiará a ${nextLabel}.`,
      confirmText: `Cambiar a ${nextLabel}`,
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        try {
          const updated = await changeServiceOrderStatus(order.id, action.key);
          setSelectedOrder(updated);
          setNotice(`Orden ${updated.folio} actualizada a ${serviceOrderStatusLabels[updated.status]}`);
          await loadServiceOrderData();
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  function openEquipmentModal(item = null) {
    setError('');
    setNotice('');
    if (item) {
      setEditingEquipmentId(item.id);
      setEquipmentForm({
        name: item.name ?? '',
        brand: item.brand ?? '',
        model: item.model ?? '',
        serialNumber: item.serial_number ?? '',
        internalId: item.internal_id ?? '',
        rangeOrCapacity: item.range_or_capacity ?? '',
        initialCondition: item.initial_condition ?? '',
        notes: item.notes ?? ''
      });
    } else {
      setEditingEquipmentId(null);
      setEquipmentForm(emptyEquipmentForm);
    }
    setIsEquipmentModalOpen(true);
  }

  function closeEquipmentModal() {
    setIsEquipmentModalOpen(false);
    setEditingEquipmentId(null);
    setEquipmentForm(emptyEquipmentForm);
    setError('');
  }

  async function handleEquipmentSubmit(event) {
    event.preventDefault();
    if (!selectedOrder) return;
    if (!equipmentForm.name.trim()) {
      setError('Captura el nombre del equipo.');
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const payload = {
        service_order_id: selectedOrder.id,
        name: equipmentForm.name.trim(),
        brand: equipmentForm.brand.trim() || null,
        model: equipmentForm.model.trim() || null,
        serial_number: equipmentForm.serialNumber.trim() || null,
        internal_id: equipmentForm.internalId.trim() || null,
        range_or_capacity: equipmentForm.rangeOrCapacity.trim() || null,
        initial_condition: equipmentForm.initialCondition.trim() || null,
        notes: equipmentForm.notes.trim() || null
      };
      const saved = editingEquipmentId
        ? await updateEquipment(editingEquipmentId, payload)
        : await createEquipment(payload);
      setNotice(editingEquipmentId ? 'Equipo actualizado' : 'Equipo agregado');
      setEquipment((current) =>
        editingEquipmentId
          ? current.map((item) => (item.id === editingEquipmentId ? saved : item))
          : [saved, ...current]
      );
      closeEquipmentModal();
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDeleteEquipment(item) {
    openConfirm({
      title: 'Dar de baja equipo',
      message: `Esta acción dará de baja el equipo ${item.name}.\nNo se eliminará físicamente y se recalcularán los contadores de la orden.`,
      confirmText: 'Dar de baja equipo',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        try {
          await deleteEquipment(item.id);
          setEquipment((current) => current.filter((equipmentItem) => equipmentItem.id !== item.id));
          setNotice('Equipo dado de baja');
          await loadServiceOrderData();
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  function isEquipmentActionAllowed(item, action) {
    return equipmentTransitions[item.status]?.has(action.nextStatus) ?? false;
  }

  async function handleEquipmentStatus(item, action) {
    const nextLabel = equipmentStatusLabels[action.nextStatus] ?? action.nextStatus;
    openConfirm({
      title: 'Confirmar cambio de equipo',
      message: `El equipo ${item.name} cambiará a ${nextLabel}.`,
      confirmText: `Cambiar a ${nextLabel}`,
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        try {
          const updated = await changeEquipmentStatus(item.id, action.key);
          setEquipment((current) =>
            current.map((equipmentItem) => (equipmentItem.id === updated.id ? updated : equipmentItem))
          );
          setNotice(`Equipo actualizado a ${equipmentStatusLabels[updated.status]}`);
          await loadServiceOrderData();
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  async function openFieldSheetForEquipment(item) {
    setError('');
    setNotice('');
    setSelectedEquipmentForSheet(item);
    try {
      const existing = fieldSheetsByEquipmentId.get(item.id);
      const sheet = existing
        ? await getFieldSheet(existing.id)
        : await createFieldSheet({ equipment_id: item.id });
      setSelectedFieldSheet(sheet);
      setFieldSheetForm(fieldSheetToForm(sheet));
      setFieldSheetCertificateType('trazable');
      setFieldSheetTab('info');
      setIsFieldSheetModalOpen(true);
      if (!existing) {
        setFieldSheets((current) => [sheet, ...current]);
        setNotice(`Hoja de campo creada para ${item.name}`);
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function closeFieldSheetModal() {
    setIsFieldSheetModalOpen(false);
    setSelectedEquipmentForSheet(null);
    setSelectedFieldSheet(null);
    setFieldSheetForm(emptyFieldSheetForm);
    setFieldSheetCertificateType('trazable');
    setFieldSheetTab('info');
    setError('');
  }

  function updateFieldSheetForm(field, value) {
    setFieldSheetForm((current) => ({ ...current, [field]: value }));
  }

  async function saveFieldSheet() {
    if (!selectedFieldSheet) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await updateFieldSheet(
        selectedFieldSheet.id,
        buildFieldSheetPayload(fieldSheetForm)
      );
      setSelectedFieldSheet(updated);
      setFieldSheetForm(fieldSheetToForm(updated));
      setFieldSheets((current) =>
        current.map((sheet) => (sheet.id === updated.id ? updated : sheet))
      );
      setNotice('Hoja de campo guardada');
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function completeCurrentFieldSheet() {
    if (!selectedFieldSheet) return;
    const missing = getFieldSheetCompletionErrors(fieldSheetForm);
    if (missing.length) {
      setError(`No se puede completar. Faltan: ${missing.join(', ')}.`);
      setFieldSheetTab('technical');
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const saved = await updateFieldSheet(selectedFieldSheet.id, buildFieldSheetPayload(fieldSheetForm));
      const completed = await completeFieldSheet(saved.id);
      setSelectedFieldSheet(completed);
      setFieldSheetForm(fieldSheetToForm(completed));
      setFieldSheets((current) =>
        current.map((sheet) => (sheet.id === completed.id ? completed : sheet))
      );
      setNotice('Hoja de campo completada. El equipo paso a calibrado.');
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function reviewCurrentFieldSheet() {
    if (!selectedFieldSheet) return;
    if (selectedFieldSheet.status !== 'completed') {
      setError('Solo una hoja completada puede enviarse a revision.');
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const reviewed = await reviewFieldSheet(selectedFieldSheet.id);
      setSelectedFieldSheet(reviewed);
      setFieldSheetForm(fieldSheetToForm(reviewed));
      setFieldSheets((current) =>
        current.map((sheet) => (sheet.id === reviewed.id ? reviewed : sheet))
      );
      setNotice('Hoja de campo enviada a revision');
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function createCertificateFromCurrentFieldSheet() {
    if (!selectedOrder || !selectedEquipmentForSheet || !selectedFieldSheet) return;
    if (!certificateReadyFieldSheetStatuses.has(selectedFieldSheet.status)) {
      setError('La hoja debe estar completada, en revision o aprobada para crear certificado.');
      return;
    }
    if (!certificateReadyEquipmentStatuses.has(selectedEquipmentForSheet.status)) {
      setError('El equipo debe estar calibrado o etiquetado para crear certificado.');
      return;
    }
    if (activeCertificatesByFieldSheetId.has(selectedFieldSheet.id)) {
      setError('Esta hoja de campo ya tiene un certificado activo.');
      return;
    }
    if (!['acreditado', 'trazable'].includes(fieldSheetCertificateType)) {
      setError('Selecciona un tipo de certificado valido.');
      return;
    }
    openConfirm({
      title: 'Crear certificado',
      message: `Se creará un certificado ${fieldSheetCertificateType} para ${selectedEquipmentForSheet.name}.`,
      confirmText: 'Crear certificado',
      onConfirm: async () => {
        setIsSaving(true);
        setError('');
        setNotice('');
        try {
          const created = await createCertificate({
            service_order_id: selectedOrder.id,
            equipment_id: selectedEquipmentForSheet.id,
            field_sheet_id: selectedFieldSheet.id,
            certificate_type: fieldSheetCertificateType
          });
          setCertificates((current) => [created, ...current]);
          setNotice(`Certificado ${created.folio} creado`);
          await loadServiceOrderData();
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setIsSaving(false);
        }
      }
    });
  }

  async function handleDeleteServiceOrder() {
    if (!selectedOrder) return;
    openConfirm({
      title: 'Dar de baja orden de servicio',
      message: `Esta acción dará de baja la orden ${selectedOrder.folio}.\nNo se eliminará físicamente y puede afectar equipos, hojas y certificados relacionados.`,
      confirmText: 'Dar de baja orden',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        try {
          await deleteServiceOrder(selectedOrder.id);
          closeOrderDetail();
          setNotice('Orden de servicio dada de baja');
          await loadServiceOrderData();
        } catch (requestError) {
          setError(requestError.message);
        }
      }
    });
  }

  async function handleDeleteFieldSheet() {
    if (!selectedFieldSheet) return;
    openConfirm({
      title: 'Dar de baja hoja de campo',
      message: `Esta acción dará de baja la hoja de campo #${selectedFieldSheet.id}.\nNo se eliminará físicamente y puede afectar certificados relacionados.`,
      confirmText: 'Dar de baja hoja',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        setIsSaving(true);
        try {
          await deleteFieldSheet(selectedFieldSheet.id);
          closeFieldSheetModal();
          setNotice('Hoja de campo dada de baja');
          await loadServiceOrderData();
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setIsSaving(false);
        }
      }
    });
  }

  return (
    <section className="module-workspace service-orders-workspace">
      <div className="module-workspace__hero clients-hero">
        <span className="module-workspace__icon">
          <ClipboardList size={28} />
        </span>
        <div>
          <p>Operacion MYC SYSTEM</p>
          <h1>Ordenes de Servicio</h1>
          <span>Seguimiento operativo desde cotizacion aceptada hasta liberacion del servicio.</span>
        </div>
      </div>

      {error && !isEquipmentModalOpen ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Listado operativo</p>
            <h2>{isLoading ? 'Cargando...' : `${serviceOrders.length} ordenes`}</h2>
          </div>
        </div>

        <div className="clients-table service-orders-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>Folio</span>
            <span>Cliente</span>
            <span>Cotizacion</span>
            <span>Estado</span>
            <span>Agenda</span>
            <span>Servicio</span>
            <span>Equipos</span>
            <span>Tecnico</span>
            <span>Acciones</span>
          </div>

          {isLoading ? (
            <div className="clients-empty">Cargando ordenes de servicio...</div>
          ) : serviceOrders.length ? (
            serviceOrders.map((order) => {
              const client = clientsById.get(order.client_id);
              const quotation = quotationsById.get(order.quotation_id);
              return (
                <button className="clients-table__row quotation-row-button" key={order.id} onClick={() => openOrderDetail(order)} type="button">
                  <span>{order.folio}</span>
                  <span>{getClientDisplayName(client)}</span>
                  <span>{quotation?.folio || (order.quotation_id ? `#${order.quotation_id}` : '-')}</span>
                  <span>
                    <mark className={`quotation-status status-${order.status}`}>
                      {serviceOrderStatusLabels[order.status] ?? order.status}
                    </mark>
                  </span>
                  <span>{formatDate(order.agenda_date)}</span>
                  <span>{formatDate(order.service_date)}</span>
                  <span>{order.completed_equipment ?? 0}/{order.total_equipment || getOrderEquipmentCount(order)}</span>
                  <span>{order.technician_id ? `#${order.technician_id}` : 'Por asignar'}</span>
                  <span>Ver ficha</span>
                </button>
              );
            })
          ) : (
            <div className="clients-empty">Todavia no hay ordenes de servicio registradas.</div>
          )}
        </div>
      </section>

      {isDetailOpen && selectedOrder ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-detail-modal service-order-modal" aria-modal="true" role="dialog">
            <div className="quotation-detail-header">
              <div>
                <p>Orden de servicio</p>
                <h2>{selectedOrder.folio}</h2>
                <span>{getClientDisplayName(clientsById.get(selectedOrder.client_id))}</span>
              </div>
              <mark className={`quotation-status quotation-status--large status-${selectedOrder.status}`}>
                {serviceOrderStatusLabels[selectedOrder.status] ?? selectedOrder.status}
              </mark>
              <button className="icon-text-button" onClick={closeOrderDetail} type="button">
                Cerrar
              </button>
            </div>

            <div className="client-modal-tabs quotation-detail-tabs" role="tablist" aria-label="Detalle de orden de servicio">
              {[
                ['info', 'Informacion'],
                ['equipment', 'Equipos'],
                ['field-sheet', 'Hoja de campo'],
                ['history', 'Historial']
              ].map(([key, label]) => (
                <button
                  aria-selected={activeTab === key}
                  className={activeTab === key ? 'client-modal-tab is-active' : 'client-modal-tab'}
                  key={key}
                  onClick={() => setActiveTab(key)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>

            {activeTab === 'info' ? (
              <>
                <form className="quotation-detail-form" onSubmit={handleOrderSubmit}>
                  <section className="quotation-section">
                    <div className="quotation-section__title">
                      <p>Informacion operativa</p>
                      <h3>Ficha editable</h3>
                    </div>
                    <div className="quotation-commercial-grid service-order-info-grid">
                      <article>
                        <span>Cliente</span>
                        <strong>{getClientDisplayName(clientsById.get(selectedOrder.client_id))}</strong>
                      </article>
                      <article>
                        <span>Cotizacion origen</span>
                        <strong>{quotationsById.get(selectedOrder.quotation_id)?.folio || '-'}</strong>
                      </article>
                      <article>
                        <span>Asesor</span>
                        <strong>{selectedOrder.advisor_id ? `#${selectedOrder.advisor_id}` : 'Sin asesor'}</strong>
                      </article>
                      <label>
                        Tecnico
                        <input
                          onChange={(event) => updateOrderForm('technicianId', event.target.value)}
                          placeholder="ID de usuario tecnico"
                          type="number"
                          value={orderForm.technicianId}
                        />
                      </label>
                      <label>
                        Fecha agenda
                        <input onChange={(event) => updateOrderForm('agendaDate', event.target.value)} type="date" value={orderForm.agendaDate} />
                      </label>
                      <label>
                        Fecha servicio
                        <input onChange={(event) => updateOrderForm('serviceDate', event.target.value)} type="date" value={orderForm.serviceDate} />
                      </label>
                      <article>
                        <span>Total de equipos</span>
                        <strong>{selectedOrder.total_equipment || selectedEquipment.length}</strong>
                      </article>
                      <article>
                        <span>Equipos completados</span>
                        <strong>{selectedOrder.completed_equipment ?? 0}</strong>
                      </article>
                      <label className="service-order-checkbox">
                        <input
                          checked={orderForm.requiresPayment}
                          onChange={(event) => updateOrderForm('requiresPayment', event.target.checked)}
                          type="checkbox"
                        />
                        Requiere pago
                      </label>
                    </div>
                  </section>

                  <section className="quotation-section">
                    <div className="quotation-section__title">
                      <p>Notas</p>
                      <h3>Observaciones operativas</h3>
                    </div>
                    <label className="quotation-notes-field">
                      <textarea
                        onChange={(event) => updateOrderForm('notes', event.target.value)}
                        placeholder="Sin notas registradas."
                        rows={4}
                        value={orderForm.notes}
                      />
                    </label>
                  </section>

                  <div className="quotation-detail-save">
                    <span>Guarda agenda, servicio, tecnico, pago y notas.</span>
                    <button className="primary-button" disabled={isSaving} type="submit">
                      {isSaving ? 'Guardando...' : 'Guardar cambios'}
                    </button>
                  </div>
                </form>

                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <p>Acciones de estado</p>
                    <h3>Flujo operativo</h3>
                  </div>
                  <div className="quotation-actions">
                    {serviceOrderActions.map((action) => (
                      <button
                        className="table-button"
                        disabled={!isServiceOrderActionAllowed(selectedOrder, action)}
                        key={action.key}
                        onClick={() => handleServiceOrderStatus(selectedOrder, action)}
                        type="button"
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                </section>

                <section className="danger-zone">
                  <div className="danger-zone__copy">
                    <p>Zona de baja</p>
                    <span>Esta acción dará de baja la orden de servicio. No se eliminará físicamente y el backend validará dependencias activas.</span>
                  </div>
                  <div className="toolbar-actions">
                    <button className="table-button table-button--danger" onClick={handleDeleteServiceOrder} type="button">
                      Dar de baja orden
                    </button>
                  </div>
                </section>
              </>
            ) : null}

            {activeTab === 'equipment' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>Equipos de la orden</p>
                    <h3>{selectedEquipment.length} equipos</h3>
                  </div>
                  <button className="primary-button" onClick={() => openEquipmentModal()} type="button">
                    + Agregar equipo
                  </button>
                </div>
                <div className="clients-table equipment-table">
                  <div className="clients-table__head">
                    <span>Nombre</span>
                    <span>Marca</span>
                    <span>Modelo</span>
                    <span>Serie</span>
                    <span>ID interno</span>
                    <span>Rango</span>
                    <span>Estado</span>
                    <span>Acciones</span>
                  </div>
                  {selectedEquipment.length ? (
                    selectedEquipment.map((item) => (
                      <div className="clients-table__row" key={item.id}>
                        <span>{item.name}</span>
                        <span>{item.brand || '-'}</span>
                        <span>{item.model || '-'}</span>
                        <span>{item.serial_number || '-'}</span>
                        <span>{item.internal_id || '-'}</span>
                        <span>{item.range_or_capacity || '-'}</span>
                        <span>
                          <mark className={`quotation-status status-${item.status}`}>
                            {equipmentStatusLabels[item.status] ?? item.status}
                          </mark>
                        </span>
                        <span className="clients-table__actions">
                          <button className="table-button" onClick={() => openEquipmentModal(item)} type="button">
                            Editar
                          </button>
                          {equipmentActions.map((action) => (
                            <button
                              className="table-button"
                              disabled={!isEquipmentActionAllowed(item, action)}
                              key={action.key}
                              onClick={() => handleEquipmentStatus(item, action)}
                              type="button"
                            >
                              {action.label}
                            </button>
                          ))}
                          <button className="table-button table-button--primary" onClick={() => openFieldSheetForEquipment(item)} type="button">
                            Abrir hoja
                          </button>
                          <button className="table-button" onClick={() => handleDeleteEquipment(item)} type="button">
                            Eliminar
                          </button>
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="clients-empty">Todavia no hay equipos vinculados a esta orden.</div>
                  )}
                </div>
              </section>
            ) : null}

            {activeTab === 'field-sheet' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Hoja de campo</p>
                  <h3>Preparacion tecnica</h3>
                </div>
                {selectedEquipment.length ? (
                  <div className="field-sheet-prep-list">
                    {selectedEquipment.map((item) => (
                      <article className="glass-card-mini" key={item.id}>
                        <strong>{item.name}</strong>
                        <span>
                          {fieldSheetsByEquipmentId.has(item.id)
                            ? `Hoja ${fieldSheetsByEquipmentId.get(item.id).id} · ${fieldSheetStatusLabels[fieldSheetsByEquipmentId.get(item.id).status] ?? fieldSheetsByEquipmentId.get(item.id).status}`
                            : `${item.brand || '-'} · ${item.model || '-'} · ${item.serial_number || 'Sin serie'}`}
                        </span>
                        <button className="table-button" onClick={() => openFieldSheetForEquipment(item)} type="button">
                          {fieldSheetsByEquipmentId.has(item.id) ? 'Abrir hoja de campo' : 'Crear hoja de campo'}
                        </button>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="clients-empty">Agrega equipos para preparar hojas de campo.</div>
                )}
              </section>
            ) : null}

            {activeTab === 'history' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Historial</p>
                  <h3>Eventos de orden</h3>
                </div>
                <div className="quotation-history-list">
                  <article>
                    <strong>Orden creada</strong>
                    <span>{new Date(selectedOrder.created_at).toLocaleString('es-MX')}</span>
                  </article>
                  <article>
                    <strong>Ultima actualizacion</strong>
                    <span>{new Date(selectedOrder.updated_at).toLocaleString('es-MX')}</span>
                  </article>
                  <article>
                    <strong>Estado actual</strong>
                    <span>{serviceOrderStatusLabels[selectedOrder.status] ?? selectedOrder.status}</span>
                  </article>
                  <article>
                    <strong>Cotizacion origen</strong>
                    <span>{quotationsById.get(selectedOrder.quotation_id)?.folio || '-'}</span>
                  </article>
                </div>
              </section>
            ) : null}
          </section>
        </div>
      ) : null}

      {isEquipmentModalOpen && selectedOrder ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal" aria-modal="true" role="dialog">
            <div className="section-heading">
              <div>
                <p>Equipos</p>
                <h2>{editingEquipmentId ? 'Editar equipo' : 'Agregar equipo'}</h2>
              </div>
            </div>
            {error ? <div className="form-error dashboard-error">{error}</div> : null}
            <form className="client-form client-form--modal" onSubmit={handleEquipmentSubmit}>
              <label>
                Nombre
                <input onChange={(event) => updateEquipmentForm('name', event.target.value)} required type="text" value={equipmentForm.name} />
              </label>
              <label>
                Marca
                <input onChange={(event) => updateEquipmentForm('brand', event.target.value)} type="text" value={equipmentForm.brand} />
              </label>
              <label>
                Modelo
                <input onChange={(event) => updateEquipmentForm('model', event.target.value)} type="text" value={equipmentForm.model} />
              </label>
              <label>
                Serie
                <input onChange={(event) => updateEquipmentForm('serialNumber', event.target.value)} type="text" value={equipmentForm.serialNumber} />
              </label>
              <label>
                ID interno
                <input onChange={(event) => updateEquipmentForm('internalId', event.target.value)} type="text" value={equipmentForm.internalId} />
              </label>
              <label>
                Rango / capacidad
                <input onChange={(event) => updateEquipmentForm('rangeOrCapacity', event.target.value)} type="text" value={equipmentForm.rangeOrCapacity} />
              </label>
              <label className="form-field--wide">
                Condicion inicial
                <textarea onChange={(event) => updateEquipmentForm('initialCondition', event.target.value)} rows={3} value={equipmentForm.initialCondition} />
              </label>
              <label className="form-field--wide">
                Notas
                <textarea onChange={(event) => updateEquipmentForm('notes', event.target.value)} rows={3} value={equipmentForm.notes} />
              </label>
              <div className="client-form__actions client-form__actions--modal">
                <button className="icon-text-button" disabled={isSaving} onClick={closeEquipmentModal} type="button">
                  Cancelar
                </button>
                <button className="primary-button" disabled={isSaving} type="submit">
                  {isSaving ? 'Guardando...' : editingEquipmentId ? 'Guardar cambios' : 'Agregar equipo'}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}

      {isFieldSheetModalOpen && selectedOrder && selectedEquipmentForSheet && selectedFieldSheet ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-detail-modal field-sheet-modal" aria-modal="true" role="dialog">
            <div className="quotation-detail-header">
              <div>
                <p>Hoja de campo</p>
                <h2>{selectedEquipmentForSheet.name}</h2>
                <span>{selectedOrder.folio} · {getClientDisplayName(clientsById.get(selectedOrder.client_id))}</span>
              </div>
              <mark className={`quotation-status quotation-status--large status-${selectedFieldSheet.status}`}>
                {fieldSheetStatusLabels[selectedFieldSheet.status] ?? selectedFieldSheet.status}
              </mark>
              <button className="icon-text-button" onClick={closeFieldSheetModal} type="button">
                Cerrar
              </button>
            </div>

            <div className="client-modal-tabs quotation-detail-tabs" role="tablist" aria-label="Hoja de campo">
              {[
                ['info', 'Informacion'],
                ['technical', 'Datos tecnicos'],
                ['history', 'Historial']
              ].map(([key, label]) => (
                <button
                  aria-selected={fieldSheetTab === key}
                  className={fieldSheetTab === key ? 'client-modal-tab is-active' : 'client-modal-tab'}
                  key={key}
                  onClick={() => setFieldSheetTab(key)}
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>

            {fieldSheetTab === 'info' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Informacion tecnica</p>
                  <h3>Contexto de la hoja</h3>
                </div>
                <div className="quotation-commercial-grid service-order-info-grid">
                  <article>
                    <span>Orden de Servicio</span>
                    <strong>{selectedOrder.folio}</strong>
                  </article>
                  <article>
                    <span>Cliente</span>
                    <strong>{getClientDisplayName(clientsById.get(selectedOrder.client_id))}</strong>
                  </article>
                  <article>
                    <span>Equipo</span>
                    <strong>{selectedEquipmentForSheet.name}</strong>
                  </article>
                  <article>
                    <span>Marca</span>
                    <strong>{selectedEquipmentForSheet.brand || '-'}</strong>
                  </article>
                  <article>
                    <span>Modelo</span>
                    <strong>{selectedEquipmentForSheet.model || '-'}</strong>
                  </article>
                  <article>
                    <span>Serie</span>
                    <strong>{selectedEquipmentForSheet.serial_number || '-'}</strong>
                  </article>
                  <article>
                    <span>Estado actual</span>
                    <strong>{fieldSheetStatusLabels[selectedFieldSheet.status] ?? selectedFieldSheet.status}</strong>
                  </article>
                </div>
              </section>
            ) : null}

            {fieldSheetTab === 'technical' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Datos tecnicos</p>
                  <h3>Captura de campo</h3>
                </div>
                <div className="field-sheet-form-grid">
                  <label>
                    Condicion inicial
                    <textarea rows={3} value={fieldSheetForm.initialCondition} onChange={(event) => updateFieldSheetForm('initialCondition', event.target.value)} />
                  </label>
                  <label>
                    Condicion final
                    <textarea rows={3} value={fieldSheetForm.finalCondition} onChange={(event) => updateFieldSheetForm('finalCondition', event.target.value)} />
                  </label>
                  <label>
                    Patron usado
                    <textarea rows={3} value={fieldSheetForm.patternUsed} onChange={(event) => updateFieldSheetForm('patternUsed', event.target.value)} />
                  </label>
                  <label>
                    Resultados
                    <textarea rows={3} value={fieldSheetForm.results} onChange={(event) => updateFieldSheetForm('results', event.target.value)} />
                  </label>
                  <label>
                    Metodo
                    <textarea rows={3} value={fieldSheetForm.method} onChange={(event) => updateFieldSheetForm('method', event.target.value)} />
                  </label>
                  <label>
                    Condiciones ambientales
                    <textarea rows={3} value={fieldSheetForm.environmentalConditions} onChange={(event) => updateFieldSheetForm('environmentalConditions', event.target.value)} />
                  </label>
                  <label>
                    Observaciones
                    <textarea rows={3} value={fieldSheetForm.observations} onChange={(event) => updateFieldSheetForm('observations', event.target.value)} />
                  </label>
                  <label>
                    Evidencia / notas
                    <textarea rows={3} value={fieldSheetForm.evidenceNotes} onChange={(event) => updateFieldSheetForm('evidenceNotes', event.target.value)} />
                  </label>
                  <label className="form-field--wide">
                    Notas del tecnico
                    <textarea rows={3} value={fieldSheetForm.technicianNotes} onChange={(event) => updateFieldSheetForm('technicianNotes', event.target.value)} />
                  </label>
                </div>
                <div className="quotation-detail-save">
                  <span>Para completar se requieren condicion inicial/final, patron, resultados y observaciones o evidencia.</span>
                  <div className="toolbar-actions">
                    <button className="table-button" disabled={isSaving} onClick={saveFieldSheet} type="button">
                      Guardar
                    </button>
                    <button className="primary-button" disabled={isSaving || !['draft', 'in_progress', 'rejected'].includes(selectedFieldSheet.status)} onClick={completeCurrentFieldSheet} type="button">
                      Completar
                    </button>
                    <button className="table-button" disabled={isSaving || selectedFieldSheet.status !== 'completed'} onClick={reviewCurrentFieldSheet} type="button">
                      Enviar a revision
                    </button>
                    <label className="inline-select-field">
                      Tipo
                      <select
                        disabled={isSaving || activeCertificatesByFieldSheetId.has(selectedFieldSheet.id)}
                        onChange={(event) => setFieldSheetCertificateType(event.target.value)}
                        value={fieldSheetCertificateType}
                      >
                        <option value="acreditado">Acreditado</option>
                        <option value="trazable">Trazable</option>
                      </select>
                    </label>
                    <button
                      className="table-button table-button--primary"
                      disabled={
                        isSaving ||
                        !certificateReadyFieldSheetStatuses.has(selectedFieldSheet.status) ||
                        !certificateReadyEquipmentStatuses.has(selectedEquipmentForSheet.status) ||
                        activeCertificatesByFieldSheetId.has(selectedFieldSheet.id)
                      }
                      onClick={createCertificateFromCurrentFieldSheet}
                      type="button"
                    >
                      {activeCertificatesByFieldSheetId.has(selectedFieldSheet.id) ? 'Certificado creado' : 'Crear certificado'}
                    </button>
                  </div>
                </div>

                <section className="danger-zone">
                  <div className="danger-zone__copy">
                    <p>Zona de baja</p>
                    <span>Esta acción dará de baja la hoja de campo. No se eliminará físicamente y puede impactar certificados relacionados.</span>
                  </div>
                  <div className="toolbar-actions">
                    <button className="table-button table-button--danger" disabled={isSaving} onClick={handleDeleteFieldSheet} type="button">
                      Dar de baja hoja de campo
                    </button>
                  </div>
                </section>
              </section>
            ) : null}

            {fieldSheetTab === 'history' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Historial</p>
                  <h3>Eventos de hoja</h3>
                </div>
                <div className="quotation-history-list">
                  <article>
                    <strong>Hoja creada</strong>
                    <span>{new Date(selectedFieldSheet.created_at).toLocaleString('es-MX')}</span>
                  </article>
                  <article>
                    <strong>Ultima actualizacion</strong>
                    <span>{new Date(selectedFieldSheet.updated_at).toLocaleString('es-MX')}</span>
                  </article>
                  <article>
                    <strong>Estado actual</strong>
                    <span>{fieldSheetStatusLabels[selectedFieldSheet.status] ?? selectedFieldSheet.status}</span>
                  </article>
                  <article>
                    <strong>Equipo</strong>
                    <span>{selectedEquipmentForSheet.name}</span>
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


export default ServiceOrdersPage;
