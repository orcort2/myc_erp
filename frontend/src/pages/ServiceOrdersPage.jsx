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
  certificateReadyEquipmentStatuses,
  certificateStatusLabels
} from '../constants/statuses.js';
import {
  authenticateCertificate,
  authenticateApprovedCertificates,
  bulkUploadCertificatePdfs,
  changeEquipmentStatus,
  changeCertificateStatus,
  changeServiceOrderStatus,
  completeFieldSheet,
  createCertificate,
  downloadFieldSheetPdf,
  downloadAuthenticatedCertificatePdf,
  downloadWorkOrderPdf,
  createEquipment,
  createFieldSheet,
  deleteEquipment,
  deleteFieldSheet,
  deleteServiceOrder,
  getFieldSheet,
  getFieldSheetPdfUrl,
  getAuthenticatedCertificatePdfUrl,
  getOriginalCertificatePdfUrl,
  getWorkOrderPdfUrl,
  listCalibrationProcedures,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheets,
  listQuotations,
  listReferenceStandards,
  listServiceOrders,
  manualAcceptCertificateMatch,
  reviewFieldSheet,
  suggestFieldSheetPatterns,
  updateEquipment,
  updateFieldSheet,
  updateServiceOrder,
  uploadCertificatePdf,
  validateCertificatePdfMatch,
  releaseAuthenticatedCertificates,
  validateFieldSheetPatterns
} from '../services/api.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import {
  fieldSheetToForm,
  buildFieldSheetPayload,
  fieldSheetTemplateRowConfig,
  getFieldSheetCompletionErrors,
  updateFieldSheetResultCell,
  updateFieldSheetResultsRowsForTemplate
} from '../utils/fieldSheets.js';
import { formatDate, getClientDisplayName } from '../utils/formatters.js';

function safeNumber(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function safeText(value, fallback = '-') {
  return value === undefined || value === null || value === '' ? fallback : value;
}

function getRoleNames(user) {
  return (user?.roles ?? []).map((role) => (role.name || '').toLowerCase());
}

function hasStageAccess(user, stage) {
  const roles = getRoleNames(user);
  if (!roles.length || roles.some((role) => ['admin', 'administrador', 'administrator'].includes(role))) {
    return true;
  }
  if (stage === 'technical') return roles.some((role) => ['tecnico', 'técnico', 'technical'].includes(role));
  if (stage === 'capture') return roles.some((role) => ['captura', 'capture'].includes(role));
  if (stage === 'quality') return roles.some((role) => ['calidad', 'quality'].includes(role));
  return true;
}

function ServiceOrdersPage({ user = null }) {
  const [serviceOrders, setServiceOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [referenceStandards, setReferenceStandards] = useState([]);
  const [calibrationProcedures, setCalibrationProcedures] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedEquipmentForSheet, setSelectedEquipmentForSheet] = useState(null);
  const [selectedFieldSheet, setSelectedFieldSheet] = useState(null);
  const [orderForm, setOrderForm] = useState(emptyServiceOrderForm);
  const [equipmentForm, setEquipmentForm] = useState(emptyEquipmentForm);
  const [fieldSheetForm, setFieldSheetForm] = useState(emptyFieldSheetForm);
  const [fieldSheetCertificateType, setFieldSheetCertificateType] = useState('trazable');
  const [fieldSheetPatternSelection, setFieldSheetPatternSelection] = useState(null);
  const [selectedAuthentication, setSelectedAuthentication] = useState(null);
  const [selectedQualityCertificate, setSelectedQualityCertificate] = useState(null);
  const [returnToTechnicianRequest, setReturnToTechnicianRequest] = useState(null);
  const [returnToTechnicianReason, setReturnToTechnicianReason] = useState('');
  const [editingEquipmentId, setEditingEquipmentId] = useState(null);
  const [activeTab, setActiveTab] = useState('info');
  const [fieldSheetTab, setFieldSheetTab] = useState('info');
  const [orderFilter, setOrderFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isEquipmentModalOpen, setIsEquipmentModalOpen] = useState(false);
  const [isFieldSheetModalOpen, setIsFieldSheetModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const { confirmDialog, openConfirm, closeConfirm, handleConfirm } = useConfirmDialog();
  const canUseTechnicalActions = hasStageAccess(user, 'technical');
  const canUseCaptureActions = hasStageAccess(user, 'capture');
  const canUseQualityActions = hasStageAccess(user, 'quality');

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

  const selectedCertificates = useMemo(
    () => certificates.filter((certificate) => certificate.service_order_id === selectedOrder?.id && certificate.is_active !== false),
    [certificates, selectedOrder]
  );

  const selectedFieldSheets = useMemo(
    () => fieldSheets.filter((sheet) => selectedEquipment.some((item) => item.id === sheet.equipment_id) && sheet.is_active !== false),
    [fieldSheets, selectedEquipment]
  );

  const selectedOrderMetrics = useMemo(
    () => (selectedOrder ? getOrderMetrics(selectedOrder) : {
      equipmentCount: 0,
      expectedEquipment: 0,
      completedEquipment: 0,
      fieldSheetsCount: 0,
      fieldSheetsDone: 0,
      certificatesExpected: 0,
      pdfUploaded: 0,
      capturePending: 0,
      qualityPending: 0,
      authenticated: 0,
      released: 0,
      billingPending: false,
      advance: 0
    }),
    [selectedOrder, equipment, fieldSheets, certificates]
  );

  const captureMetrics = useMemo(() => ({
    expected: selectedCertificates.length,
    uploaded: selectedCertificates.filter((certificate) => certificate.final_pdf_path).length,
    pending: selectedCertificates.filter((certificate) => !certificate.final_pdf_path).length,
    matched: selectedCertificates.filter((certificate) => certificate.match_status === 'matched').length,
    warnings: selectedCertificates.filter((certificate) => certificate.match_status === 'warning').length,
    mismatches: selectedCertificates.filter((certificate) => certificate.match_status === 'mismatch').length,
    manual: selectedCertificates.filter((certificate) => certificate.match_status === 'manual_accepted').length
  }), [selectedCertificates]);

  const qualityMetrics = useMemo(() => ({
    pending: selectedCertificates.filter((certificate) => ['ready_for_quality', 'quality_review'].includes(certificate.status)).length,
    review: selectedCertificates.filter((certificate) => certificate.status === 'quality_review').length,
    approved: selectedCertificates.filter((certificate) => ['quality_approved', 'pdf_pending', 'pdf_uploaded'].includes(certificate.status)).length,
    rejected: selectedCertificates.filter((certificate) => certificate.status === 'quality_rejected').length,
    releasable: selectedCertificates.filter((certificate) => ['quality_approved', 'pdf_pending', 'pdf_uploaded'].includes(certificate.status) && certificate.final_pdf_path).length,
    authenticated: selectedCertificates.filter((certificate) => certificate.authenticated_pdf_path).length
  }), [selectedCertificates]);

  function getOrderMetrics(order) {
    const orderEquipment = equipment.filter((item) => item.service_order_id === order.id && item.is_active !== false);
    const orderEquipmentIds = new Set(orderEquipment.map((item) => item.id));
    const orderSheets = fieldSheets.filter((sheet) => orderEquipmentIds.has(sheet.equipment_id) && sheet.is_active !== false);
    const orderCertificates = certificates.filter((certificate) => certificate.service_order_id === order.id && certificate.is_active !== false);
    const pdfUploaded = orderCertificates.filter((certificate) => Boolean(certificate.final_pdf_path)).length;
    const capturePending = orderCertificates.filter((certificate) => ['expected', 'field_sheet_ready', 'capture_pending', 'capture_in_progress', 'quality_rejected'].includes(certificate.status)).length;
    const qualityPending = orderCertificates.filter((certificate) => ['ready_for_quality', 'quality_review'].includes(certificate.status)).length;
    const authenticated = orderCertificates.filter((certificate) => Boolean(certificate.authenticated_pdf_path)).length;
    const released = orderCertificates.filter((certificate) => certificate.status === 'released_to_client').length;
    const expectedEquipment = (order.items ?? []).reduce((sum, item) => sum + safeNumber(item.quantity), 0);
    const fieldSheetsDone = orderSheets.filter((sheet) => ['completed', 'under_review', 'approved'].includes(sheet.status)).length;
    const stageChecks = [
      Boolean(order.quotation_id),
      Boolean(order.agenda_date && order.service_date && order.technician_id),
      expectedEquipment ? orderEquipment.length >= Math.min(expectedEquipment, 10) : orderEquipment.length > 0,
      orderSheets.length > 0,
      orderSheets.length > 0 && fieldSheetsDone === orderSheets.length,
      orderCertificates.length > 0 && pdfUploaded === orderCertificates.length,
      orderCertificates.length > 0 && orderCertificates.every((certificate) => ['quality_approved', 'pdf_pending', 'pdf_uploaded', 'released_to_client'].includes(certificate.status)),
      orderCertificates.length > 0 && authenticated === orderCertificates.length,
      !order.requires_payment || ['released', 'closed'].includes(order.status),
      order.status === 'closed'
    ];
    return {
      expectedEquipment,
      equipmentCount: orderEquipment.length,
      completedEquipment: safeNumber(order.completed_equipment),
      fieldSheetsCount: orderSheets.length,
      fieldSheetsDone,
      certificatesExpected: orderCertificates.length,
      pdfUploaded,
      capturePending,
      qualityPending,
      authenticated,
      released,
      billingPending: order.status === 'pending_payment' || order.requires_payment,
      advance: Math.round((stageChecks.filter(Boolean).length / stageChecks.length) * 100)
    };
  }

  const filteredServiceOrders = useMemo(() => {
    return serviceOrders.filter((order) => {
      const metrics = getOrderMetrics(order);
      if (orderFilter === 'scheduled') return ['scheduled', 'confirmed', 'called'].includes(order.status);
      if (orderFilter === 'in_progress') return ['in_progress', 'technical_review'].includes(order.status);
      if (orderFilter === 'capture') return metrics.capturePending > 0 || order.status === 'capture';
      if (orderFilter === 'quality') return metrics.qualityPending > 0 || order.status === 'quality_review';
      if (orderFilter === 'pdf_pending') return metrics.certificatesExpected > metrics.pdfUploaded;
      if (orderFilter === 'released') return metrics.released > 0 || order.status === 'released';
      if (orderFilter === 'billing') return metrics.billingPending;
      if (orderFilter === 'closed') return order.status === 'closed';
      return true;
    });
  }, [serviceOrders, equipment, fieldSheets, certificates, orderFilter]);

  async function loadServiceOrderData() {
    setError('');
    setIsLoading(true);
    try {
      const [
        ordersResult,
        clientsResult,
        quotationsResult,
        equipmentResult,
        fieldSheetResult,
        certificatesResult,
        referenceStandardsResult,
        proceduresResult
      ] = await Promise.all([
        listServiceOrders(),
        listClients(),
        listQuotations(),
        listEquipment(),
        listFieldSheets(),
        listCertificates(),
        listReferenceStandards(),
        listCalibrationProcedures()
      ]);
      const nextOrders = Array.isArray(ordersResult) ? ordersResult : [];
      setServiceOrders(nextOrders);
      if (selectedOrder?.id) {
        const freshOrder = nextOrders.find((order) => order.id === selectedOrder.id);
        if (freshOrder) {
          setSelectedOrder(freshOrder);
        }
      }
      setClients(Array.isArray(clientsResult) ? clientsResult : []);
      setQuotations(Array.isArray(quotationsResult) ? quotationsResult : []);
      setEquipment(Array.isArray(equipmentResult) ? equipmentResult : []);
      setFieldSheets(Array.isArray(fieldSheetResult) ? fieldSheetResult : []);
      setCertificates(Array.isArray(certificatesResult) ? certificatesResult : []);
      setReferenceStandards(Array.isArray(referenceStandardsResult) ? referenceStandardsResult : []);
      setCalibrationProcedures(Array.isArray(proceduresResult) ? proceduresResult : []);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadServiceOrderData();
  }, []);

  useEffect(() => {
    function handleEscape(event) {
      if (event.key !== 'Escape') return;
      if (isFieldSheetModalOpen) {
        closeFieldSheetModal();
      } else if (isEquipmentModalOpen) {
        closeEquipmentModal();
      } else if (isDetailOpen) {
        closeOrderDetail();
      }
    }

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isDetailOpen, isEquipmentModalOpen, isFieldSheetModalOpen]);

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
    setSelectedAuthentication(null);
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
    if (!item && selectedEquipment.length >= 10) {
      setError('Maximo 10 equipos por Orden de Trabajo.');
      return;
    }
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

    if (existing) {
      const sheet = await getFieldSheet(existing.id);
      setSelectedFieldSheet(sheet);
      setFieldSheetForm(fieldSheetToForm(sheet));
      setFieldSheetCertificateType('trazable');
      setFieldSheetPatternSelection(null);
      setFieldSheetTab('info');
      setIsFieldSheetModalOpen(true);
      return;
    }

    const freshSheets = await listFieldSheets();
    const freshExisting = Array.isArray(freshSheets)
      ? freshSheets.find((sheet) => sheet.equipment_id === item.id && sheet.is_active !== false)
      : null;

    if (freshExisting) {
      setFieldSheets(freshSheets);
      const sheet = await getFieldSheet(freshExisting.id);
      setSelectedFieldSheet(sheet);
      setFieldSheetForm(fieldSheetToForm(sheet));
      setFieldSheetCertificateType('trazable');
      setFieldSheetPatternSelection(null);
      setFieldSheetTab('info');
      setIsFieldSheetModalOpen(true);
      return;
    }

    const sheet = await createFieldSheet({ equipment_id: item.id });
    setSelectedFieldSheet(sheet);
    setFieldSheetForm(fieldSheetToForm(sheet));
    setFieldSheetCertificateType('trazable');
    setFieldSheetPatternSelection(null);
    setFieldSheetTab('info');
    setIsFieldSheetModalOpen(true);
    setFieldSheets((current) => [sheet, ...current]);
    setNotice(`Hoja de campo creada para ${item.name}`);
    await loadServiceOrderData();
  } catch (requestError) {
    if (requestError.message.includes('ya tiene') || requestError.message.includes('409')) {
      await loadServiceOrderData();
      setError('La hoja ya existe. Recarga el ETS y vuelve a abrirla.');
      return;
    }
    setError(requestError.message);
  }
}

  function closeFieldSheetModal() {
    setIsFieldSheetModalOpen(false);
    setSelectedEquipmentForSheet(null);
    setSelectedFieldSheet(null);
    setFieldSheetForm(emptyFieldSheetForm);
    setFieldSheetCertificateType('trazable');
    setFieldSheetPatternSelection(null);
    setFieldSheetTab('info');
    setError('');
  }

  function updateFieldSheetForm(field, value) {
    setFieldSheetForm((current) => ({ ...current, [field]: value }));
  }

  function applyNextCalibrationInterval(months) {
    if (months === 'manual') return;
    if (!fieldSheetForm.calibrationDate) {
      setError('Define primero la fecha de calibracion.');
      return;
    }
    const nextDate = new Date(`${fieldSheetForm.calibrationDate}T00:00:00`);
    nextDate.setMonth(nextDate.getMonth() + Number(months));
    updateFieldSheetForm('nextCalibrationDate', nextDate.toISOString().slice(0, 10));
  }

  function addReferenceStandardToFieldSheet() {
    if (!fieldSheetForm.newReferenceStandardId) {
      setError('Selecciona un patron para agregarlo.');
      return;
    }
    const selectedReferenceStandard = referenceStandards.find(
      (item) => String(item.id) === fieldSheetForm.newReferenceStandardId
    );
    if (!selectedReferenceStandard) {
      setError('El patron seleccionado ya no esta disponible.');
      return;
    }
    const alreadyExists = fieldSheetForm.referenceStandards.some(
      (item) =>
        item.referenceStandardId === fieldSheetForm.newReferenceStandardId &&
        item.usageRole === (fieldSheetForm.newReferenceStandardUsageRole || 'primary') &&
        (item.measurementSection || '') === (fieldSheetForm.newReferenceStandardMeasurementSection || '')
    );
    if (alreadyExists) {
      setError('Ese patron ya fue agregado con el mismo rol y seccion.');
      return;
    }
    setFieldSheetForm((current) => ({
      ...current,
      referenceStandards: [
        ...current.referenceStandards,
        {
          referenceStandardId: current.newReferenceStandardId,
          usageRole: current.newReferenceStandardUsageRole || 'primary',
          measurementSection: current.newReferenceStandardMeasurementSection || '',
          notes: current.newReferenceStandardNotes || '',
          referenceStandard: selectedReferenceStandard
        }
      ],
      newReferenceStandardId: '',
      newReferenceStandardUsageRole: 'primary',
      newReferenceStandardMeasurementSection: '',
      newReferenceStandardNotes: ''
    }));
    setError('');
  }

  function removeReferenceStandardFromFieldSheet(indexToRemove) {
    setFieldSheetForm((current) => ({
      ...current,
      referenceStandards: current.referenceStandards.filter((_, index) => index !== indexToRemove)
    }));
  }

  async function suggestPatternsForCurrentFieldSheet() {
    if (!selectedFieldSheet) return;
    setError('');
    try {
      const result = await suggestFieldSheetPatterns(selectedFieldSheet.id);
      setFieldSheetPatternSelection(result);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function validatePatternsForCurrentFieldSheet() {
    if (!selectedFieldSheet) return;
    setError('');
    try {
      const result = await validateFieldSheetPatterns(selectedFieldSheet.id);
      setFieldSheetPatternSelection(result);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function updateFieldSheetTemplate(templateKey) {
    setFieldSheetForm((current) => updateFieldSheetResultsRowsForTemplate(current, templateKey));
  }

  function updateFieldSheetResult(rowIndex, field, value) {
    setFieldSheetForm((current) => ({
      ...current,
      resultsRows: updateFieldSheetResultCell(current.resultsRows, rowIndex, field, value)
    }));
  }

  function triggerBlobDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function openWorkOrderPdf(mode = 'view') {
    if (!selectedOrder) return;
    const pdfWindow = window.open(getWorkOrderPdfUrl(selectedOrder.id), '_blank', 'noopener,noreferrer');
    if (mode === 'print' && pdfWindow) {
      pdfWindow.addEventListener('load', () => {
        pdfWindow.focus();
        pdfWindow.print();
      });
    }
  }

  async function handleDownloadWorkOrderPdf() {
    if (!selectedOrder) return;
    setError('');
    setNotice('');
    try {
      const { blob, filename } = await downloadWorkOrderPdf(
        selectedOrder.id,
        selectedOrder.work_order_number,
        getClientDisplayName(clientsById.get(selectedOrder.client_id))
      );
      triggerBlobDownload(blob, filename);
      setNotice(`PDF ${filename} generado correctamente`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function openFieldSheetPdf(mode = 'view') {
    if (!selectedFieldSheet) return;
    const pdfWindow = window.open(getFieldSheetPdfUrl(selectedFieldSheet.id), '_blank', 'noopener,noreferrer');
    if (mode === 'print' && pdfWindow) {
      pdfWindow.addEventListener('load', () => {
        pdfWindow.focus();
        pdfWindow.print();
      });
    }
  }

  async function handleDownloadFieldSheetPdf() {
    if (!selectedFieldSheet || !selectedEquipmentForSheet) return;
    setError('');
    setNotice('');
    try {
      const { blob, filename } = await downloadFieldSheetPdf(
        selectedFieldSheet.id,
        selectedFieldSheet.work_order_number,
        selectedEquipmentForSheet.name
      );
      triggerBlobDownload(blob, filename);
      setNotice(`PDF ${filename} generado correctamente`);
    } catch (requestError) {
      setError(requestError.message);
    }
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

  /* async function createCertificateFromCurrentFieldSheet() {
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
    */

  /* async function createExpectedCertificateForEquipment(item) {
    if (!selectedOrder) return;
    if (activeCertificatesByEquipmentId.has(item.id)) {
      setError('Este equipo ya tiene un certificado esperado activo.');
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const created = await createCertificate({
        service_order_id: selectedOrder.id,
        equipment_id: item.id,
        field_sheet_id: fieldSheetsByEquipmentId.get(item.id)?.id ?? null,
        certificate_type: 'trazable'
      });
      setCertificates((current) => [created, ...current]);
      setNotice(`Certificado esperado ${created.folio} creado`);
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }
    */

  async function handleCertificateWorkflow(certificate, action, message) {
    let comment = null;
    if (action === 'return-to-technician') {
      setReturnToTechnicianRequest({ certificate, action, message });
      setReturnToTechnicianReason('');
      setError('');
      return;
    }
    await executeCertificateWorkflow(certificate, action, message, comment);
  }

  async function executeCertificateWorkflow(certificate, action, message, comment = null) {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await changeCertificateStatus(certificate.id, action, comment);
      setCertificates((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setNotice(message);
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function confirmReturnToTechnician() {
    const reason = returnToTechnicianReason.trim();
    if (!returnToTechnicianRequest) return;
    if (!reason) {
      setError('Captura el motivo para regresar al tecnico.');
      return;
    }
    const request = returnToTechnicianRequest;
    setReturnToTechnicianRequest(null);
    setReturnToTechnicianReason('');
    await executeCertificateWorkflow(request.certificate, request.action, request.message, reason);
  }

  async function handleCertificateAuthentication(certificate) {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await authenticateCertificate(certificate.id);
      setCertificates((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setNotice(`Certificado ${updated.folio} autenticado`);
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCertificateMatchAcceptance(certificate) {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await manualAcceptCertificateMatch(certificate.id, 'Aceptado manualmente desde ETS');
      setCertificates((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setNotice(`Match aceptado para ${updated.folio}`);
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCertificateMatchValidation(certificate) {
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await validateCertificatePdfMatch(certificate.id);
      setCertificates((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setNotice(`Matching ${updated.match_status} para ${updated.folio}`);
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleCertificatePdfUpload(certificate, files, input = null) {
    const [file] = Array.from(files ?? []);
    if (!file) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await uploadCertificatePdf(certificate.id, file);
      setCertificates((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setNotice(`PDF cargado para ${updated.folio}. Match: ${updated.match_status}`);
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
      if (input) {
        input.value = '';
      }
    }
  }

  function openAuthenticatedCertificatePdf(certificate) {
    if (!certificate.authenticated_pdf_path) {
      setError('El certificado aun no tiene PDF autenticado.');
      return;
    }
    const pdfWindow = window.open(getAuthenticatedCertificatePdfUrl(certificate.id), '_blank', 'noopener,noreferrer');
    if (!pdfWindow) {
      setError('No se pudo abrir el PDF autenticado.');
    }
  }

  function openOriginalCertificatePdf(certificate) {
    if (!certificate.final_pdf_path) {
      setError('El certificado aun no tiene PDF original cargado.');
      return;
    }
    const pdfWindow = window.open(getOriginalCertificatePdfUrl(certificate.id), '_blank', 'noopener,noreferrer');
    if (!pdfWindow) {
      setError('No se pudo abrir el PDF original.');
    }
  }

  async function handleDownloadAuthenticatedCertificatePdf(certificate) {
    setError('');
    setNotice('');
    try {
      const { blob, filename } = await downloadAuthenticatedCertificatePdf(
        certificate.id,
        certificate.expected_folio || certificate.folio,
        certificate.authentication_code
      );
      triggerBlobDownload(blob, filename);
      setNotice(`PDF autenticado ${filename} descargado`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function showCertificateAuthentication(certificate) {
    setSelectedAuthentication({
      code: certificate.authentication_code || '-',
      url: certificate.verification_url || (certificate.authentication_code ? `/verify/${certificate.authentication_code}` : '-'),
      hash: certificate.authentication_hash || '-',
      status: certificateStatusLabels[certificate.status] ?? certificate.status,
      authenticatedAt: certificate.authenticated_pdf_generated_at || null
    });
  }

  async function handleBulkPdfUpload(files, input = null) {
    if (!selectedOrder || !files?.length) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await bulkUploadCertificatePdfs(selectedOrder.id, files);
      setNotice(`Carga masiva: ${result.matched} matched, ${result.warnings} warning, ${result.mismatches} mismatch, ${result.missing} faltantes`);
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
      if (input) {
        input.value = '';
      }
    }
  }

  function summarizeBatchResult(result) {
    const processed = result.results?.filter((item) => ['authenticated', 'released'].includes(item.status)).map((item) => item.folio).filter(Boolean) ?? [];
    const actionCount = result.authenticated ?? result.released ?? 0;
    return `${actionCount} procesados, ${result.skipped} omitidos, ${result.errors} errores${processed.length ? `: ${processed.join(', ')}` : ''}`;
  }

  function handleAuthenticateApprovedBatch() {
    if (!selectedOrder) return;
    openConfirm({
      title: 'Autenticar aprobados',
      message: 'Se autenticarán los certificados aprobados con PDF y match aceptable. El lote continuará aunque algun certificado falle.',
      confirmText: 'Autenticar',
      onConfirm: async () => {
        setIsSaving(true);
        setError('');
        try {
          const result = await authenticateApprovedCertificates(selectedOrder.id);
          setNotice(`Autenticacion masiva: ${summarizeBatchResult(result)}`);
          await loadServiceOrderData();
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setIsSaving(false);
        }
      }
    });
  }

  function handleReleaseAuthenticatedBatch() {
    if (!selectedOrder) return;
    openConfirm({
      title: 'Liberar autenticados',
      message: 'Se liberarán al cliente los certificados autenticados con PDF y match aceptable. El lote continuará aunque algun certificado falle.',
      confirmText: 'Liberar',
      onConfirm: async () => {
        setIsSaving(true);
        setError('');
        try {
          const result = await releaseAuthenticatedCertificates(selectedOrder.id);
          setNotice(`Liberacion masiva: ${summarizeBatchResult(result)}`);
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
          <h1>Servicios / ETS</h1>
          <span>Expediente Tecnico del Servicio desde cotizacion aceptada hasta certificado autenticado.</span>
        </div>
      </div>

      {error && !isEquipmentModalOpen ? <div className="form-error dashboard-error">{error}</div> : null}
      {notice ? <div className="form-notice dashboard-error">{notice}</div> : null}

      <section className="clients-list-panel">
        <div className="section-heading">
          <div>
            <p>Listado operativo</p>
            <h2>{isLoading ? 'Cargando...' : `${filteredServiceOrders.length} expedientes`}</h2>
          </div>
        </div>

        <div className="client-modal-tabs quotation-detail-tabs ets-filter-tabs" role="tablist" aria-label="Filtros ETS">
          {[
            ['all', 'Todos'],
            ['scheduled', 'Programados'],
            ['in_progress', 'En proceso'],
            ['capture', 'Captura'],
            ['quality', 'Calidad'],
            ['pdf_pending', 'PDF pendientes'],
            ['released', 'Liberados'],
            ['billing', 'Facturacion pendiente'],
            ['closed', 'Cerrados']
          ].map(([key, label]) => (
            <button
              aria-selected={orderFilter === key}
              className={orderFilter === key ? 'client-modal-tab is-active' : 'client-modal-tab'}
              key={key}
              onClick={() => setOrderFilter(key)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>

        <div className="clients-table service-orders-table" aria-busy={isLoading}>
          <div className="clients-table__head">
            <span>Folio OS</span>
            <span>OT</span>
            <span>Cliente</span>
            <span>Estado</span>
            <span>Responsable</span>
            <span>Fecha</span>
            <span>Equipos</span>
            <span>Hojas</span>
            <span>Cert.</span>
            <span>PDFs</span>
            <span>Captura</span>
            <span>Calidad</span>
            <span>Avance</span>
            <span>Acciones</span>
          </div>

          {isLoading ? (
            <div className="clients-empty">Cargando expedientes...</div>
          ) : filteredServiceOrders.length ? (
            filteredServiceOrders.map((order) => {
              const client = clientsById.get(order.client_id);
              const metrics = getOrderMetrics(order);
              return (
                <button className="clients-table__row quotation-row-button" key={order.id} onClick={() => openOrderDetail(order)} type="button">
                  <span>{order.folio}</span>
                  <span>OT {order.work_order_number ?? '-'}</span>
                  <span>{getClientDisplayName(client)}</span>
                  <span>
                    <mark className={`quotation-status status-${order.status}`}>
                      {serviceOrderStatusLabels[order.status] ?? order.status}
                    </mark>
                  </span>
                  <span>{order.technician_id ? `#${order.technician_id}` : 'Por asignar'}</span>
                  <span>{formatDate(order.service_date || order.agenda_date)}</span>
                  <span>{metrics.equipmentCount}</span>
                  <span>{metrics.fieldSheetsDone}/{metrics.fieldSheetsCount}</span>
                  <span>{metrics.certificatesExpected}</span>
                  <span>{metrics.pdfUploaded}</span>
                  <span>{metrics.capturePending}</span>
                  <span>{metrics.qualityPending}</span>
                  <span>{metrics.advance}%</span>
                  <span>Abrir ETS</span>
                </button>
              );
            })
          ) : (
            <div className="clients-empty">No hay expedientes para este filtro.</div>
          )}
        </div>
      </section>

      {isDetailOpen && selectedOrder ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-detail-modal service-order-modal" aria-modal="true" role="dialog">
            <div className="quotation-detail-header">
              <div>
                <p>Expediente Tecnico del Servicio</p>
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

            <div className="ets-folder-tabs" role="tablist" aria-label="Carpetas del expediente">
              {[
                ['info', 'Resumen'],
                ['equipment', 'Equipos'],
                ['field-sheet', 'Hojas de Campo'],
                ['capture', 'Captura'],
                ['quality', 'Calidad'],
                ['certificates', 'Certificados'],
                ['documents', 'Documentos'],
                ['history', 'Historial'],
                ['billing', 'Facturacion']
              ].map(([key, label]) => (
                <button
                  aria-selected={activeTab === key}
                  className={activeTab === key ? 'ets-folder-tab is-active' : 'ets-folder-tab'}
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
                      <h3>Resumen ejecutivo</h3>
                    </div>
                    <div className="ets-progress-panel">
                      <div className="ets-progress-panel__header">
                        <strong>{safeNumber(selectedOrderMetrics.advance)}%</strong>
                        <span>Progreso global del expediente</span>
                      </div>
                      <div className="ets-progress-bar" aria-label="Progreso global">
                        <span style={{ width: `${safeNumber(selectedOrderMetrics.advance)}%` }} />
                      </div>
                      <div className="ets-stage-strip">
                        {[
                          ['Cotización', Boolean(selectedOrder.quotation_id)],
                          ['Agenda', Boolean(selectedOrder.agenda_date && selectedOrder.service_date && selectedOrder.technician_id)],
                          ['Equipos', selectedOrderMetrics.expectedEquipment ? selectedOrderMetrics.equipmentCount >= Math.min(selectedOrderMetrics.expectedEquipment, 10) : selectedOrderMetrics.equipmentCount > 0],
                          ['Hojas', selectedOrderMetrics.fieldSheetsCount > 0],
                          ['Captura', selectedOrderMetrics.certificatesExpected > 0 && selectedOrderMetrics.pdfUploaded === selectedOrderMetrics.certificatesExpected],
                          ['Calidad', selectedOrderMetrics.certificatesExpected > 0 && selectedCertificates.every((certificate) => ['quality_approved', 'pdf_pending', 'pdf_uploaded', 'released_to_client'].includes(certificate.status))],
                          ['PDF autenticado', selectedOrderMetrics.certificatesExpected > 0 && selectedOrderMetrics.authenticated === selectedOrderMetrics.certificatesExpected],
                          ['Facturación', !selectedOrderMetrics.billingPending],
                          ['Cierre', selectedOrder.status === 'closed']
                        ].map(([label, done]) => (
                          <span className={done ? 'ets-stage is-done' : 'ets-stage'} key={label}>{label}</span>
                        ))}
                      </div>
                    </div>
                    <div className="quotation-commercial-grid service-order-info-grid">
                      <article>
                        <span>Folio OS</span>
                        <strong>{selectedOrder.folio}</strong>
                      </article>
                      <article>
                        <span>Orden de trabajo</span>
                        <strong>OT {selectedOrder.work_order_number ?? '-'}</strong>
                      </article>
                      <article>
                        <span>Cliente</span>
                        <strong>{getClientDisplayName(clientsById.get(selectedOrder.client_id))}</strong>
                      </article>
                      <article>
                        <span>Cotizacion origen</span>
                        <strong>{quotationsById.get(selectedOrder.quotation_id)?.folio || '-'}</strong>
                      </article>
                      <article>
                        <span>Equipos esperados desde cotizacion</span>
                        <strong>{safeNumber(selectedOrderMetrics.expectedEquipment)}</strong>
                      </article>
                      <article>
                        <span>Equipos registrados</span>
                        <strong>{selectedEquipment.length} / 10</strong>
                      </article>
                      <article>
                        <span>Asesor</span>
                        <strong>{selectedOrder.advisor_id ? `#${selectedOrder.advisor_id}` : 'Sin asesor'}</strong>
                      </article>
                      <article>
                        <span>Estado actual</span>
                        <strong>{serviceOrderStatusLabels[selectedOrder.status] ?? selectedOrder.status}</strong>
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
                        <strong>{safeNumber(selectedOrder.total_equipment || selectedEquipment.length)}</strong>
                      </article>
                      <article>
                        <span>Equipos completados</span>
                        <strong>{safeNumber(selectedOrderMetrics.completedEquipment)}</strong>
                      </article>
                      <article>
                        <span>Hojas creadas</span>
                        <strong>{safeNumber(selectedOrderMetrics.fieldSheetsCount)}</strong>
                      </article>
                      <article>
                        <span>Hojas completadas</span>
                        <strong>{safeNumber(selectedOrderMetrics.fieldSheetsDone)}</strong>
                      </article>
                      <article>
                        <span>Certificados esperados</span>
                        <strong>{safeNumber(selectedOrderMetrics.certificatesExpected)}</strong>
                      </article>
                      <article>
                        <span>PDFs subidos</span>
                        <strong>{safeNumber(selectedOrderMetrics.pdfUploaded)}</strong>
                      </article>
                      <article>
                        <span>PDFs autenticados</span>
                        <strong>{safeNumber(selectedOrderMetrics.authenticated)}</strong>
                      </article>
                      <article>
                        <span>Certificados liberados</span>
                        <strong>{safeNumber(selectedOrderMetrics.released)}</strong>
                      </article>
                      <article>
                        <span>Pendientes Captura</span>
                        <strong>{safeNumber(selectedOrderMetrics.capturePending)}</strong>
                      </article>
                      <article>
                        <span>Pendientes Calidad</span>
                        <strong>{safeNumber(selectedOrderMetrics.qualityPending)}</strong>
                      </article>
                      <article>
                        <span>Facturacion pendiente</span>
                        <strong>{selectedOrderMetrics.billingPending ? 'Si' : 'No'}</strong>
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
                    <div className="toolbar-actions">
                      <button className="table-button" onClick={() => openWorkOrderPdf('view')} type="button">
                        Ver orden PDF
                      </button>
                      <button className="table-button" onClick={() => openEquipmentModal()} type="button">
                        Crear equipo
                      </button>
                      <button className="table-button" onClick={() => setActiveTab('equipment')} type="button">
                        Abrir equipos
                      </button>
                      <button className="table-button" onClick={() => setActiveTab('capture')} type="button">
                        Abrir captura
                      </button>
                      <button className="table-button" onClick={() => setActiveTab('quality')} type="button">
                        Abrir calidad
                      </button>
                      <label className="table-button table-button--file">
                        Subir PDFs
                        <input
                          accept="application/pdf"
                          multiple
                          onChange={(event) => handleBulkPdfUpload(event.target.files, event.target)}
                          type="file"
                        />
                      </label>
                      <button className="table-button" onClick={handleDownloadWorkOrderPdf} type="button">
                        Descargar PDF
                      </button>
                      <button className="table-button" onClick={() => openWorkOrderPdf('print')} type="button">
                        Imprimir
                      </button>
                      <button className="primary-button" disabled={isSaving} type="submit">
                        {isSaving ? 'Guardando...' : 'Guardar cambios'}
                      </button>
                    </div>
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
                    <h3>Equipos registrados: {selectedEquipment.length} / 10</h3>
                  </div>
                  {canUseTechnicalActions ? (
                    <button className="primary-button" disabled={selectedEquipment.length >= 10} onClick={() => openEquipmentModal()} type="button">
                      + Agregar equipo
                    </button>
                  ) : null}
                </div>
                <div className="ets-metric-strip">
                  <span className="ets-metric-badge"><strong>{safeNumber(selectedOrderMetrics.expectedEquipment)}</strong>Esperados cotizacion</span>
                  <span className="ets-metric-badge"><strong>{selectedEquipment.length}</strong>Registrados</span>
                  <span className="ets-metric-badge"><strong>{selectedEquipment.length} / 10</strong>Capacidad OT</span>
                  <span className="ets-metric-badge"><strong>{selectedFieldSheets.length} / 10</strong>Hojas</span>
                </div>
                {selectedEquipment.length >= 10 ? (
                  <div className="clients-empty">Maximo 10 equipos por Orden de Trabajo.</div>
                ) : null}
                <div className="clients-table equipment-table">
                  <div className="clients-table__head">
                    <span>Instrumento</span>
                    <span>Marca</span>
                    <span>Modelo</span>
                    <span>Serie</span>
                    <span>Identificacion</span>
                    <span>Folio reservado</span>
                    <span>Estado</span>
                    <span>Hoja de Campo</span>
                    <span>Certificado</span>
                    <span>PDF final</span>
                    <span>Acciones</span>
                  </div>
                  {selectedEquipment.length ? (
                    selectedEquipment.map((item) => {
                      const sheet = fieldSheetsByEquipmentId.get(item.id);
                      const certificate = activeCertificatesByEquipmentId.get(item.id);
                      return (
                        <div className="clients-table__row" key={item.id}>
                          <span>{item.name}</span>
                          <span>{item.brand || '-'}</span>
                          <span>{item.model || '-'}</span>
                          <span>{item.serial_number || '-'}</span>
                          <span>{item.internal_id || '-'}</span>
                          <span>{certificate?.expected_folio || certificate?.folio || '-'}</span>
                          <span>
                            <mark className={`quotation-status status-${item.status}`}>
                              {equipmentStatusLabels[item.status] ?? item.status}
                            </mark>
                          </span>
                          <span>{sheet ? `Hoja ${sheet.id}` : '-'}</span>
                          <span>{certificate ? certificateStatusLabels[certificate.status] ?? certificate.status : 'Pendiente'}</span>
                          <span>{certificate?.authenticated_pdf_path ? 'Autenticado' : certificate?.final_pdf_path ? 'Original' : '-'}</span>
                          <span className="clients-table__actions">
                            {canUseTechnicalActions ? (
                              <button className="table-button" onClick={() => openEquipmentModal(item)} type="button">
                                Editar
                              </button>
                            ) : null}
                            {canUseTechnicalActions ? equipmentActions.map((action) => (
                              <button
                                className="table-button"
                                disabled={!isEquipmentActionAllowed(item, action)}
                                key={action.key}
                                onClick={() => handleEquipmentStatus(item, action)}
                                type="button"
                              >
                                {action.label}
                              </button>
                            )) : null}
                            <button className="table-button table-button--primary" onClick={() => openFieldSheetForEquipment(item)} type="button">
                              Abrir hoja
                            </button>
                            {canUseTechnicalActions ? (
                              <button className="table-button" onClick={() => handleDeleteEquipment(item)} type="button">
                                Eliminar
                              </button>
                            ) : null}
                          </span>
                        </div>
                      );
                    })
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

            {activeTab === 'capture' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>Captura</p>
                    <h3>Certificados externos y PDFs finales</h3>
                  </div>
                  {canUseCaptureActions ? (
                    <label className="table-button table-button--file">
                      Subir PDFs multiples
                      <input accept="application/pdf" multiple onChange={(event) => handleBulkPdfUpload(event.target.files, event.target)} type="file" />
                    </label>
                  ) : null}
                </div>
                <div className="ets-metric-strip">
                  {[
                    ['Esperados', captureMetrics.expected],
                    ['PDFs cargados', captureMetrics.uploaded],
                    ['PDFs pendientes', captureMetrics.pending],
                    ['Matches', captureMetrics.matched],
                    ['Warnings', captureMetrics.warnings],
                    ['Mismatches', captureMetrics.mismatches],
                    ['Manual', captureMetrics.manual]
                  ].map(([label, value]) => (
                    <span className="ets-metric-badge" key={label}><strong>{safeNumber(value)}</strong>{label}</span>
                  ))}
                </div>
                <div className="clients-table ets-certificates-table">
                  <div className="clients-table__head">
                    <span>Folio</span>
                    <span>Equipo</span>
                    <span>Serie</span>
                    <span>Estado</span>
                    <span>PDF</span>
                    <span>Match</span>
                    <span>Acciones</span>
                  </div>
                  {selectedCertificates.length ? (
                    selectedCertificates.map((certificate) => {
                      const item = equipment.find((equipmentItem) => equipmentItem.id === certificate.equipment_id);
                      return (
                        <div className="clients-table__row" key={certificate.id}>
                          <span>{certificate.expected_folio || certificate.folio}</span>
                          <span>{item?.name || '-'}</span>
                          <span>{item?.serial_number || '-'}</span>
                          <span>{certificateStatusLabels[certificate.status] ?? certificate.status}</span>
                          <span>{certificate.final_pdf_path ? 'Cargado' : 'Pendiente'}</span>
                          <span>{certificate.match_status}</span>
                          <span className="clients-table__actions">
                            {canUseCaptureActions ? (
                              <>
                                <button className="table-button" onClick={() => handleCertificateWorkflow(certificate, 'start-capture', `Captura iniciada para ${certificate.folio}`)} type="button">
                                  Iniciar
                                </button>
                                <label className="table-button table-button--file">
                                  Subir PDF
                                  <input accept="application/pdf" onChange={(event) => handleCertificatePdfUpload(certificate, event.target.files, event.target)} type="file" />
                                </label>
                                <button className="table-button" disabled={!certificate.final_pdf_path} onClick={() => handleCertificateMatchValidation(certificate)} type="button">
                                  Validar
                                </button>
                                <button className="table-button" onClick={() => handleCertificateWorkflow(certificate, 'send-to-quality', `Certificado ${certificate.folio} enviado a calidad`)} type="button">
                                  Enviar a Calidad
                                </button>
                              </>
                            ) : null}
                          </span>
                        </div>
                      );
                    })
                  ) : (
                    <div className="clients-empty">Crea certificados esperados desde Equipos para iniciar captura.</div>
                  )}
                </div>
              </section>
            ) : null}

            {activeTab === 'quality' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>Calidad</p>
                    <h3>Revision, aprobacion y liberacion</h3>
                  </div>
                  {canUseQualityActions ? (
                    <div className="toolbar-actions">
                      <button className="table-button" disabled={isSaving} onClick={handleAuthenticateApprovedBatch} type="button">
                        Autenticar aprobados
                      </button>
                      <button className="table-button table-button--primary" disabled={isSaving} onClick={handleReleaseAuthenticatedBatch} type="button">
                        Liberar autenticados
                      </button>
                    </div>
                  ) : null}
                </div>
                <div className="ets-metric-strip">
                  {[
                    ['Pendientes', qualityMetrics.pending],
                    ['En revision', qualityMetrics.review],
                    ['Aprobados', qualityMetrics.approved],
                    ['Rechazados', qualityMetrics.rejected],
                    ['Liberables', qualityMetrics.releasable],
                    ['Autenticados', qualityMetrics.authenticated]
                  ].map(([label, value]) => (
                    <span className="ets-metric-badge" key={label}><strong>{safeNumber(value)}</strong>{label}</span>
                  ))}
                </div>
                <div className="clients-table ets-certificates-table">
                  <div className="clients-table__head">
                    <span>Folio</span>
                    <span>Equipo</span>
                    <span>Hoja</span>
                    <span>PDF</span>
                    <span>Match</span>
                    <span>Estado</span>
                    <span>Acciones</span>
                  </div>
                  {selectedCertificates.length ? (
                    selectedCertificates.map((certificate) => {
                      const item = equipment.find((equipmentItem) => equipmentItem.id === certificate.equipment_id);
                      const sheet = certificate.field_sheet_id ? fieldSheets.find((candidate) => candidate.id === certificate.field_sheet_id) : null;
                      return (
                        <div
                          className="clients-table__row clients-table__row--clickable"
                          key={certificate.id}
                          onClick={() => setSelectedQualityCertificate(certificate)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter') setSelectedQualityCertificate(certificate);
                          }}
                          role="button"
                          tabIndex={0}
                        >
                          <span>{certificate.expected_folio || certificate.folio}</span>
                          <span>{item?.name || '-'}</span>
                          <span>{sheet ? fieldSheetStatusLabels[sheet.status] ?? sheet.status : '-'}</span>
                          <span>{certificate.final_pdf_path ? 'Cargado' : 'Pendiente'}</span>
                          <span>{certificate.match_status}</span>
                          <span>{certificateStatusLabels[certificate.status] ?? certificate.status}</span>
                          <span className="clients-table__actions">
                            {canUseQualityActions ? (
                              <button className="table-button" onClick={(event) => { event.stopPropagation(); setSelectedQualityCertificate(certificate); }} type="button">
                                Revisar
                              </button>
                            ) : null}
                          </span>
                        </div>
                      );
                    })
                  ) : (
                    <div className="clients-empty">No hay certificados esperados en este ETS.</div>
                  )}
                </div>
              </section>
            ) : null}

            {activeTab === 'certificates' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Certificados</p>
                  <h3>Administracion de certificados externos</h3>
                </div>
                <div className="clients-table ets-certificates-table">
                  <div className="clients-table__head">
                    <span>Folio</span>
                    <span>Equipo</span>
                    <span>Serie</span>
                    <span>Identificacion</span>
                    <span>Estado</span>
                    <span>PDF original</span>
                    <span>PDF autenticado</span>
                    <span>Codigo</span>
                    <span>Match</span>
                    <span>Cliente</span>
                    <span>Fecha auth</span>
                    <span>Acciones</span>
                  </div>
                  {selectedCertificates.length ? (
                    selectedCertificates.map((certificate) => {
                      const item = equipment.find((equipmentItem) => equipmentItem.id === certificate.equipment_id);
                      return (
                        <div className="clients-table__row" key={certificate.id}>
                          <span>{certificate.expected_folio || certificate.folio}</span>
                          <span>{item?.name || '-'}</span>
                          <span>{item?.serial_number || '-'}</span>
                          <span>{item?.internal_id || '-'}</span>
                          <span>{certificateStatusLabels[certificate.status] ?? certificate.status}</span>
                          <span>{certificate.final_pdf_path ? 'Cargado' : '-'}</span>
                          <span>{certificate.authenticated_pdf_path ? 'Listo' : '-'}</span>
                          <span>{certificate.authentication_code || '-'}</span>
                          <span>{certificate.match_status}</span>
                          <span>{certificate.client_visible ? 'Visible' : 'Interno'}</span>
                          <span>{certificate.authenticated_pdf_generated_at ? new Date(certificate.authenticated_pdf_generated_at).toLocaleString('es-MX') : '-'}</span>
                          <span className="clients-table__actions">
                            <button className="table-button" disabled={!certificate.authenticated_pdf_path} onClick={() => openAuthenticatedCertificatePdf(certificate)} type="button">
                              Ver PDF
                            </button>
                            <button className="table-button" disabled={!certificate.authenticated_pdf_path} onClick={() => handleDownloadAuthenticatedCertificatePdf(certificate)} type="button">
                              Descargar
                            </button>
                            <button className="table-button" disabled={!certificate.authentication_code} onClick={() => showCertificateAuthentication(certificate)} type="button">
                              Ver autenticacion
                            </button>
                            {canUseCaptureActions ? (
                              <label className="table-button table-button--file">
                                Reemplazar PDF
                                <input accept="application/pdf" onChange={(event) => handleCertificatePdfUpload(certificate, event.target.files, event.target)} type="file" />
                              </label>
                            ) : null}
                            {canUseCaptureActions || canUseQualityActions ? (
                              <button className="table-button" disabled={!certificate.final_pdf_path} onClick={() => handleCertificateMatchValidation(certificate)} type="button">
                                Validar match
                              </button>
                            ) : null}
                            {canUseQualityActions ? (
                              <>
                                <button className="table-button" disabled={!certificate.final_pdf_path} onClick={() => handleCertificateAuthentication(certificate)} type="button">
                                  Autenticar
                                </button>
                                <button className="table-button table-button--primary" onClick={() => handleCertificateWorkflow(certificate, 'release-to-client', `Certificado ${certificate.folio} liberado al cliente`)} type="button">
                                  Liberar
                                </button>
                                <button className="table-button" onClick={() => handleCertificateWorkflow(certificate, 'suspend', `Certificado ${certificate.folio} suspendido`)} type="button">
                                  Suspender
                                </button>
                              </>
                            ) : null}
                          </span>
                        </div>
                      );
                    })
                  ) : (
                    <div className="clients-empty">No hay certificados esperados en este ETS.</div>
                  )}
                </div>
                {selectedAuthentication ? (
                  <aside className="ets-auth-panel">
                    <div>
                      <p>Autenticacion del certificado</p>
                      <strong>{selectedAuthentication.code}</strong>
                    </div>
                    <span>URL: {selectedAuthentication.url}</span>
                    <span>Hash SHA-256: {selectedAuthentication.hash}</span>
                    <span>Estado: {selectedAuthentication.status}</span>
                    <span>Fecha: {selectedAuthentication.authenticatedAt ? new Date(selectedAuthentication.authenticatedAt).toLocaleString('es-MX') : '-'}</span>
                  </aside>
                ) : null}
              </section>
            ) : null}

            {activeTab === 'documents' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Documentos</p>
                  <h3>Documentos del expediente</h3>
                </div>
                <div className="field-sheet-prep-list">
                  <article className="glass-card-mini">
                    <strong>Cotizacion</strong>
                    <span>{quotationsById.get(selectedOrder.quotation_id)?.folio || 'Sin cotizacion vinculada'}</span>
                    <button className="table-button" disabled type="button">Pendiente</button>
                  </article>
                  <article className="glass-card-mini">
                    <strong>Orden de trabajo</strong>
                    <span>Documento operativo del ETS.</span>
                    <button className="table-button" onClick={() => openWorkOrderPdf('view')} type="button">Abrir</button>
                    <button className="table-button" onClick={handleDownloadWorkOrderPdf} type="button">Descargar</button>
                    <button className="table-button" onClick={() => openWorkOrderPdf('print')} type="button">Imprimir</button>
                  </article>
                  <article className="glass-card-mini">
                    <strong>Hojas de campo</strong>
                    <span>{selectedFieldSheets.length} hojas vinculadas al expediente.</span>
                    <button className="table-button" onClick={() => setActiveTab('field-sheet')} type="button">Abrir hojas</button>
                  </article>
                  <article className="glass-card-mini">
                    <strong>Certificados originales</strong>
                    <span>{selectedCertificates.filter((certificate) => certificate.final_pdf_path).length} PDF originales cargados.</span>
                    <button className="table-button" onClick={() => setActiveTab('certificates')} type="button">Abrir certificados</button>
                    <button className="table-button" disabled type="button">Lote proximamente</button>
                  </article>
                  <article className="glass-card-mini">
                    <strong>Certificados autenticados</strong>
                    <span>{selectedCertificates.filter((certificate) => certificate.authenticated_pdf_path).length} finales para cliente.</span>
                    <button className="table-button" onClick={() => setActiveTab('certificates')} type="button">Abrir autenticados</button>
                    <button className="table-button" disabled type="button">Lote proximamente</button>
                  </article>
                  <article className="glass-card-mini">
                    <strong>Evidencias</strong>
                    <span>Repositorio documental del ETS.</span>
                    <button className="table-button" disabled type="button">Proximamente</button>
                  </article>
                  <article className="glass-card-mini">
                    <strong>Facturacion</strong>
                    <span>{selectedOrder.status === 'pending_payment' ? 'Facturacion pendiente' : 'Preparado para facturacion'}</span>
                    <button className="table-button" onClick={() => setActiveTab('billing')} type="button">Abrir facturacion</button>
                  </article>
                  <article className="glass-card-mini">
                    <strong>Cliente / administrativos</strong>
                    <span>El cliente solo descarga certificados autenticados.</span>
                    <button className="table-button" disabled type="button">Proximamente</button>
                  </article>
                  {selectedCertificates.filter((certificate) => certificate.authenticated_pdf_path).map((certificate) => (
                    <article className="glass-card-mini" key={`auth-doc-${certificate.id}`}>
                      <strong>{certificate.expected_folio || certificate.folio}</strong>
                      <span>{certificate.authentication_code || 'PDF autenticado'}</span>
                      <button className="table-button" onClick={() => openAuthenticatedCertificatePdf(certificate)} type="button">Ver</button>
                      <button className="table-button" onClick={() => handleDownloadAuthenticatedCertificatePdf(certificate)} type="button">Descargar</button>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {activeTab === 'history' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Historial</p>
                  <h3>Linea de tiempo del expediente</h3>
                </div>
                <div className="ets-timeline">
                  {[
                    selectedOrder.quotation_id ? {
                      date: quotationsById.get(selectedOrder.quotation_id)?.created_at || selectedOrder.created_at,
                      action: 'Cotizacion vinculada',
                      entity: quotationsById.get(selectedOrder.quotation_id)?.folio || `#${selectedOrder.quotation_id}`,
                      description: 'Origen comercial del expediente.'
                    } : null,
                    {
                      date: selectedOrder.created_at,
                      action: 'Orden creada',
                      entity: selectedOrder.folio,
                      description: `OT ${selectedOrder.work_order_number ?? '-'} registrada.`
                    },
                    ...selectedEquipment.map((item) => ({
                      date: item.created_at,
                      action: 'Equipo registrado',
                      entity: item.name,
                      description: [item.brand, item.model, item.serial_number].filter(Boolean).join(' · ') || 'Equipo del expediente.'
                    })),
                    ...selectedFieldSheets.map((sheet) => ({
                      date: sheet.created_at,
                      action: 'Hoja creada',
                      entity: `Hoja ${sheet.id}`,
                      description: fieldSheetStatusLabels[sheet.status] ?? sheet.status
                    })),
                    ...selectedFieldSheets.filter((sheet) => ['completed', 'review', 'approved'].includes(sheet.status)).map((sheet) => ({
                      date: sheet.updated_at,
                      action: 'Hoja completada',
                      entity: `Hoja ${sheet.id}`,
                      description: 'Registro tecnico listo para revision documental.'
                    })),
                    ...selectedCertificates.flatMap((certificate) => [
                      {
                        date: certificate.created_at,
                        action: 'Certificado esperado',
                        entity: certificate.expected_folio || certificate.folio,
                        description: certificateStatusLabels[certificate.status] ?? certificate.status
                      },
                      certificate.capture_started_at ? {
                        date: certificate.capture_started_at,
                        action: 'Captura iniciada',
                        entity: certificate.expected_folio || certificate.folio,
                        description: 'Captura trabaja el certificado externo.'
                      } : null,
                      certificate.final_pdf_uploaded_at ? {
                        date: certificate.final_pdf_uploaded_at,
                        action: 'PDF subido',
                        entity: certificate.final_pdf_original_filename || certificate.folio,
                        description: `Match: ${certificate.match_status || '-'}`
                      } : null,
                      certificate.sent_to_quality_at ? {
                        date: certificate.sent_to_quality_at,
                        action: 'Enviado a calidad',
                        entity: certificate.expected_folio || certificate.folio,
                        description: 'Listo para revision documental.'
                      } : null,
                      certificate.quality_reviewed_at ? {
                        date: certificate.quality_reviewed_at,
                        action: certificate.status === 'quality_rejected' ? 'Calidad rechazo' : 'Calidad aprobo',
                        entity: certificate.expected_folio || certificate.folio,
                        description: certificate.quality_rejection_reason || 'Revision de calidad registrada.'
                      } : null,
                      certificate.authenticated_pdf_generated_at ? {
                        date: certificate.authenticated_pdf_generated_at,
                        action: 'Certificado autenticado',
                        entity: certificate.authentication_code || certificate.folio,
                        description: 'PDF autenticado generado por MYC SYSTEM.'
                      } : null,
                      certificate.released_to_client_at ? {
                        date: certificate.released_to_client_at,
                        action: 'Liberado al cliente',
                        entity: certificate.expected_folio || certificate.folio,
                        description: 'Certificado visible en portal cliente.'
                      } : null
                    ].filter(Boolean))
                  ]
                    .filter(Boolean)
                    .sort((a, b) => new Date(b.date || 0) - new Date(a.date || 0))
                    .map((event, index) => (
                      <article className="ets-timeline-item" key={`${event.action}-${event.entity}-${index}`}>
                        <time>{event.date ? new Date(event.date).toLocaleString('es-MX') : '-'}</time>
                        <div>
                          <strong>{event.action}</strong>
                          <span>{event.entity}</span>
                          <p>{event.description}</p>
                        </div>
                      </article>
                    ))}
                </div>
              </section>
            ) : null}

            {activeTab === 'billing' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Facturacion</p>
                  <h3>Control administrativo del ETS</h3>
                </div>
                <div className="quotation-commercial-grid service-order-info-grid">
                  <article>
                    <span>Requiere pago</span>
                    <strong>{selectedOrder.requires_payment ? 'Si' : 'No'}</strong>
                  </article>
                  <article>
                    <span>Estado administrativo</span>
                    <strong>{selectedOrder.status === 'pending_payment' ? 'Facturacion pendiente' : 'Sin bloqueo administrativo'}</strong>
                  </article>
                  <article>
                    <span>Certificados liberados</span>
                    <strong>{selectedCertificates.filter((certificate) => certificate.status === 'released_to_client').length}</strong>
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
                    <span>Orden de trabajo</span>
                    <strong>OT {selectedFieldSheet.work_order_number ?? selectedOrder.work_order_number ?? '-'}</strong>
                  </article>
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
                    <span>Plantilla</span>
                    <strong>{fieldSheetForm.templateKey === 'electrica' ? 'Eléctrica' : 'General'}</strong>
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
                    Plantilla
                    <select
                      disabled={selectedFieldSheet.status !== 'draft' || isSaving}
                      value={fieldSheetForm.templateKey}
                      onChange={(event) => updateFieldSheetTemplate(event.target.value)}
                    >
                      <option value="general">General</option>
                      <option value="electrica">Eléctrica</option>
                    </select>
                  </label>
                  <label>
                    Procedimiento de calibracion
                    <select value={fieldSheetForm.calibrationProcedureId} onChange={(event) => updateFieldSheetForm('calibrationProcedureId', event.target.value)}>
                      <option value="">Sin procedimiento</option>
                      {calibrationProcedures.map((procedure) => (
                        <option key={procedure.id} value={procedure.id}>
                          {procedure.code} v{procedure.version} · {procedure.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Lugar de calibracion
                    <input type="text" value={fieldSheetForm.calibrationPlace} onChange={(event) => updateFieldSheetForm('calibrationPlace', event.target.value)} />
                  </label>
                  <label className="form-field--wide">
                    Patrones utilizados (opcional)
                    <div className="field-sheet-reference-builder">
                      <select value={fieldSheetForm.newReferenceStandardId || ''} onChange={(event) => updateFieldSheetForm('newReferenceStandardId', event.target.value)}>
                        <option value="">Selecciona patron</option>
                        {referenceStandards.map((standard) => (
                          <option key={standard.id} value={standard.id}>
                            {standard.internal_code} · {standard.name}
                          </option>
                        ))}
                      </select>
                      <select value={fieldSheetForm.newReferenceStandardUsageRole || 'primary'} onChange={(event) => updateFieldSheetForm('newReferenceStandardUsageRole', event.target.value)}>
                        <option value="primary">Primario</option>
                        <option value="secondary">Secundario</option>
                        <option value="auxiliary">Auxiliar</option>
                        <option value="environmental">Ambiental</option>
                        <option value="other">Otro</option>
                      </select>
                      <input type="text" placeholder="Seccion de medicion" value={fieldSheetForm.newReferenceStandardMeasurementSection || ''} onChange={(event) => updateFieldSheetForm('newReferenceStandardMeasurementSection', event.target.value)} />
                      <input type="text" placeholder="Notas de uso" value={fieldSheetForm.newReferenceStandardNotes || ''} onChange={(event) => updateFieldSheetForm('newReferenceStandardNotes', event.target.value)} />
                      <button className="table-button" type="button" onClick={addReferenceStandardToFieldSheet}>
                        Agregar patron
                      </button>
                    </div>
                    <div className="field-sheet-reference-list">
                      {fieldSheetForm.referenceStandards.length ? (
                        fieldSheetForm.referenceStandards.map((item, index) => {
                          const standard = item.referenceStandard || referenceStandards.find((row) => String(row.id) === item.referenceStandardId);
                          return (
                            <article className="field-sheet-reference-card" key={`${item.referenceStandardId}-${item.usageRole}-${item.measurementSection}-${index}`}>
                              <div>
                                <strong>{standard?.internal_code || 'Patron'} · {standard?.name || item.referenceStandardId}</strong>
                                <span>
                                  {item.usageRole} · {item.measurementSection || 'sin seccion'} · {standard?.magnitude || '-'}
                                </span>
                                <span>
                                  Estado: {standard?.effective_status || standard?.status || '-'} · Vigencia: {standard?.next_calibration_on || '-'}
                                </span>
                                <span>
                                  Rango: {[standard?.range_min, standard?.range_max, standard?.unit].filter((value) => value !== null && value !== undefined && value !== '').join(' / ') || '-'}
                                </span>
                                <span>
                                  Incertidumbres activas: {Array.isArray(standard?.uncertainties) ? standard.uncertainties.filter((row) => row.is_active !== false).length : 0}
                                </span>
                                {standard?.effective_status === 'expired' || standard?.status === 'out_of_service' ? (
                                  <mark className={`quotation-status status-${standard.effective_status || standard.status}`}>
                                    Advertencia: patron vencido o fuera de servicio
                                  </mark>
                                ) : null}
                              </div>
                              <button className="table-button table-button--danger" type="button" onClick={() => removeReferenceStandardFromFieldSheet(index)}>
                                Quitar
                              </button>
                            </article>
                          );
                        })
                      ) : (
                        <span className="field-sheet-reference-empty">Aun no se asignan patrones a esta hoja.</span>
                      )}
                    </div>
                    <div className="toolbar-actions">
                      <button className="table-button" type="button" onClick={suggestPatternsForCurrentFieldSheet}>
                        Sugerir patrones opcional
                      </button>
                      <button className="table-button" type="button" onClick={validatePatternsForCurrentFieldSheet}>
                        Validar opcional
                      </button>
                    </div>
                    {fieldSheetPatternSelection ? (
                      <div className="pattern-selection-panel">
                        <strong>{fieldSheetPatternSelection.errors?.length ? 'Error' : fieldSheetPatternSelection.warnings?.length ? 'Advertencia' : 'Valido'}</strong>
                        <span>{fieldSheetPatternSelection.explanation}</span>
                        {(fieldSheetPatternSelection.errors ?? []).map((item) => <mark className="quotation-status status-rejected" key={item}>{item}</mark>)}
                        {(fieldSheetPatternSelection.warnings ?? []).map((item) => <mark className="quotation-status status-draft" key={item}>{item}</mark>)}
                        <div className="field-sheet-reference-list">
                          {(fieldSheetPatternSelection.selected_recommendations ?? []).map((candidate) => (
                            <article className="field-sheet-reference-card" key={candidate.pattern_id}>
                              <div>
                                <strong>{candidate.pattern_code} · {candidate.pattern_name}</strong>
                                <span>Rango: {[candidate.range_min, candidate.range_max, candidate.unit].filter((value) => value !== null && value !== undefined && value !== '').join(' / ') || '-'}</span>
                                <span>Certificado: {candidate.current_certificate_number || '-'} · Vence: {candidate.current_certificate_expiration_date || '-'}</span>
                                <span>Incertidumbre: {candidate.applicable_uncertainty ?? '-'} {candidate.uncertainty_unit || ''} · k {candidate.k_factor ?? '-'}</span>
                                <span>{candidate.validation_messages?.join(' · ') || 'Recomendado por mejor compatibilidad.'}</span>
                              </div>
                              <mark className={`quotation-status status-${candidate.validation_status}`}>{candidate.validation_status}</mark>
                            </article>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </label>
                  <label>
                    Fecha recepcion
                    <input type="date" value={fieldSheetForm.receptionDate} onChange={(event) => updateFieldSheetForm('receptionDate', event.target.value)} />
                  </label>
                  <label>
                    Fecha calibracion
                    <input type="date" value={fieldSheetForm.calibrationDate} onChange={(event) => updateFieldSheetForm('calibrationDate', event.target.value)} />
                  </label>
                  <label>
                    Proxima calibracion
                    <input type="date" value={fieldSheetForm.nextCalibrationDate} onChange={(event) => updateFieldSheetForm('nextCalibrationDate', event.target.value)} />
                  </label>
                  <label>
                    Vigencia rapida
                    <select defaultValue="manual" onChange={(event) => applyNextCalibrationInterval(event.target.value)}>
                      <option value="manual">Manual</option>
                      <option value="6">6 meses</option>
                      <option value="12">12 meses</option>
                      <option value="24">24 meses</option>
                    </select>
                  </label>
                  <label>
                    Cotizacion / pedido
                    <input type="text" value={fieldSheetForm.purchaseOrderOrQuotation} onChange={(event) => updateFieldSheetForm('purchaseOrderOrQuotation', event.target.value)} />
                  </label>
                  <label>
                    Humedad inicial
                    <input type="text" value={fieldSheetForm.environmentHumidityStart} onChange={(event) => updateFieldSheetForm('environmentHumidityStart', event.target.value)} />
                  </label>
                  <label>
                    Humedad final
                    <input type="text" value={fieldSheetForm.environmentHumidityEnd} onChange={(event) => updateFieldSheetForm('environmentHumidityEnd', event.target.value)} />
                  </label>
                  <label>
                    Temperatura inicial
                    <input type="text" value={fieldSheetForm.environmentTemperatureStart} onChange={(event) => updateFieldSheetForm('environmentTemperatureStart', event.target.value)} />
                  </label>
                  <label>
                    Temperatura final
                    <input type="text" value={fieldSheetForm.environmentTemperatureEnd} onChange={(event) => updateFieldSheetForm('environmentTemperatureEnd', event.target.value)} />
                  </label>
                  <label>
                    Condicion general equipo
                    <select value={fieldSheetForm.equipmentGeneralCondition} onChange={(event) => updateFieldSheetForm('equipmentGeneralCondition', event.target.value)}>
                      <option value="">Sin definir</option>
                      <option value="ok">OK</option>
                      <option value="not_ok">No OK</option>
                    </select>
                  </label>
                  <label className="service-order-checkbox">
                    <input
                      checked={fieldSheetForm.considerEquipmentDeviations}
                      onChange={(event) => updateFieldSheetForm('considerEquipmentDeviations', event.target.checked)}
                      type="checkbox"
                    />
                    Considerar desviaciones del equipo
                  </label>
                  <label>
                    Unidades
                    <input type="text" value={fieldSheetForm.units} onChange={(event) => updateFieldSheetForm('units', event.target.value)} />
                  </label>
                  <label>
                    Calibro
                    <input type="text" value={fieldSheetForm.calibratedBy} onChange={(event) => updateFieldSheetForm('calibratedBy', event.target.value)} />
                  </label>
                  <label>
                    Reviso
                    <input type="text" value={fieldSheetForm.reviewedBy} onChange={(event) => updateFieldSheetForm('reviewedBy', event.target.value)} />
                  </label>
                  <label>
                    Reporte
                    <input type="text" value={fieldSheetForm.reportMadeBy} onChange={(event) => updateFieldSheetForm('reportMadeBy', event.target.value)} />
                  </label>
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
                    Resumen de resultados
                    <textarea rows={3} value={fieldSheetForm.resultsSummary} onChange={(event) => updateFieldSheetForm('resultsSummary', event.target.value)} />
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
                <div className="field-sheet-results-stack">
                  {(fieldSheetTemplateRowConfig[fieldSheetForm.templateKey] ?? fieldSheetTemplateRowConfig.general).map((section) => {
                    const sectionRows = fieldSheetForm.resultsRows.filter((row) => row.sectionKey === section.key);
                    return (
                      <section className="field-sheet-results-panel" key={section.key}>
                        <div className="quotation-section__title">
                          <p>Resultados estructurados</p>
                          <h3>{section.label}</h3>
                        </div>
                        <div className="clients-table field-sheet-results-table">
                          <div className="clients-table__head">
                            <span>#</span>
                            <span>Patron</span>
                            <span>Lectura 1</span>
                            <span>Lectura 2</span>
                            <span>Lectura 3</span>
                            <span>Unidad</span>
                            <span>Notas</span>
                          </div>
                          {sectionRows.map((row) => {
                            const rowIndex = fieldSheetForm.resultsRows.findIndex(
                              (item) => item.sectionKey === row.sectionKey && item.rowNumber === row.rowNumber
                            );
                            return (
                              <div className="clients-table__row field-sheet-results-row" key={`${row.sectionKey}-${row.rowNumber}`}>
                                <span>{row.rowNumber}</span>
                                <span><input type="text" value={row.patternValue} onChange={(event) => updateFieldSheetResult(rowIndex, 'patternValue', event.target.value)} /></span>
                                <span><input type="text" value={row.ibcValue1} onChange={(event) => updateFieldSheetResult(rowIndex, 'ibcValue1', event.target.value)} /></span>
                                <span><input type="text" value={row.ibcValue2} onChange={(event) => updateFieldSheetResult(rowIndex, 'ibcValue2', event.target.value)} /></span>
                                <span><input type="text" value={row.ibcValue3} onChange={(event) => updateFieldSheetResult(rowIndex, 'ibcValue3', event.target.value)} /></span>
                                <span><input type="text" value={row.unit} onChange={(event) => updateFieldSheetResult(rowIndex, 'unit', event.target.value)} /></span>
                                <span><input type="text" value={row.notes} onChange={(event) => updateFieldSheetResult(rowIndex, 'notes', event.target.value)} /></span>
                              </div>
                            );
                          })}
                        </div>
                      </section>
                    );
                  })}
                </div>
                <div className="quotation-detail-save">
                  <span>Para completar se requieren condición inicial/final, resultados estructurados y observaciones o evidencia.</span>
                  <div className="toolbar-actions">
                    <button className="table-button" onClick={() => openFieldSheetPdf('view')} type="button">
                      Ver PDF
                    </button>
                    <button className="table-button" onClick={handleDownloadFieldSheetPdf} type="button">
                      Descargar PDF
                    </button>
                    <button className="table-button" onClick={() => openFieldSheetPdf('print')} type="button">
                      Imprimir
                    </button>
                    {canUseTechnicalActions ? (
                      <>
                        <button className="table-button" disabled={isSaving} onClick={saveFieldSheet} type="button">
                          Guardar
                        </button>
                        <button className="primary-button" disabled={isSaving || !['draft', 'in_progress', 'rejected', 'returned_to_technician'].includes(selectedFieldSheet.status)} onClick={completeCurrentFieldSheet} type="button">
                          Completar
                        </button>
                        <button className="table-button" disabled={isSaving || selectedFieldSheet.status !== 'completed'} onClick={reviewCurrentFieldSheet} type="button">
                          Enviar a Captura
                        </button>
                      </>
                    ) : null}
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
                    <strong>Orden de trabajo</strong>
                    <span>OT {selectedFieldSheet.work_order_number ?? selectedOrder.work_order_number ?? '-'}</span>
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

      {selectedQualityCertificate ? (() => {
        const certificate = certificates.find((item) => item.id === selectedQualityCertificate.id) || selectedQualityCertificate;
        const item = equipment.find((equipmentItem) => equipmentItem.id === certificate.equipment_id);
        const sheet = certificate.field_sheet_id ? fieldSheets.find((candidate) => candidate.id === certificate.field_sheet_id) : null;
        const canApprove = ['ready_for_quality', 'quality_review'].includes(certificate.status);
        const canAuthenticate = Boolean(certificate.final_pdf_path) && ['quality_approved', 'approved', 'pdf_pending', 'pdf_uploaded'].includes(certificate.status) && !certificate.authenticated_pdf_path;
        const canRelease = Boolean(certificate.final_pdf_path && certificate.authenticated_pdf_path) && ['quality_approved', 'approved', 'pdf_pending', 'pdf_uploaded'].includes(certificate.status) && ['matched', 'warning', 'manual_accepted'].includes(certificate.match_status);
        return (
          <div className="modal-backdrop" role="presentation">
            <section aria-modal="true" className="client-modal field-sheet-modal" role="dialog">
              <div className="modal-header">
                <div>
                  <p>Revision de calidad</p>
                  <h2>{certificate.expected_folio || certificate.folio}</h2>
                </div>
                <button className="icon-button" onClick={() => setSelectedQualityCertificate(null)} type="button">
                  <X size={18} />
                </button>
              </div>
              <div className="quotation-commercial-grid service-order-info-grid">
                <article><span>Certificado</span><strong>{certificate.expected_folio || certificate.folio}</strong></article>
                <article><span>Equipo</span><strong>{item?.name || '-'}</strong></article>
                <article><span>Serie</span><strong>{item?.serial_number || '-'}</strong></article>
                <article><span>Hoja vinculada</span><strong>{sheet ? `Hoja ${sheet.id} · ${fieldSheetStatusLabels[sheet.status] ?? sheet.status}` : '-'}</strong></article>
                <article><span>PDF original</span><strong>{certificate.final_pdf_original_filename || (certificate.final_pdf_path ? 'Cargado' : 'Pendiente')}</strong></article>
                <article><span>Match</span><strong>{certificate.match_status || '-'}</strong></article>
                <article><span>Estado</span><strong>{certificateStatusLabels[certificate.status] ?? certificate.status}</strong></article>
                <article><span>Autenticacion</span><strong>{certificate.authentication_code || '-'}</strong></article>
              </div>
              <div className="quality-action-ribbon">
                <button className="table-button" disabled={!certificate.final_pdf_path} onClick={() => openOriginalCertificatePdf(certificate)} type="button">1. Ver PDF original</button>
                <button className="table-button" disabled={!certificate.final_pdf_path || isSaving} onClick={() => handleCertificateMatchValidation(certificate)} type="button">2. Validar match</button>
                <button className="table-button" disabled={!certificate.final_pdf_path || isSaving} onClick={() => handleCertificateMatchAcceptance(certificate)} type="button">3. Aceptar match manual</button>
                <button className="table-button" disabled={!canApprove || isSaving} onClick={() => handleCertificateWorkflow(certificate, 'quality-approve', `Certificado ${certificate.folio} aprobado`)} type="button">4. Aprobar</button>
                <button className="table-button" disabled={!canApprove || isSaving} onClick={() => handleCertificateWorkflow(certificate, 'quality-reject', `Certificado ${certificate.folio} rechazado`)} type="button">4. Rechazar</button>
                <button className="table-button" disabled={isSaving} onClick={() => handleCertificateWorkflow(certificate, 'return-to-technician', `Certificado ${certificate.folio} devuelto al tecnico`)} type="button">5. Regresar a tecnico</button>
                <button className="table-button" disabled={!canAuthenticate || isSaving} onClick={() => handleCertificateAuthentication(certificate)} type="button">6. Autenticar</button>
                <button className="table-button table-button--primary" disabled={!canRelease || isSaving} onClick={() => handleCertificateWorkflow(certificate, 'release-to-client', `Certificado ${certificate.folio} liberado al cliente`)} type="button">7. Liberar</button>
              </div>
              <div className="quotation-history-list">
                <article><strong>Creado</strong><span>{certificate.created_at ? new Date(certificate.created_at).toLocaleString('es-MX') : '-'}</span></article>
                <article><strong>PDF subido</strong><span>{certificate.final_pdf_uploaded_at ? new Date(certificate.final_pdf_uploaded_at).toLocaleString('es-MX') : '-'}</span></article>
                <article><strong>Enviado a calidad</strong><span>{certificate.sent_to_quality_at ? new Date(certificate.sent_to_quality_at).toLocaleString('es-MX') : '-'}</span></article>
                <article><strong>Revision calidad</strong><span>{certificate.quality_reviewed_at ? new Date(certificate.quality_reviewed_at).toLocaleString('es-MX') : '-'}</span></article>
                <article><strong>Autenticado</strong><span>{certificate.authenticated_pdf_generated_at ? new Date(certificate.authenticated_pdf_generated_at).toLocaleString('es-MX') : '-'}</span></article>
              </div>
              <pre className="match-details-panel">{JSON.stringify(certificate.match_details || {}, null, 2)}</pre>
            </section>
          </div>
        );
      })() : null}

      {returnToTechnicianRequest ? (
        <div className="modal-backdrop" role="presentation">
          <section aria-modal="true" className="client-modal confirm-dialog" role="dialog">
            <div className="section-heading confirm-dialog__header">
              <div>
                <p>Devolucion tecnica</p>
                <h2>Motivo obligatorio</h2>
              </div>
            </div>
            <div className="confirm-dialog__body">
              <p>Registra la causa de devolucion. La hoja volvera a estado editable y quedara evidencia en auditoria.</p>
              <textarea
                autoFocus
                className="form-textarea"
                onChange={(event) => setReturnToTechnicianReason(event.target.value)}
                placeholder="Describe el motivo para regresar al tecnico"
                rows={4}
                value={returnToTechnicianReason}
              />
            </div>
            <div className="confirm-dialog__actions">
              <button
                className="confirm-dialog__cancel"
                disabled={isSaving}
                onClick={() => {
                  setReturnToTechnicianRequest(null);
                  setReturnToTechnicianReason('');
                }}
                type="button"
              >
                Cancelar
              </button>
              <button
                className="confirm-dialog__confirm"
                disabled={isSaving}
                onClick={confirmReturnToTechnician}
                type="button"
              >
                {isSaving ? 'Procesando...' : 'Regresar al tecnico'}
              </button>
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


export default ServiceOrdersPage;
