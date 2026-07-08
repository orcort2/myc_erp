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
  listFieldSheetTemplates,
  listFieldSheets,
  listQuotations,
  listReferenceStandards,
  listServiceOrders,
  listUsers,
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
import { navigate } from '../utils/routing.js';
import {
  getFieldSheetTemplate,
  getFieldSheetTemplateLabel,
  normalizeTemplate,
  fieldSheetToForm,
  buildFieldSheetPayload,
  buildFieldSheetResultSections,
  getFieldSheetCompletionErrors,
  updateFieldSheetResultCell,
  updateFieldSheetResultsRowsForTemplate
} from '../utils/fieldSheets.js';
import { fieldSheetTemplateOptions } from '../constants/fieldSheetTemplates.js';
import { formatDate, getClientDisplayName } from '../utils/formatters.js';
import FieldSheetLayout from '../components/field-sheets/FieldSheetLayout.jsx';

function safeNumber(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function safeText(value, fallback = '-') {
  return value === undefined || value === null || value === '' ? fallback : value;
}

function getRoleNames(user) {
  return (user?.roles ?? []).map((role) => (role.name || '').toLowerCase());
}

function getUserRoleNames(user) {
  return (user?.roles ?? []).map((role) => role.name || '');
}

function isPrivilegedUser(user) {
  const roles = getRoleNames(user);
  return !roles.length || roles.some((role) => ['admin', 'administrador', 'administrator', 'desarrollador', 'developer'].includes(role));
}

function hasStageAccess(user, stage) {
  const roles = getRoleNames(user);
  if (isPrivilegedUser(user)) {
    return true;
  }
  if (stage === 'technical') return roles.some((role) => ['tecnico', 'técnico', 'technical'].includes(role));
  if (stage === 'capture') return roles.some((role) => ['captura', 'capture'].includes(role));
  if (stage === 'quality') return roles.some((role) => ['calidad', 'quality'].includes(role));
  return true;
}

function canManageServices(user) {
  const roles = getRoleNames(user);
  return isPrivilegedUser(user) || roles.some((role) => ['tecnico', 'técnico', 'technical', 'calidad', 'quality', 'comercial'].includes(role));
}

const calibrationScopeLabels = {
  traceable: 'Trazable',
  accredited_iso_17025: 'Acreditado ISO/IEC 17025',
  accredited_linked_lab: 'Vinculado',
};

const calibrationScopeBadgeLabels = {
  traceable: 'Trazables',
  accredited_iso_17025: 'Acreditados',
  accredited_linked_lab: 'Vinculados',
};

function ServiceOrdersPage({ user = null }) {
  const [serviceOrders, setServiceOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [users, setUsers] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [referenceStandards, setReferenceStandards] = useState([]);
  const [calibrationProcedures, setCalibrationProcedures] = useState([]);
  const [fieldSheetTemplates, setFieldSheetTemplates] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedEquipmentForSheet, setSelectedEquipmentForSheet] = useState(null);
  const [selectedEquipmentDetail, setSelectedEquipmentDetail] = useState(null);
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
  const [etsSearch, setEtsSearch] = useState('');
  const [fieldSheetWorkOrderFilter, setFieldSheetWorkOrderFilter] = useState('');
  const [isTechnicianPickerOpen, setIsTechnicianPickerOpen] = useState(false);
  const [technicianSearch, setTechnicianSearch] = useState('');
  const [technicianPage, setTechnicianPage] = useState(1);
  const [reopenedStages, setReopenedStages] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isEquipmentModalOpen, setIsEquipmentModalOpen] = useState(false);
  const [isFieldSheetModalOpen, setIsFieldSheetModalOpen] = useState(false);
  const [isFieldSheetCreateModalOpen, setIsFieldSheetCreateModalOpen] = useState(false);
  const [pendingFieldSheetEquipment, setPendingFieldSheetEquipment] = useState(null);
  const [fieldSheetCreateForm, setFieldSheetCreateForm] = useState({
    templateKey: 'anemometro',
    certificateClientMode: 'billing',
    certificateClientCompany: '',
    certificateClientAttention: '',
    certificateClientAddress: '',
    applyCertificateClientToOrder: true,
  });
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

  const usersById = useMemo(
    () => new Map(users.map((systemUser) => [systemUser.id, systemUser])),
    [users]
  );

  const technicianOptions = useMemo(
    () => users.filter((systemUser) => systemUser.is_active !== false && canManageServices(systemUser)),
    [users]
  );

  const quotationsById = useMemo(
    () => new Map(quotations.map((quotation) => [quotation.id, quotation])),
    [quotations]
  );

  const fieldSheetTemplatesByKey = useMemo(
    () => Object.fromEntries((fieldSheetTemplates || []).map((template) => [template.template_key || template.key, template])),
    [fieldSheetTemplates]
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

  const relatedWorkOrders = useMemo(() => {
    if (!selectedOrder) return [];
    const sameQuotation = selectedOrder.quotation_id
      ? serviceOrders.filter((order) => order.quotation_id === selectedOrder.quotation_id && order.is_active !== false)
      : [];
    const base = sameQuotation.length ? sameQuotation : [selectedOrder];
    return base
      .filter((order, index, list) => list.findIndex((candidate) => candidate.id === order.id) === index)
      .sort((left, right) => String(left.work_order_number || '').localeCompare(String(right.work_order_number || '')));
  }, [selectedOrder, serviceOrders]);

  const normalizedEtsSearch = etsSearch.trim().toLowerCase();

  const filteredSelectedEquipment = useMemo(() => {
    if (!normalizedEtsSearch) return selectedEquipment;
    return selectedEquipment.filter((item) => {
      const sheet = fieldSheetsByEquipmentId.get(item.id);
      const certificate = activeCertificatesByEquipmentId.get(item.id);
      return [
        selectedOrder?.work_order_number,
        item.name,
        item.brand,
        item.model,
        item.serial_number,
        item.internal_id,
        item.range_or_capacity,
        sheet?.id ? `hoja ${sheet.id}` : '',
        sheet?.work_order_number,
        certificate?.folio,
        certificate?.expected_folio,
        certificate?.final_pdf_original_filename,
        certificate?.authentication_code
      ].some((value) => String(value || '').toLowerCase().includes(normalizedEtsSearch));
    });
  }, [activeCertificatesByEquipmentId, fieldSheetsByEquipmentId, normalizedEtsSearch, selectedEquipment, selectedOrder]);

  const filteredSelectedCertificates = useMemo(() => {
    if (!normalizedEtsSearch) return selectedCertificates;
    return selectedCertificates.filter((certificate) => {
      const item = equipment.find((candidate) => candidate.id === certificate.equipment_id);
      const sheet = certificate.field_sheet_id ? fieldSheets.find((candidate) => candidate.id === certificate.field_sheet_id) : null;
      return [
        certificate.folio,
        certificate.expected_folio,
        certificate.authentication_code,
        certificate.final_pdf_original_filename,
        certificate.final_pdf_path,
        certificate.authenticated_pdf_path,
        item?.name,
        item?.serial_number,
        item?.internal_id,
        sheet?.id,
        sheet?.work_order_number
      ].some((value) => String(value || '').toLowerCase().includes(normalizedEtsSearch));
    });
  }, [equipment, fieldSheets, normalizedEtsSearch, selectedCertificates]);

  const filteredTechnicianOptions = useMemo(() => {
    const query = technicianSearch.trim().toLowerCase();
    const list = technicianOptions.filter((systemUser) => {
      if (!query) return true;
      return [
        systemUser.full_name,
        systemUser.email,
        ...getUserRoleNames(systemUser)
      ].some((value) => String(value || '').toLowerCase().includes(query));
    });
    return list;
  }, [technicianOptions, technicianSearch]);

  const paginatedTechnicianOptions = useMemo(() => {
    if (filteredTechnicianOptions.length <= 15) return filteredTechnicianOptions;
    const start = (technicianPage - 1) * 5;
    return filteredTechnicianOptions.slice(start, start + 5);
  }, [filteredTechnicianOptions, technicianPage]);

  const technicianPageCount = filteredTechnicianOptions.length > 15
    ? Math.max(Math.ceil(filteredTechnicianOptions.length / 5), 1)
    : 1;

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

  const selectedOrderCertificateCapacity = useMemo(() => {
    if (!selectedOrder) {
      return {
        traceable: { quoted: 0, used: 0, available: 0 },
        accredited_iso_17025: { quoted: 0, used: 0, available: 0 },
        accredited_linked_lab: { quoted: 0, used: 0, available: 0 },
        availableScopes: [],
        singleAvailableScope: null,
      };
    }

    const quoted = {
      traceable: 0,
      accredited_iso_17025: 0,
      accredited_linked_lab: 0,
    };
    (selectedOrder.items ?? []).forEach((item) => {
      if (item.calibration_scope && quoted[item.calibration_scope] !== undefined) {
        quoted[item.calibration_scope] += safeNumber(item.quantity);
      }
    });

    const used = {
      traceable: 0,
      accredited_iso_17025: 0,
      accredited_linked_lab: 0,
    };
    selectedCertificates.forEach((certificate) => {
      if (certificate.certificate_type === 'trazable') used.traceable += 1;
      if (certificate.certificate_type === 'acreditado') used.accredited_iso_17025 += 1;
      if (certificate.certificate_type === 'vinculado') used.accredited_linked_lab += 1;
    });

    const capacity = {
      traceable: {
        quoted: quoted.traceable,
        used: used.traceable,
        available: Math.max(quoted.traceable - used.traceable, 0),
      },
      accredited_iso_17025: {
        quoted: quoted.accredited_iso_17025,
        used: used.accredited_iso_17025,
        available: Math.max(quoted.accredited_iso_17025 - used.accredited_iso_17025, 0),
      },
      accredited_linked_lab: {
        quoted: quoted.accredited_linked_lab,
        used: used.accredited_linked_lab,
        available: Math.max(quoted.accredited_linked_lab - used.accredited_linked_lab, 0),
      },
    };

    const availableScopes = Object.entries(capacity)
      .filter(([, item]) => item.available > 0)
      .map(([scope]) => scope);

    return {
      ...capacity,
      availableScopes,
      singleAvailableScope: availableScopes.length === 1 ? availableScopes[0] : null,
    };
  }, [selectedCertificates, selectedOrder]);

  const selectedStageState = useMemo(() => {
    if (!selectedOrder) return {};
    const reopened = reopenedStages[selectedOrder.id] ?? {};
    const summaryReady = Boolean(selectedOrder.agenda_date && selectedOrder.service_date && selectedOrder.technician_id);
    const equipmentReady = selectedEquipment.length > 0 && selectedEquipment.length <= 10;
    const sheetsStarted = selectedFieldSheets.length > 0;
    const usableSheets = selectedFieldSheets.filter((sheet) => ['completed', 'under_review', 'approved', 'returned_to_technician'].includes(sheet.status)).length;
    const captureReady = usableSheets > 0 || selectedCertificates.length > 0;
    const captureComplete = selectedCertificates.length > 0 && selectedCertificates.some((certificate) => certificate.final_pdf_path);
    const qualityReady = selectedCertificates.some((certificate) => ['ready_for_quality', 'quality_review', 'quality_approved', 'pdf_pending', 'pdf_uploaded', 'released_to_client'].includes(certificate.status));
    const qualityComplete = selectedCertificates.length > 0 && selectedCertificates.every((certificate) => ['quality_approved', 'pdf_pending', 'pdf_uploaded', 'released_to_client'].includes(certificate.status));
    const certificateReady = selectedCertificates.length > 0;
    const certificateComplete = selectedCertificates.length > 0 && selectedCertificates.every((certificate) => certificate.authenticated_pdf_path || certificate.status === 'released_to_client');
    const documentsReady = certificateComplete || selectedFieldSheets.length > 0 || Boolean(selectedOrder.quotation_id);
    const billingReady = selectedCertificates.some((certificate) => certificate.status === 'released_to_client') || ['pending_payment', 'released', 'closed'].includes(selectedOrder.status);
    const billingComplete = !selectedOrder.requires_payment || ['released', 'closed'].includes(selectedOrder.status);
    const states = {
      info: {
        label: reopened.info ? 'Reabierta' : summaryReady ? 'Lista' : 'En proceso',
        status: reopened.info ? 'reopened' : summaryReady ? 'done' : 'active',
        ready: summaryReady,
      },
      equipment: {
        label: reopened.equipment ? 'Reabierta' : equipmentReady ? 'Lista' : summaryReady ? 'En proceso' : 'Pendiente',
        status: reopened.equipment ? 'reopened' : equipmentReady ? 'done' : summaryReady ? 'active' : 'blocked',
        ready: equipmentReady,
      },
      'field-sheet': {
        label: sheetsStarted ? (usableSheets ? 'En proceso' : 'Iniciada') : equipmentReady ? 'Pendiente' : 'Bloqueada',
        status: sheetsStarted ? (usableSheets ? 'active' : 'reopened') : equipmentReady ? 'pending' : 'blocked',
        ready: sheetsStarted,
      },
      capture: {
        label: captureComplete ? 'En proceso' : captureReady ? 'Disponible' : 'Bloqueada',
        status: captureComplete ? 'active' : captureReady ? 'pending' : 'blocked',
        ready: captureReady,
      },
      quality: {
        label: qualityComplete ? 'Lista' : qualityReady ? 'En proceso' : 'Pendiente',
        status: qualityComplete ? 'done' : qualityReady ? 'active' : 'pending',
        ready: qualityReady,
      },
      certificates: {
        label: certificateComplete ? 'Lista' : certificateReady ? 'En proceso' : 'Pendiente',
        status: certificateComplete ? 'done' : certificateReady ? 'active' : 'pending',
        ready: certificateReady,
      },
      documents: {
        label: documentsReady ? 'Disponible' : 'Pendiente',
        status: documentsReady ? 'active' : 'pending',
        ready: documentsReady,
      },
      history: {
        label: 'Disponible',
        status: 'active',
        ready: true,
      },
      billing: {
        label: billingComplete ? 'Lista' : billingReady ? 'En proceso' : 'Pendiente',
        status: billingComplete ? 'done' : billingReady ? 'active' : 'pending',
        ready: billingReady,
      },
    };
    return states;
  }, [selectedOrder, selectedEquipment, selectedFieldSheets, selectedCertificates, reopenedStages]);

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

  function getUserDisplayNameById(userId, fallback = 'Sin asignar') {
    if (!userId) return fallback;
    const systemUser = usersById.get(userId);
    return systemUser?.full_name || systemUser?.email || fallback;
  }

  function getOrderAdvisorName(order) {
    return order.advisor_name || getUserDisplayNameById(order.advisor_id, 'Sin asesor');
  }

  function getOrderTechnicianName(order) {
    return order.technician_name || getUserDisplayNameById(order.technician_id, 'Sin asignar');
  }

  function markStageVisual(stage, message) {
    if (!selectedOrder) return;
    setReopenedStages((current) => ({
      ...current,
      [selectedOrder.id]: {
        ...(current[selectedOrder.id] ?? {}),
        [stage]: false,
      },
    }));
    setNotice(message);
  }

  function reopenStageVisual(stage, label) {
    if (!selectedOrder) return;
    setReopenedStages((current) => ({
      ...current,
      [selectedOrder.id]: {
        ...(current[selectedOrder.id] ?? {}),
        [stage]: true,
      },
    }));
    setNotice(`${label} reabierta visualmente. La auditoria formal queda pendiente de endpoint especifico.`);
  }

  function openTechnicianPicker() {
    setTechnicianSearch('');
    setTechnicianPage(1);
    setIsTechnicianPickerOpen(true);
  }

  function selectTechnician(systemUser) {
    updateOrderForm('technicianId', systemUser ? String(systemUser.id) : '');
    setIsTechnicianPickerOpen(false);
    setTechnicianSearch('');
    setTechnicianPage(1);
  }

  function openQuotationFromEts() {
    if (!selectedOrder?.quotation_id) {
      setError('Este ETS no tiene cotizacion vinculada.');
      return;
    }
    window.sessionStorage.setItem('myc:openQuotationId', String(selectedOrder.quotation_id));
    navigate('/dashboard#cotizaciones');
  }

  function openTabFromSummary(tab, options = {}) {
    if (options.workOrderNumber) {
      setFieldSheetWorkOrderFilter(String(options.workOrderNumber));
    } else if (tab !== 'field-sheet') {
      setFieldSheetWorkOrderFilter('');
    }
    setActiveTab(tab);
  }

  function openEquipmentDetail(item) {
    setSelectedEquipmentDetail(item);
    setError('');
    setNotice('');
  }

  function closeEquipmentDetail() {
    setSelectedEquipmentDetail(null);
  }

  function editEquipmentFromDetail(item) {
    closeEquipmentDetail();
    openEquipmentModal(item);
  }

  function setEquipmentConditionPreset(kind) {
    if (kind === 'good') {
      updateEquipmentForm('initialCondition', 'Equipo recibido en buen estado general.');
      return;
    }
    updateEquipmentForm('initialCondition', 'Equipo recibido con anomalías visibles.');
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
        fieldSheetTemplatesResult,
        fieldSheetResult,
        certificatesResult,
        referenceStandardsResult,
        proceduresResult,
        usersResult
      ] = await Promise.all([
        listServiceOrders(),
        listClients(),
        listQuotations(),
        listEquipment(),
        listFieldSheetTemplates(),
        listFieldSheets(),
        listCertificates(),
        listReferenceStandards(),
        listCalibrationProcedures(),
        listUsers().catch(() => [])
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
      setFieldSheetTemplates(Array.isArray(fieldSheetTemplatesResult) ? fieldSheetTemplatesResult : []);
      setFieldSheets(Array.isArray(fieldSheetResult) ? fieldSheetResult : []);
      setCertificates(Array.isArray(certificatesResult) ? certificatesResult : []);
      setReferenceStandards(Array.isArray(referenceStandardsResult) ? referenceStandardsResult : []);
      setCalibrationProcedures(Array.isArray(proceduresResult) ? proceduresResult : []);
      setUsers(Array.isArray(usersResult) ? usersResult : []);
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
    setTechnicianPage(1);
  }, [technicianSearch]);

  useEffect(() => {
    function handleEscape(event) {
      if (event.key !== 'Escape') return;
      if (isTechnicianPickerOpen) {
        setIsTechnicianPickerOpen(false);
      } else if (selectedEquipmentDetail) {
        closeEquipmentDetail();
      } else if (isFieldSheetModalOpen) {
        closeFieldSheetModal();
      } else if (isEquipmentModalOpen) {
        closeEquipmentModal();
      } else if (isDetailOpen) {
        closeOrderDetail();
      }
    }

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isDetailOpen, isEquipmentModalOpen, isFieldSheetModalOpen, isTechnicianPickerOpen, selectedEquipmentDetail]);

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
    setEtsSearch('');
    setFieldSheetWorkOrderFilter('');
    setIsDetailOpen(true);
    setError('');
    setNotice('');
  }

  function closeOrderDetail() {
    setIsDetailOpen(false);
    setSelectedOrder(null);
    setSelectedEquipmentForSheet(null);
    setSelectedEquipmentDetail(null);
    setSelectedFieldSheet(null);
    setOrderForm(emptyServiceOrderForm);
    setEquipmentForm(emptyEquipmentForm);
    setFieldSheetForm(emptyFieldSheetForm);
    setEditingEquipmentId(null);
    setActiveTab('info');
    setEtsSearch('');
    setFieldSheetWorkOrderFilter('');
    setIsTechnicianPickerOpen(false);
    setFieldSheetTab('technical');
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
        serviceOrderItemId: item.service_order_item_id ? String(item.service_order_item_id) : '',
        certificateScope: item.calibration_scope ?? selectedOrderCertificateCapacity.singleAvailableScope ?? 'traceable',
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
      setEquipmentForm({
        ...emptyEquipmentForm,
        certificateScope:
          selectedOrderCertificateCapacity.singleAvailableScope ??
          (selectedOrderCertificateCapacity.availableScopes.length > 1 ? '' : emptyEquipmentForm.certificateScope),
      });
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
    if (!editingEquipmentId && !equipmentForm.certificateScope) {
      setError('Selecciona el tipo de certificado para este equipo.');
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const payload = {
        service_order_id: selectedOrder.id,
        calibration_scope: equipmentForm.certificateScope || null,
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
      title: 'Eliminar equipo',
      message: `El equipo ${item.name} se eliminará de la operación visible.\nNo se eliminará físicamente y se recalcularán los contadores de la orden.`,
      confirmText: 'Eliminar equipo',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        try {
          await deleteEquipment(item.id);
          setEquipment((current) => current.filter((equipmentItem) => equipmentItem.id !== item.id));
          setNotice('Equipo eliminado de la operación visible');
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
        setFieldSheetTab('technical');
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
        setFieldSheetTab('technical');
        setIsFieldSheetModalOpen(true);
        return;
      }

      const inheritedCertificateClient = selectedFieldSheets
        .filter((sheet) => sheet.apply_certificate_client_to_order && sheet.certificate_client_mode === 'different')
        .sort((left, right) => new Date(right.created_at || 0) - new Date(left.created_at || 0))[0];

      setPendingFieldSheetEquipment(item);
      setFieldSheetCreateForm({
        templateKey: 'anemometro',
        certificateClientMode: inheritedCertificateClient?.certificate_client_mode ?? 'billing',
        certificateClientCompany: inheritedCertificateClient?.certificate_client_company ?? '',
        certificateClientAttention: inheritedCertificateClient?.certificate_client_attention ?? '',
        certificateClientAddress: inheritedCertificateClient?.certificate_client_address ?? '',
        applyCertificateClientToOrder: inheritedCertificateClient?.apply_certificate_client_to_order ?? true,
      });
      setIsFieldSheetCreateModalOpen(true);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

      async function confirmCreateFieldSheet() {
    if (!pendingFieldSheetEquipment) return;

    setIsSaving(true);
    setError('');
    setNotice('');

    try {
      const sheet = await createFieldSheet({
        equipment_id: pendingFieldSheetEquipment.id,
        template_key: fieldSheetCreateForm.templateKey,
        certificate_client_mode: fieldSheetCreateForm.certificateClientMode,
        certificate_client_company: fieldSheetCreateForm.certificateClientCompany || null,
        certificate_client_attention: fieldSheetCreateForm.certificateClientAttention || null,
        certificate_client_address: fieldSheetCreateForm.certificateClientAddress || null,
        apply_certificate_client_to_order: Boolean(fieldSheetCreateForm.applyCertificateClientToOrder),
      });

      const nextForm = fieldSheetToForm(sheet);

      const equipmentName = pendingFieldSheetEquipment.name;

      setSelectedFieldSheet(sheet);
      setFieldSheetForm(nextForm);
      setFieldSheetCertificateType('trazable');
      setFieldSheetPatternSelection(null);
      setFieldSheetTab('technical');

      setIsFieldSheetCreateModalOpen(false);
      setPendingFieldSheetEquipment(null);

      setFieldSheets((current) => [sheet, ...current]);
      setNotice(`Hoja de campo creada para ${equipmentName}`);

      await loadServiceOrderData();

      setIsFieldSheetModalOpen(true);
    } catch (requestError) {
      if (
        requestError.message.includes('ya tiene') ||
        requestError.message.includes('409')
      ) {
        await loadServiceOrderData();
        setError('La hoja ya existe. Recarga el ETS y vuelve a abrirla.');
        return;
      }

      setError(requestError.message);
    } finally {
      setIsSaving(false);
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

  function updateFieldSheetCreateForm(field, value) {
    setFieldSheetCreateForm((current) => ({
      ...current,
      [field]: value,
    }));
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
    setFieldSheetForm((current) =>
      updateFieldSheetResultsRowsForTemplate(current, templateKey, fieldSheetTemplatesByKey)
    );
  }

  function updateFieldSheetResult(sectionKey, rowNumber, field, value) {
    setFieldSheetForm((current) => ({
      ...current,
      resultsRows: updateFieldSheetResultCell(
        current.resultsRows,
        sectionKey,
        rowNumber,
        field,
        value,
      )
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
        buildFieldSheetPayload(fieldSheetForm, fieldSheetTemplatesByKey)
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
    const missing = getFieldSheetCompletionErrors(fieldSheetForm, selectedFieldSheet?.template_definition
      ? { [fieldSheetForm.templateKey || 'general']: selectedFieldSheet.template_definition }
      : fieldSheetTemplatesByKey);
    if (missing.length) {
      setError(`No se puede completar. Faltan: ${missing.join(', ')}.`);
      setFieldSheetTab('technical');
      return;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const saved = await updateFieldSheet(
        selectedFieldSheet.id,
        buildFieldSheetPayload(fieldSheetForm, fieldSheetTemplatesByKey),
      );
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
      title: 'Eliminar orden de servicio',
      message: `La orden ${selectedOrder.folio} se eliminará de la operación visible.\nNo se eliminará físicamente: se conservará trazabilidad y el backend validará equipos, hojas y certificados relacionados.`,
      confirmText: 'Eliminar',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        try {
          await deleteServiceOrder(selectedOrder.id);
          closeOrderDetail();
          setNotice('Orden de servicio eliminada de la operación visible');
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
      title: 'Eliminar hoja de campo',
      message: `La hoja de campo #${selectedFieldSheet.id} se eliminará de la operación visible.\nNo se eliminará físicamente y puede afectar certificados relacionados.`,
      confirmText: 'Eliminar hoja',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        setIsSaving(true);
        try {
          await deleteFieldSheet(selectedFieldSheet.id);
          closeFieldSheetModal();
          setNotice('Hoja de campo eliminada de la operación visible');
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
                  <span>{getOrderTechnicianName(order)}</span>
                  <span>{formatDate(order.service_date || order.agenda_date)}</span>
                  <span>{metrics.equipmentCount}</span>
                  <span>{metrics.fieldSheetsDone}/{metrics.fieldSheetsCount}</span>
                  <span>{metrics.certificatesExpected}</span>
                  <span>{metrics.pdfUploaded}</span>
                  <span>{metrics.capturePending}</span>
                  <span>{metrics.qualityPending}</span>
                  <span>{metrics.advance}%</span>
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

            <div className="ets-modal-action-ribbon" aria-label="Acciones principales del ETS">
              <button className="table-button" onClick={() => openWorkOrderPdf('view')} type="button">
                Ver orden PDF
              </button>
              <button className="table-button" onClick={handleDownloadWorkOrderPdf} type="button">
                Descargar PDF
              </button>
              <button className="table-button" onClick={() => openWorkOrderPdf('print')} type="button">
                Imprimir
              </button>
              <button className="primary-button" disabled={isSaving || activeTab !== 'info'} form="service-order-summary-form" type="submit">
                {isSaving ? 'Guardando...' : 'Guardar cambios'}
              </button>
              <button className="icon-text-button" onClick={closeOrderDetail} type="button">
                Cerrar
              </button>
            </div>

            <label className="ets-expedient-search">
              <span>Buscar dentro del ETS</span>
              <input
                onChange={(event) => setEtsSearch(event.target.value)}
                placeholder="OT, equipo, serie, ID interno, hoja, certificado, PDF o folio"
                type="search"
                value={etsSearch}
              />
            </label>

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
                  onClick={() => openTabFromSummary(key)}
                  type="button"
                >
                  <span>{label}</span>
                  <small className={`ets-stage-badge is-${selectedStageState[key]?.status ?? 'pending'}`}>
                    {selectedStageState[key]?.label ?? 'Pendiente'}
                  </small>
                </button>
              ))}
            </div>

            {activeTab === 'info' ? (
              <>
                <form className="quotation-detail-form" id="service-order-summary-form" onSubmit={handleOrderSubmit}>
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
                          ['Cotización', Boolean(selectedOrder.quotation_id), 'done'],
                          ['Resumen', selectedStageState.info?.ready, selectedStageState.info?.status],
                          ['Equipos', selectedStageState.equipment?.ready, selectedStageState.equipment?.status],
                          ['Hojas', selectedStageState['field-sheet']?.ready, selectedStageState['field-sheet']?.status],
                          ['Captura', selectedStageState.capture?.ready, selectedStageState.capture?.status],
                          ['Calidad', selectedStageState.quality?.ready, selectedStageState.quality?.status],
                          ['PDF autenticado', selectedOrderMetrics.certificatesExpected > 0 && selectedOrderMetrics.authenticated === selectedOrderMetrics.certificatesExpected, selectedOrderMetrics.authenticated ? 'done' : 'pending'],
                          ['Facturación', !selectedOrderMetrics.billingPending, selectedStageState.billing?.status],
                          ['Cierre', selectedOrder.status === 'closed']
                        ].map(([label, done, state]) => (
                          <span className={`ets-stage ${done ? 'is-done' : ''} is-${state ?? 'pending'}`} key={label}>{label}</span>
                        ))}
                      </div>
                    </div>
                    <div className="quotation-commercial-grid service-order-info-grid">
                      <article>
                        <span>Folio OS</span>
                        <strong>{selectedOrder.folio}</strong>
                      </article>
                      <article className="ets-summary-work-orders">
                        <span>Ordenes de trabajo</span>
                        <div>
                          {relatedWorkOrders.map((order) => (
                            <button
                              className="ets-summary-link"
                              key={order.id}
                              onClick={() => openTabFromSummary('field-sheet', { workOrderNumber: order.work_order_number })}
                              type="button"
                            >
                              <strong>OT {order.work_order_number ?? '-'}</strong>
                              <small>{getOrderEquipmentCount(order)} equipos</small>
                            </button>
                          ))}
                        </div>
                      </article>
                      <article>
                        <span>Cliente</span>
                        <strong>{getClientDisplayName(clientsById.get(selectedOrder.client_id))}</strong>
                      </article>
                      <article className="ets-summary-card--clickable">
                        <span>Cotizacion origen</span>
                        <strong>{quotationsById.get(selectedOrder.quotation_id)?.folio || '-'}</strong>
                        <button className="table-button" disabled={!selectedOrder.quotation_id} onClick={openQuotationFromEts} type="button">
                          Abrir cotizacion
                        </button>
                      </article>
                      <article>
                        <span>Equipos esperados desde cotizacion</span>
                        <strong>{safeNumber(selectedOrderMetrics.expectedEquipment)}</strong>
                      </article>
                      <button className="ets-summary-card" onClick={() => openTabFromSummary('equipment')} type="button">
                        <span>Equipos registrados</span>
                        <strong>{selectedEquipment.length} / 10</strong>
                      </button>
                      <article>
                        <span>Asesor</span>
                        <strong>{getOrderAdvisorName(selectedOrder)}</strong>
                      </article>
                      <article>
                        <span>Estado actual</span>
                        <strong>{serviceOrderStatusLabels[selectedOrder.status] ?? selectedOrder.status}</strong>
                      </article>
                      <article className="ets-technician-card">
                        <span>Tecnico</span>
                        <strong>{orderForm.technicianId ? getUserDisplayNameById(Number(orderForm.technicianId)) : 'Sin asignar'}</strong>
                        <button className="table-button" onClick={openTechnicianPicker} type="button">
                          Elegir tecnico
                        </button>
                      </article>
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
                      <button className="ets-summary-card" onClick={() => openTabFromSummary('field-sheet')} type="button">
                        <span>Hojas creadas</span>
                        <strong>{safeNumber(selectedOrderMetrics.fieldSheetsCount)}</strong>
                      </button>
                      <article>
                        <span>Hojas completadas</span>
                        <strong>{safeNumber(selectedOrderMetrics.fieldSheetsDone)}</strong>
                      </article>
                      <button className="ets-summary-card" onClick={() => openTabFromSummary('certificates')} type="button">
                        <span>Certificados esperados</span>
                        <strong>{safeNumber(selectedOrderMetrics.certificatesExpected)}</strong>
                      </button>
                      <button className="ets-summary-card" onClick={() => openTabFromSummary('documents')} type="button">
                        <span>PDFs subidos</span>
                        <strong>{safeNumber(selectedOrderMetrics.pdfUploaded)}</strong>
                      </button>
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
                    <span>La etapa queda lista cuando exista fecha de agenda, fecha de servicio y tecnico asignado.</span>
                    <div className="toolbar-actions">
                      <button
                        className="primary-button"
                        disabled={!orderForm.agendaDate || !orderForm.serviceDate || !orderForm.technicianId || isSaving}
                        type="submit"
                      >
                        {selectedStageState.info?.ready ? 'Resumen listo' : 'Marcar resumen listo'}
                      </button>
                      {selectedStageState.info?.ready ? (
                        <button className="table-button" onClick={() => setActiveTab('equipment')} type="button">
                          Siguiente: Equipos
                        </button>
                      ) : null}
                      {isPrivilegedUser(user) && selectedStageState.info?.ready ? (
                        <button className="table-button" onClick={() => reopenStageVisual('info', 'Resumen')} type="button">
                          Reabrir resumen
                        </button>
                      ) : null}
                    </div>
                  </div>
                </form>

                <section className="danger-zone">
                  <div className="danger-zone__copy">
                    <p>Zona de eliminacion operativa</p>
                    <span>La orden se elimina de la operación visible, pero se conserva trazabilidad y el backend valida dependencias activas.</span>
                  </div>
                  <div className="toolbar-actions">
                    <button className="table-button table-button--danger" onClick={handleDeleteServiceOrder} type="button">
                      Eliminar
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
                    <span className={`ets-inline-stage is-${selectedStageState.equipment?.status ?? 'pending'}`}>
                      {selectedStageState.equipment?.label ?? 'Pendiente'}
                    </span>
                  </div>
                  <div className="toolbar-actions">
                    {selectedEquipment.length > 0 && selectedEquipment.length <= 10 ? (
                      <button className="table-button table-button--primary" onClick={() => markStageVisual('equipment', 'Etapa Equipos marcada como lista. Hojas de Campo queda destacada como siguiente etapa.')} type="button">
                        Marcar equipos listos
                      </button>
                    ) : null}
                    {isPrivilegedUser(user) && selectedStageState.equipment?.ready ? (
                      <button className="table-button" onClick={() => reopenStageVisual('equipment', 'Equipos')} type="button">
                        Reabrir equipos
                      </button>
                    ) : null}
                    {canUseTechnicalActions ? (
                      <button className="primary-button" disabled={selectedEquipment.length >= 10} onClick={() => openEquipmentModal()} type="button">
                        + Agregar equipo
                      </button>
                    ) : null}
                  </div>
                </div>
                <div className="ets-metric-strip">
                  <span className="ets-metric-badge"><strong>{safeNumber(selectedOrderMetrics.expectedEquipment)}</strong>Esperados cotizacion</span>
                  <span className="ets-metric-badge"><strong>{selectedEquipment.length}</strong>Registrados</span>
                  <span className="ets-metric-badge"><strong>{selectedEquipment.length} / 10</strong>Capacidad OT</span>
                  <span className="ets-metric-badge"><strong>{selectedFieldSheets.length} / 10</strong>Hojas</span>
                  {['traceable', 'accredited_iso_17025', 'accredited_linked_lab'].map((scope) => (
                    <span className="ets-metric-badge" key={scope}>
                      <strong>
                        {safeNumber(selectedOrderCertificateCapacity[scope]?.used)} / {safeNumber(selectedOrderCertificateCapacity[scope]?.quoted)}
                      </strong>
                      {calibrationScopeBadgeLabels[scope]}
                    </span>
                  ))}
                </div>
                {selectedEquipment.length >= 10 ? (
                  <div className="clients-empty">Maximo 10 equipos por Orden de Trabajo.</div>
                ) : null}
                <div className="ets-stage-note">
                  Orden de trabajo pendiente de firma: este control queda preparado como estado visual hasta definir el campo documental formal.
                </div>
                <div className="ets-equipment-card-grid">
                  {filteredSelectedEquipment.length ? (
                    filteredSelectedEquipment.map((item) => {
                      const sheet = fieldSheetsByEquipmentId.get(item.id);
                      const certificate = activeCertificatesByEquipmentId.get(item.id);
                      return (
                        <button className="ets-equipment-card" key={item.id} onClick={() => openEquipmentDetail(item)} type="button">
                          <span className="ets-equipment-card__eyebrow">{calibrationScopeLabels[item.calibration_scope] || 'Sin tipo'}</span>
                          <strong>{item.name}</strong>
                          <mark className={`quotation-status status-${item.status}`}>
                            {equipmentStatusLabels[item.status] ?? item.status}
                          </mark>
                          <dl>
                            <div>
                              <dt>Marca</dt>
                              <dd>{item.brand || '-'}</dd>
                            </div>
                            <div>
                              <dt>Modelo</dt>
                              <dd>{item.model || '-'}</dd>
                            </div>
                            <div>
                              <dt>Serie</dt>
                              <dd>{item.serial_number || '-'}</dd>
                            </div>
                            <div>
                              <dt>ID interno</dt>
                              <dd>{item.internal_id || '-'}</dd>
                            </div>
                            <div>
                              <dt>Folio reservado</dt>
                              <dd>{certificate?.expected_folio || certificate?.folio || '-'}</dd>
                            </div>
                            <div>
                              <dt>Hoja</dt>
                              <dd>{sheet ? `Hoja ${sheet.id}` : 'Pendiente'}</dd>
                            </div>
                            <div>
                              <dt>Certificado</dt>
                              <dd>{certificate ? certificateStatusLabels[certificate.status] ?? certificate.status : 'Pendiente'}</dd>
                            </div>
                            <div>
                              <dt>PDF</dt>
                              <dd>{certificate?.authenticated_pdf_path ? 'Autenticado' : certificate?.final_pdf_path ? 'Original' : 'Pendiente'}</dd>
                            </div>
                          </dl>
                        </button>
                      );
                    })
                  ) : selectedEquipment.length && etsSearch ? (
                    <div className="clients-empty">No hay equipos que coincidan con la busqueda dentro de este ETS.</div>
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
                <div className="ets-stage-note">
                  Captura puede avanzar con hojas utilizables o certificados esperados disponibles; el tecnico puede seguir completando hojas en paralelo.
                </div>
                {fieldSheetWorkOrderFilter ? (
                  <div className="ets-stage-note">
                    Mostrando hojas de la OT {fieldSheetWorkOrderFilter}.
                    <button className="table-button" onClick={() => setFieldSheetWorkOrderFilter('')} type="button">Ver todas</button>
                  </div>
                ) : null}
                {selectedEquipment.length ? (
                  <div className="field-sheet-prep-list">
                    {filteredSelectedEquipment
                      .filter((item) => {
                        if (!fieldSheetWorkOrderFilter) return true;
                        const sheet = fieldSheetsByEquipmentId.get(item.id);
                        return String(sheet?.work_order_number || selectedOrder.work_order_number || '') === String(fieldSheetWorkOrderFilter);
                      })
                      .map((item) => (
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
                <div className="ets-stage-note">
                  La carga de PDFs no espera el cierre total de hojas. Cada certificado puede iniciar captura, cargar PDF y pasar a calidad conforme este listo.
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
                  {filteredSelectedCertificates.length ? (
                    filteredSelectedCertificates.map((certificate) => {
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
                  {filteredSelectedCertificates.length ? (
                    filteredSelectedCertificates.map((certificate) => {
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
                  {filteredSelectedCertificates.length ? (
                    filteredSelectedCertificates.map((certificate) => {
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
                <div className="settings-filters__actions">
                  <button
                    className="primary-button"
                    onClick={() => {
                      window.localStorage.setItem('myc_billing_order_id', String(selectedOrder.id));
                      navigate('/dashboard#facturacion');
                    }}
                    type="button"
                  >
                    Crear factura
                  </button>
                </div>
              </section>
            ) : null}
          </section>
        </div>
      ) : null}

      {isTechnicianPickerOpen ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-client-picker" aria-modal="true" role="dialog">
            <div className="quotation-detail-header">
              <div>
                <p>Servicios / ETS</p>
                <h2>Elegir tecnico</h2>
                <span>Usuarios con permiso operativo para atender servicios</span>
              </div>
              <button className="icon-text-button" onClick={() => setIsTechnicianPickerOpen(false)} type="button">
                Cerrar
              </button>
            </div>
            <label className="quotation-client-search">
              <span>Buscar usuario</span>
              <input
                autoFocus
                onChange={(event) => setTechnicianSearch(event.target.value)}
                placeholder="Nombre, correo o rol"
                type="search"
                value={technicianSearch}
              />
            </label>
            <div className="quotation-client-results">
              <button className="quotation-client-result" onClick={() => selectTechnician(null)} type="button">
                <strong>Sin asignar</strong>
                <span>Deja el tecnico pendiente.</span>
              </button>
              {paginatedTechnicianOptions.length ? (
                paginatedTechnicianOptions.map((systemUser) => (
                  <button
                    className="quotation-client-result"
                    key={systemUser.id}
                    onClick={() => selectTechnician(systemUser)}
                    type="button"
                  >
                    <strong>{systemUser.full_name || systemUser.email}</strong>
                    <span>{systemUser.email}</span>
                    <small>{getUserRoleNames(systemUser).join(', ') || 'Sin rol'}</small>
                  </button>
                ))
              ) : (
                <div className="clients-empty">No hay usuarios operativos que coincidan con la busqueda.</div>
              )}
            </div>
            {filteredTechnicianOptions.length > 15 ? (
              <div className="ets-picker-pagination">
                <button className="table-button" disabled={technicianPage <= 1} onClick={() => setTechnicianPage((page) => Math.max(page - 1, 1))} type="button">
                  Anterior
                </button>
                <span>Pagina {technicianPage} de {technicianPageCount}</span>
                <button className="table-button" disabled={technicianPage >= technicianPageCount} onClick={() => setTechnicianPage((page) => Math.min(page + 1, technicianPageCount))} type="button">
                  Siguiente
                </button>
              </div>
            ) : null}
          </section>
        </div>
      ) : null}

      {selectedEquipmentDetail ? (
        <div className="modal-backdrop" role="presentation">
          <section className="client-modal quotation-detail-modal" aria-modal="true" role="dialog">
            <div className="quotation-detail-header">
              <div>
                <p>Detalle de equipo</p>
                <h2>{selectedEquipmentDetail.name}</h2>
                <span>{selectedOrder?.folio} · OT {selectedOrder?.work_order_number ?? '-'}</span>
              </div>
              <mark className={`quotation-status quotation-status--large status-${selectedEquipmentDetail.status}`}>
                {equipmentStatusLabels[selectedEquipmentDetail.status] ?? selectedEquipmentDetail.status}
              </mark>
              <button className="icon-text-button" onClick={closeEquipmentDetail} type="button">
                Cerrar
              </button>
            </div>
            {(() => {
              const sheet = fieldSheetsByEquipmentId.get(selectedEquipmentDetail.id);
              const certificate = activeCertificatesByEquipmentId.get(selectedEquipmentDetail.id);
              return (
                <>
                  <div className="quotation-commercial-grid service-order-info-grid">
                    <article>
                      <span>Instrumento</span>
                      <strong>{selectedEquipmentDetail.name}</strong>
                    </article>
                    <article>
                      <span>Marca / modelo</span>
                      <strong>{selectedEquipmentDetail.brand || '-'} · {selectedEquipmentDetail.model || '-'}</strong>
                    </article>
                    <article>
                      <span>Serie</span>
                      <strong>{selectedEquipmentDetail.serial_number || '-'}</strong>
                    </article>
                    <article>
                      <span>ID interno</span>
                      <strong>{selectedEquipmentDetail.internal_id || '-'}</strong>
                    </article>
                    <article>
                      <span>Tipo certificado</span>
                      <strong>{calibrationScopeLabels[selectedEquipmentDetail.calibration_scope] || '-'}</strong>
                    </article>
                    <article>
                      <span>Folio reservado</span>
                      <strong>{certificate?.expected_folio || certificate?.folio || '-'}</strong>
                    </article>
                    <article>
                      <span>Hoja</span>
                      <strong>{sheet ? `Hoja ${sheet.id}` : 'Pendiente'}</strong>
                    </article>
                    <article>
                      <span>Certificado</span>
                      <strong>{certificate ? certificateStatusLabels[certificate.status] ?? certificate.status : 'Pendiente'}</strong>
                    </article>
                    <article>
                      <span>PDF</span>
                      <strong>{certificate?.authenticated_pdf_path ? 'Autenticado' : certificate?.final_pdf_path ? 'Original cargado' : 'Pendiente'}</strong>
                    </article>
                  </div>
                  <section className="quotation-section">
                    <div className="quotation-section__title">
                      <p>Condicion y notas</p>
                      <h3>Recepcion tecnica</h3>
                    </div>
                    <div className="ets-equipment-notes">
                      <article>
                        <span>Condicion inicial</span>
                        <p>{selectedEquipmentDetail.initial_condition || 'Sin condicion inicial registrada.'}</p>
                      </article>
                      <article>
                        <span>Notas</span>
                        <p>{selectedEquipmentDetail.notes || 'Sin notas particulares.'}</p>
                      </article>
                    </div>
                  </section>
                  <div className="quotation-detail-save">
                    <span>Las acciones del equipo se concentran aqui para mantener limpio el listado operativo.</span>
                    <div className="toolbar-actions">
                      {canUseTechnicalActions ? (
                        <button className="table-button" onClick={() => editEquipmentFromDetail(selectedEquipmentDetail)} type="button">
                          Editar
                        </button>
                      ) : null}
                      {canUseTechnicalActions ? equipmentActions.map((action) => (
                        <button
                          className="table-button"
                          disabled={!isEquipmentActionAllowed(selectedEquipmentDetail, action)}
                          key={action.key}
                          onClick={() => handleEquipmentStatus(selectedEquipmentDetail, action)}
                          type="button"
                        >
                          {action.label}
                        </button>
                      )) : null}
                      <button className="table-button table-button--primary" onClick={() => openFieldSheetForEquipment(selectedEquipmentDetail)} type="button">
                        {sheet ? 'Abrir hoja' : 'Crear hoja'}
                      </button>
                      {canUseTechnicalActions ? (
                        <button className="table-button table-button--danger" onClick={() => handleDeleteEquipment(selectedEquipmentDetail)} type="button">
                          Eliminar
                        </button>
                      ) : null}
                    </div>
                  </div>
                </>
              );
            })()}
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
              {editingEquipmentId ? (
                <label>
                  Tipo de certificado
                  <input
                    disabled
                    type="text"
                    value={calibrationScopeLabels[equipmentForm.certificateScope] || '-'}
                  />
                </label>
              ) : selectedOrderCertificateCapacity.availableScopes.length > 1 ? (
                <label>
                  Tipo de certificado
                  <select
                    onChange={(event) => updateEquipmentForm('certificateScope', event.target.value)}
                    required
                    value={equipmentForm.certificateScope}
                  >
                    <option value="">Selecciona un tipo</option>
                    {selectedOrderCertificateCapacity.availableScopes.map((scope) => (
                      <option key={scope} value={scope}>
                        {calibrationScopeLabels[scope]}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <label>
                  Tipo de certificado
                  <input
                    disabled
                    type="text"
                    value={
                      calibrationScopeLabels[
                        selectedOrderCertificateCapacity.singleAvailableScope || equipmentForm.certificateScope
                      ] || 'Sin cupo disponible'
                    }
                  />
                </label>
              )}
              <div className="ets-certificate-capacity-list">
                {['traceable', 'accredited_iso_17025', 'accredited_linked_lab'].map((scope) => (
                  <article key={scope}>
                    <span>{calibrationScopeBadgeLabels[scope]}</span>
                    <strong>
                      {safeNumber(selectedOrderCertificateCapacity[scope]?.used)} / {safeNumber(selectedOrderCertificateCapacity[scope]?.quoted)}
                    </strong>
                  </article>
                ))}
              </div>
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
                <div className="ets-condition-presets">
                  <button className="table-button" onClick={() => setEquipmentConditionPreset('good')} type="button">
                    Buen estado general
                  </button>
                  <button className="table-button" onClick={() => setEquipmentConditionPreset('bad')} type="button">
                    Mal estado
                  </button>
                </div>
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
              {isFieldSheetCreateModalOpen && selectedOrder && pendingFieldSheetEquipment ? (
          <div className="modal-backdrop" role="presentation">
            <section className="client-modal quotation-detail-modal" aria-modal="true" role="dialog">
              <div className="quotation-detail-header">
                <div>
                  <p>Nueva hoja de campo</p>
                  <h2>{pendingFieldSheetEquipment.name}</h2>
                  <span>{selectedOrder.folio}</span>
                </div>

                <button
                  className="icon-text-button"
                  onClick={() => {
                    setIsFieldSheetCreateModalOpen(false);
                    setIsFieldSheetModalOpen(true);
                  }}
                  type="button"
                >
                  Cerrar
                </button>
              </div>

              <div className="client-form">
                <h3>Cliente del certificado</h3>

                <label>
                  <input
                    checked={fieldSheetCreateForm.certificateClientMode === 'billing'}
                    onChange={() => updateFieldSheetCreateForm('certificateClientMode', 'billing')}
                    type="radio"
                  />
                  Usar el mismo cliente facturado
                </label>

                <label>
                  <input
                    checked={fieldSheetCreateForm.certificateClientMode === 'different'}
                    onChange={() => updateFieldSheetCreateForm('certificateClientMode', 'different')}
                    type="radio"
                  />
                  Usar cliente diferente para el certificado
                </label>

                {fieldSheetCreateForm.certificateClientMode === 'different' ? (
                  <div className="client-form__grid">
                    <label>
                      Empresa
                      <input
                        onChange={(event) =>
                          updateFieldSheetCreateForm('certificateClientCompany', event.target.value)
                        }
                        type="text"
                        value={fieldSheetCreateForm.certificateClientCompany}
                      />
                    </label>

                    <label>
                      Atención
                      <input
                        onChange={(event) =>
                          updateFieldSheetCreateForm('certificateClientAttention', event.target.value)
                        }
                        type="text"
                        value={fieldSheetCreateForm.certificateClientAttention}
                      />
                    </label>

                    <label className="form-field--wide">
                      Dirección
                      <input
                        onChange={(event) =>
                          updateFieldSheetCreateForm('certificateClientAddress', event.target.value)
                        }
                        type="text"
                        value={fieldSheetCreateForm.certificateClientAddress}
                      />
                    </label>

                    <label className="form-field--wide">
                      <input
                        checked={fieldSheetCreateForm.applyCertificateClientToOrder}
                        onChange={(event) =>
                          updateFieldSheetCreateForm('applyCertificateClientToOrder', event.target.checked)
                        }
                        type="checkbox"
                      />
                      Usar este cliente para las demás hojas de esta orden
                    </label>
                  </div>
                ) : null}

                <h3>Plantilla</h3>

                <label>
                  Tipo de hoja de campo
                  <select
                    onChange={(event) => updateFieldSheetCreateForm('templateKey', event.target.value)}
                    value={fieldSheetCreateForm.templateKey}
                  >
                    {(fieldSheetTemplates.length ? fieldSheetTemplates : fieldSheetTemplateOptions).map((template) => (
                      <option key={template.value || template.template_key || template.key} value={template.value || template.template_key || template.key}>
                        {template.label || template.name}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="client-form__actions client-form__actions--modal">
                  <button
                    className="icon-text-button"
                    disabled={isSaving}
                    onClick={() => {
                      setIsFieldSheetCreateModalOpen(false);
                      setIsFieldSheetModalOpen(true);
                    }}
                    type="button"
                  >
                    Cancelar
                  </button>

                  <button
                    className="primary-button"
                    disabled={isSaving}
                    onClick={confirmCreateFieldSheet}
                    type="button"
                  >
                    {isSaving ? 'Creando...' : 'Crear hoja'}
                  </button>
                </div>
              </div>
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
                    <strong>{getFieldSheetTemplateLabel(selectedFieldSheet.template_key, fieldSheetTemplatesByKey)}</strong>
                  </article>
                  <article>
                    <span>Folio reservado</span>
                    <strong>{selectedFieldSheet.reserved_certificate_folio || '-'}</strong>
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
                <FieldSheetLayout
                  template={
                    selectedFieldSheet?.template_definition
                    || selectedFieldSheet?.template_definition_json
                    || getFieldSheetTemplate(fieldSheetForm.templateKey || 'general', fieldSheetTemplatesByKey)
                  }
                  values={{
                    work_order_number: selectedOrder?.work_order_number || '',
                    certificate_number:
                      selectedFieldSheet?.reserved_certificate_folio ||
                      fieldSheetForm.reservedCertificateFolio ||
                      activeCertificatesByEquipmentId.get(selectedEquipmentForSheet?.id)?.expected_folio ||
                      activeCertificatesByEquipmentId.get(selectedEquipmentForSheet?.id)?.folio ||
                      '',

                    attention:
                      fieldSheetForm.certificateClientMode === 'different'
                        ? fieldSheetForm.certificateClientAttention
                        : fieldSheetForm.attention || '',

                    company:
                      fieldSheetForm.certificateClientMode === 'different'
                        ? fieldSheetForm.certificateClientCompany
                        : fieldSheetForm.company ||
                          clientsById.get(selectedOrder?.client_id)?.commercial_name ||
                          clientsById.get(selectedOrder?.client_id)?.legal_name ||
                          '',

                    address:
                      fieldSheetForm.certificateClientMode === 'different'
                        ? fieldSheetForm.certificateClientAddress
                        : fieldSheetForm.address || '',
                    instrument: selectedEquipmentForSheet?.name || '',
                    scope: selectedEquipmentForSheet?.range_or_capacity || '',
                    minimum_division: fieldSheetForm.minimumDivision || '',
                    brand: selectedEquipmentForSheet?.brand || '',
                    serial_number: selectedEquipmentForSheet?.serial_number || '',
                    model: selectedEquipmentForSheet?.model || '',
                    internal_id: selectedEquipmentForSheet?.internal_id || '',
                    location: fieldSheetForm.location || '',
                    calibration_place: fieldSheetForm.calibrationPlace || '',
                    reception_date: fieldSheetForm.receptionDate || '',
                    calibration_date: fieldSheetForm.calibrationDate || '',
                    next_calibration_date: fieldSheetForm.nextCalibrationDate || '',
                    humidity_start: fieldSheetForm.environmentHumidityStart || '',
                    humidity_end: fieldSheetForm.environmentHumidityEnd || '',
                    temperature_start: fieldSheetForm.environmentTemperatureStart || '',
                    temperature_end: fieldSheetForm.environmentTemperatureEnd || '',
                    equipment_good_condition: fieldSheetForm.equipmentGeneralCondition || false,
                    consider_deviations: fieldSheetForm.considerEquipmentDeviations || false,
                    units: fieldSheetForm.units || '',
                    observations: fieldSheetForm.observations || '',
                    others: fieldSheetForm.evidenceNotes || '',
                    calibrated_by: fieldSheetForm.calibratedBy || '',
                    reviewed_by: fieldSheetForm.reviewedBy || '',
                    report_made_by: fieldSheetForm.reportMadeBy || '',
                    purchase_order_or_quotation: fieldSheetForm.purchaseOrderOrQuotation || '',
                  }}
                  resultSections={buildFieldSheetResultSections(
                    fieldSheetForm.resultsRows || [],
                    fieldSheetForm.templateKey || 'general',
                    selectedFieldSheet?.template_definition || selectedFieldSheet?.template_definition_json
                      ? {
                          [fieldSheetForm.templateKey || 'general']:
                            selectedFieldSheet?.template_definition || selectedFieldSheet?.template_definition_json,
                        }
                      : fieldSheetTemplatesByKey,
                  )}
                  onValueChange={(key, value) => {
                    const map = {
                      attention: 'attention',
                      company: 'company',
                      address: 'address',
                      minimum_division: 'minimumDivision',
                      location: 'location',
                      calibration_place: 'calibrationPlace',
                      reception_date: 'receptionDate',
                      calibration_date: 'calibrationDate',
                      next_calibration_date: 'nextCalibrationDate',
                      humidity_start: 'environmentHumidityStart',
                      humidity_end: 'environmentHumidityEnd',
                      temperature_start: 'environmentTemperatureStart',
                      temperature_end: 'environmentTemperatureEnd',
                      equipment_good_condition: 'equipmentGeneralCondition',
                      consider_deviations: 'considerEquipmentDeviations',
                      units: 'units',
                      observations: 'observations',
                      others: 'evidenceNotes',
                      calibrated_by: 'calibratedBy',
                      reviewed_by: 'reviewedBy',
                      report_made_by: 'reportMadeBy',
                      purchase_order_or_quotation: 'purchaseOrderOrQuotation',
                    };

                    if (map[key]) {
                      updateFieldSheetForm(map[key], value);
                    }
                  }}
                  onResultChange={(sectionKey, rowNumber, columnKey, value) => {
                    updateFieldSheetResult(sectionKey, rowNumber, columnKey, value);
                  }}
                />
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
                    <p>Zona de eliminacion operativa</p>
                    <span>La hoja de campo se elimina de la operación visible. No se eliminará físicamente y puede impactar certificados relacionados.</span>
                  </div>
                  <div className="toolbar-actions">
                    <button className="table-button table-button--danger" disabled={isSaving} onClick={handleDeleteFieldSheet} type="button">
                      Eliminar hoja de campo
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
