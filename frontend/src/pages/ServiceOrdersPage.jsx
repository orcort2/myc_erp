import { ChevronDown, ChevronRight, ClipboardList, Save, X } from 'lucide-react';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import mycLogo from '../assets/myc-logo.png';

import ConfirmDialog from '../components/ConfirmDialog.jsx';
import CaptureProcessingSummary from '../components/CaptureProcessingSummary.jsx';
import WorkOrderFlowGroups from '../components/WorkOrderFlowGroups.jsx';
import ActivityPanel from '../components/activity/ActivityPanel.jsx';
import SaleEtsTab from '../components/ets-sales/SaleEtsTab.jsx';
import MaintenanceEtsTab from '../components/ets-maintenance/MaintenanceEtsTab.jsx';
import {
  emptyServiceOrderForm,
  emptyEquipmentForm,
  emptyFieldSheetForm
} from '../constants/forms.js';
import { calibrationScopeOptions } from '../constants/catalog.js';
import {
  serviceOrderStatusLabels,
  equipmentStatusLabels,
  equipmentTransitions,
  equipmentActions,
  fieldSheetStatusLabels,
  certificateReadyFieldSheetStatuses,
  certificateReadyEquipmentStatuses,
  certificateStatusLabels,
  getCertificateStatusLabel
} from '../constants/statuses.js';
import {
  changeEquipmentStatus,
  changeCertificateStatus,
  completeFieldSheet,
  createServiceOrderException,
  createCertificate,
  createClientCertificateProfile,
  downloadFieldSheetPdf,
  downloadAuthenticatedCertificatePdf,
  downloadWorkOrderPdf,
  downloadCapturePackage,
  downloadCaptureMaster,
  getCapturePackageSummary,
  uploadCaptureFiles,
  createEquipment,
  createFieldSheet,
  deleteEquipment,
  deleteFieldSheet,
  deleteServiceOrder,
  deleteServiceWorkOrder,
  getFieldSheet,
  getCertificateReleaseReadiness,
  getServiceOrderWorkOrdersPdfUrl,
  getServiceWorkOrderPdfUrl,
  listCalibrationProcedures,
  listCaptureFiles,
  listCaptureMasterReadiness,
  listCertificates,
  listClients,
  listEquipment,
  listFieldSheetTemplates,
  listFieldSheets,
  listQuotations,
  listReferenceStandards,
  listServiceOrders,
  listUsers,
  reviewFieldSheet,
  suggestFieldSheetPatterns,
  updateEquipment,
  updateFieldSheet,
  updateServiceOrder,
  confirmServiceOrderSignatures,
  releaseAuthenticatedCertificates,
  validateFieldSheetPatterns
} from '../services/api.js';
import useConfirmDialog from '../utils/useConfirmDialog.js';
import { getCaptureMasterReadiness } from '../utils/captureMasters.js';
import { navigate } from '../utils/routing.js';
import {
  getFieldSheetTemplate,
  getFieldSheetTemplateLabel,
  normalizeTemplate,
  fieldSheetToForm,
  buildFieldSheetPayload,
  buildFieldSheetResultSections,
  getFieldSheetCompletionValidation,
  updateFieldSheetResultCell,
  updateFieldSheetResultsRowsForTemplate
} from '../utils/fieldSheets.js';
import {
  getCaptureStageStatus,
  getCertificateReleasePresentation,
  getCertificateStageStatus,
  getEquipmentStageStatus,
  getFieldSheetStageStatus,
  getQualityStageStatus,
} from '../utils/etsStages.js';
import {
  officialFieldSheetTemplateOptions,
  officialFieldSheetTemplates,
} from '../constants/officialFieldSheetTemplates.js';
import { suggestOfficialFieldSheetTemplate } from '../utils/fieldSheetTemplateResolver.js';
import { formatDate, formatDateTime, getClientAddress, getClientDisplayName } from '../utils/formatters.js';
import { exceptionActionLabel } from '../utils/exceptionAuthority.js';
import { canDeleteWorkOrder } from '../utils/workOrderDeletion.js';
import FieldSheetLayout from '../components/field-sheets/FieldSheetLayout.jsx';
import ServiceOrderSignatureMorph from '../components/signatures/ServiceOrderSignatureMorph.jsx';
import EtsBillingTab from '../components/ets-billing/EtsBillingTab.jsx';
import '../components/service-order-exceptions.css';

function safeNumber(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function getServiceOrderCapabilities(order) {
  const items = Array.isArray(order?.items) ? order.items : [];

  const hasSale = items.some(
    (item) => item.operational_category === 'sale'
  );

  const hasMaintenance = items.some(
    (item) => item.operational_category === 'maintenance'
  );

  const hasDirectCalibration = items.some(
    (item) => item.operational_category === 'calibration'
  );

  const hasEmbeddedCalibration = items.some((item) => {
    if (item.operational_category !== 'sale') {
      return false;
    }

    const saleConfiguration =
      item.service_snapshot?.sale_configuration_snapshot;

    return Boolean(
      saleConfiguration?.included_calibration_catalog_item_id ||
      saleConfiguration?.included_calibration_snapshot
    );
  });

  return {
    hasSale,
    hasMaintenance,
    hasDirectCalibration,
    hasEmbeddedCalibration,
  };
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

function canUseAdministrativeActions(user) {
  const roles = getRoleNames(user);
  return isPrivilegedUser(user) || roles.some((role) => ['calidad', 'quality', 'supervisor'].includes(role));
}

function canReleaseCertificates(user) {
  const roles = getRoleNames(user);
  return isPrivilegedUser(user) || roles.some((role) => ['finanzas', 'finance'].includes(role));
}

function stageFromPaymentReadiness(readiness, isPaid) {
  if (isPaid) return { status: 'done', label: 'LISTA', reason: readiness?.reason || 'Pago confirmado.', ready: true };
  if (!readiness) return { status: 'pending', label: 'PENDIENTE', reason: 'Validando estado de pago.', ready: false };
  return { status: 'active', label: 'PENDIENTE', reason: readiness.reason, ready: false };
}


const calibrationScopeLabels = Object.fromEntries(
  calibrationScopeOptions.map(({ value, label }) => [value, label]),
);

const calibrationScopeBadgeLabels = {
  traceable: 'Trazables',
  accredited_iso_17025: 'Acreditados',
  accredited_linked_lab: 'Vinculados',
};

function isMacCaptureAuxiliary(filename = '') {
  return filename.split('/').some((part) => part === '__MACOSX') || filename.split('/').pop() === '.DS_Store' || filename.split('/').pop()?.startsWith('._');
}

function ServiceOrdersPage({ user = null }) {
  const [serviceOrders, setServiceOrders] = useState([]);
  const [clients, setClients] = useState([]);
  const [quotations, setQuotations] = useState([]);
  const [users, setUsers] = useState([]);
  const [equipment, setEquipment] = useState([]);
  const [fieldSheets, setFieldSheets] = useState([]);
  const [certificates, setCertificates] = useState([]);
  const [captureFiles, setCaptureFiles] = useState([]);
  const [captureMasterReadiness, setCaptureMasterReadiness] = useState([]);
  const [captureProcessingResult, setCaptureProcessingResult] = useState(null);
  const [certificateReleaseReadiness, setCertificateReleaseReadiness] = useState(null);
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
  const [exceptionRequest, setExceptionRequest] = useState(null);
  const [exceptionReason, setExceptionReason] = useState('');
  const [editingEquipmentId, setEditingEquipmentId] = useState(null);
  const [activeTab, setActiveTab] = useState('info');
  const [isBillingTabMounted, setIsBillingTabMounted] = useState(false);
  const [fieldSheetTab, setFieldSheetTab] = useState('info');
  const [orderFilter, setOrderFilter] = useState('all');
  const [etsSearch, setEtsSearch] = useState('');
  const [selectedWorkOrderContext, setSelectedWorkOrderContext] = useState(null);
  const [technicalSubEtsEquipment, setTechnicalSubEtsEquipment] = useState(null);
  const [isWorkOrdersModalOpen, setIsWorkOrdersModalOpen] = useState(false);
  const [workOrderSearch, setWorkOrderSearch] = useState('');
  const [exitingEquipmentIds, setExitingEquipmentIds] = useState([]);
  const [isAdminActionsOpen, setIsAdminActionsOpen] = useState(false);
  const [signatureForm, setSignatureForm] = useState({
    technicianName: '',
    technicianSignature: '',
    clientReceivedName: '',
    clientReceivedSignature: '',
    clientAcceptanceName: '',
    clientAcceptanceSignature: '',
  });
  const [signatureLauncherActiveOrderId, setSignatureLauncherActiveOrderId] = useState(null);
  const [isTechnicianPickerOpen, setIsTechnicianPickerOpen] = useState(false);
  const [technicianSearch, setTechnicianSearch] = useState('');
  const [technicianPage, setTechnicianPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [isEquipmentModalOpen, setIsEquipmentModalOpen] = useState(false);
  const [isEquipmentLimitNoticeOpen, setIsEquipmentLimitNoticeOpen] = useState(false);
  const [isFieldSheetModalOpen, setIsFieldSheetModalOpen] = useState(false);
  const [isFieldSheetCreateModalOpen, setIsFieldSheetCreateModalOpen] = useState(false);
  const [isCertificateClientModalOpen, setIsCertificateClientModalOpen] = useState(false);
  const [fieldSheetWorkspaceView, setFieldSheetWorkspaceView] = useState('capture');
  const [fieldSheetValidationErrors, setFieldSheetValidationErrors] = useState({});
  const [expandedFieldSheetWorkOrders, setExpandedFieldSheetWorkOrders] = useState(() => new Set());
  const [pendingFieldSheetEquipment, setPendingFieldSheetEquipment] = useState(null);
  const [fieldSheetCreateForm, setFieldSheetCreateForm] = useState({
    templateKey: '',
    templateSuggestion: '',
    attention: '',
    certificateClientMode: 'billing',
    certificateClientCompany: '',
    certificateClientAddress: '',
    applyCertificateClientToOrder: true,
  });
  const [certificateClientDraft, setCertificateClientDraft] = useState({
    profileId: '',
    label: '',
    company: '',
    address: '',
    attention: '',
    saveToClient: true,
    isDefault: false,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [autosaveStatus, setAutosaveStatus] = useState('idle');
  const [autosaveError, setAutosaveError] = useState('');
  const [lastAutosaveAt, setLastAutosaveAt] = useState(null);

  const autosaveRequestIdRef = useRef(0);
  const autosaveTimerRef = useRef(null);

  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const {
    confirmDialog,
    openConfirm,
    closeConfirm,
    handleConfirm,
  } = useConfirmDialog();

  const canUseTechnicalActions = hasStageAccess(user, 'technical');
  const canUseCaptureActions = hasStageAccess(user, 'capture');
  const canUseQualityActions = hasStageAccess(user, 'quality');
  const canUseReleaseActions = canReleaseCertificates(user);
  const canUseAdminActions = canUseAdministrativeActions(user);
  const canPermanentlyDeleteWorkOrder = canDeleteWorkOrder(user);

  const clientsById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients]
  );

  const usersById = useMemo(
    () => new Map(users.map((systemUser) => [systemUser.id, systemUser])),
    [users]
  );
  const selectedOrderCapabilities = useMemo(
    () => getServiceOrderCapabilities(selectedOrder),
    [selectedOrder]
  );

  const {
    hasSale: selectedOrderHasSale,
    hasMaintenance: selectedOrderHasMaintenance,
    hasDirectCalibration: selectedOrderHasDirectCalibration,
    hasEmbeddedCalibration: selectedOrderHasEmbeddedCalibration,
  } = selectedOrderCapabilities;

  const selectedOrderTabs = useMemo(() => {
    if (!selectedOrder) {
      return [];
    }

    return [
      ['info', 'Resumen'],

      ...(selectedOrderHasMaintenance
        ? [['maintenance', 'Mantenimiento']]
        : []),

      ...(selectedOrderHasSale
        ? [['sale', 'Venta']]
        : []),

      ...(
        selectedOrderHasSale ||
        selectedOrderHasMaintenance ||
        selectedOrderHasDirectCalibration
          ? [['equipment', 'Equipos']]
          : []
      ),

      ...(selectedOrderHasDirectCalibration
        ? [
            ['field-sheet', 'Hojas de Campo'],
            ['capture', 'Captura'],
            ['quality', 'Calidad'],
            ['certificates', 'Certificados'],
          ]
        : []),

      ['billing', 'Facturacion'],
      ['documents', 'Documentos'],
      ['notes', 'Actividad'],
      ['history', 'Historial'],
    ];
  }, [
    selectedOrder,
    selectedOrderHasSale,
    selectedOrderHasMaintenance,
    selectedOrderHasDirectCalibration,
  ]);

  const technicalSubEtsTabs = useMemo(
    () => [
      ['equipment', 'Orden de trabajo'],
      ['field-sheet', 'Hojas de Campo'],
      ['capture', 'Captura'],
      ['quality', 'Calidad'],
      ['certificates', 'Certificados'],
    ],
    []
  );

  const visibleEtsTabs = technicalSubEtsEquipment
    ? technicalSubEtsTabs
    : selectedOrderTabs;



  const equipmentById = useMemo(
    () => new Map(equipment.map((item) => [item.id, item])),
    [equipment]
  );

  const selectedOrderItemsById = useMemo(
    () =>
      new Map(
        (selectedOrder?.items || []).map((item) => [
          Number(item.id),
          item,
        ])
      ),
    [selectedOrder]
  );

  function getEquipmentOperationalContext(item) {
    const sourceItem = item?.service_order_item_id
      ? selectedOrderItemsById.get(Number(item.service_order_item_id))
      : null;

    const operationalCategory =
      sourceItem?.operational_category || null;

    const saleConfiguration =
      sourceItem?.service_snapshot?.sale_configuration_snapshot || null;

    const saleIncludesCalibration = Boolean(
      saleConfiguration?.included_calibration_catalog_item_id ||
      saleConfiguration?.included_calibration_snapshot
    );

    if (operationalCategory === 'sale') {
      if (saleIncludesCalibration || item?.calibration_scope) {
        return {
          key: 'sale-calibration',
          label: 'Venta + calibración',
          hasMetrology: true,
          sourceItem,
        };
      }

      return {
        key: 'sale',
        label: 'Venta',
        hasMetrology: false,
        sourceItem,
      };
    }

    if (operationalCategory === 'maintenance') {
      return {
        key: 'maintenance',
        label: 'Mantenimiento',
        hasMetrology: Boolean(item?.calibration_scope),
        sourceItem,
      };
    }

    if (operationalCategory === 'calibration') {
      return {
        key: 'calibration',
        label: 'Calibración',
        hasMetrology: true,
        sourceItem,
      };
    }

    if (item?.calibration_scope) {
      return {
        key: 'calibration',
        label: 'Calibración',
        hasMetrology: true,
        sourceItem,
      };
    }

    return {
      key: 'equipment',
      label: 'Equipo',
      hasMetrology: false,
      sourceItem,
    };
  }

  function getEquipmentNextStep({
    item,
    operationalContext,
    sheet,
    certificate,
  }) {
    if (!operationalContext.hasMetrology) {
      return {
        label: 'Proceso operativo',
        value:
          equipmentStatusLabels[item.status] ??
          item.status ??
          'Pendiente',
      };
    }

    if (!sheet) {
      return {
        label: 'Siguiente paso',
        value: 'Preparar hoja de campo',
      };
    }

    if (
      ['draft', 'in_progress', 'returned_to_technician', 'rejected']
        .includes(sheet.status)
    ) {
      return {
        label: 'Siguiente paso',
        value: 'Completar hoja de campo',
      };
    }

    if (
      ['completed', 'under_review']
        .includes(sheet.status)
    ) {
      return {
        label: 'Siguiente paso',
        value: 'Revisión de hoja',
      };
    }

    if (!certificate) {
      return {
        label: 'Siguiente paso',
        value: 'Preparar certificado',
      };
    }

    if (certificate.authenticated_pdf_path) {
      return {
        label: 'Estado técnico',
        value: 'Certificado autenticado',
      };
    }

    if (certificate.final_pdf_path) {
      return {
        label: 'Siguiente paso',
        value: 'Revisión / autenticación',
      };
    }

    return {
      label: 'Estado técnico',
      value:
        certificateStatusLabels[certificate.status] ??
        certificate.status ??
        'En proceso',
    };
  }

  const technicianOptions = useMemo(
    () => users.filter((systemUser) => systemUser.is_active !== false && canManageServices(systemUser)),
    [users]
  );

  const quotationsById = useMemo(
    () => new Map(quotations.map((quotation) => [quotation.id, quotation])),
    [quotations]
  );

  const fieldSheetTemplatesByKey = useMemo(
    () => ({
      ...Object.fromEntries((fieldSheetTemplates || []).map((template) => [template.template_key || template.key, template])),
      ...officialFieldSheetTemplates,
    }),
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

    if (Array.isArray(selectedOrder.work_orders)) {
      return [...selectedOrder.work_orders]
      .filter((workOrder) => workOrder.is_active !== false)
      .sort((left, right) => Number(left.sequence || 0) - Number(right.sequence || 0));
    }
    
    return [
      {
        id: `legacy-${selectedOrder.id}`,
        service_order_id: selectedOrder.id,
        work_order_number: selectedOrder.work_order_number,
        sequence: 1,
        equipment_limit: 10,
        status: selectedOrder.status,
      },
    ];
  },[selectedOrder]);    

  const normalizedEtsSearch = etsSearch.trim().toLowerCase();

  function isLegacyWorkOrder(workOrder) {
    return String(workOrder?.id || '').startsWith('legacy-');
  }

  function workOrderContextFromWorkOrder(workOrder) {
    if (!workOrder) return null;
    return {
      id: isLegacyWorkOrder(workOrder) ? null : workOrder.id,
      number: workOrder.work_order_number ?? null,
      label: `OT-${workOrder.work_order_number ?? '-'}`,
    };
  }

  function getEquipmentWorkOrder(item) {
    if (!item) return null;

    return relatedWorkOrders.find((workOrder) => {
      if (
        item.work_order_id &&
        !isLegacyWorkOrder(workOrder) &&
        Number(workOrder.id) === Number(item.work_order_id)
      ) {
        return true;
      }

      return (
        String(workOrder.work_order_number || '') ===
        String(item.work_order_number || '')
      );
    }) || null;
  }

  function openTechnicalSubEts(item) {
    if (!item) return;

    const operationalContext =
      getEquipmentOperationalContext(item);

    if (!operationalContext.hasMetrology) {
      openEquipmentDetail(item);
      return;
    }

    const workOrder = getEquipmentWorkOrder(item);

    setTechnicalSubEtsEquipment(item);

    setSelectedWorkOrderContext(
      workOrder
        ? workOrderContextFromWorkOrder(workOrder)
        : {
            id: item.work_order_id || null,
            number: item.work_order_number || null,
            label: `OT-${item.work_order_number || '-'}`,
          }
    );

    setFieldSheetWorkspaceView('capture');
    setActiveTab('equipment');
  }

function closeTechnicalSubEts() {
  setTechnicalSubEtsEquipment(null);
  setSelectedWorkOrderContext(null);
  setFieldSheetWorkspaceView('capture');
  setActiveTab('equipment');
}

  function itemMatchesWorkOrderContext(item, context = selectedWorkOrderContext) {
    if (!context) return true;
    if (context.id && Number(item.work_order_id) === Number(context.id)) return true;
    return String(item.work_order_number || '') === String(context.number || '');
  }

  function sheetMatchesWorkOrderContext(sheet, context = selectedWorkOrderContext) {
    if (!context) return true;
    if (context.id && Number(sheet?.work_order_id) === Number(context.id)) return true;
    return String(sheet?.work_order_number || '') === String(context.number || '');
  }

  function getWorkOrderEquipment(workOrder, source = selectedEquipment) {
    return source.filter((item) => {
      if (!isLegacyWorkOrder(workOrder) && workOrder.id) {
        return Number(item.work_order_id) === Number(workOrder.id);
      }
      return String(item.work_order_number || '') === String(workOrder.work_order_number || selectedOrder?.work_order_number || '');
    });
  }

  function getWorkOrderEquipmentCount(workOrder) {
    return getWorkOrderEquipment(workOrder).length;
  }

  function getWorkOrderFieldSheets(workOrder) {
    return selectedFieldSheets.filter((sheet) => sheetMatchesWorkOrderContext(sheet, workOrderContextFromWorkOrder(workOrder)));
  }

  function getFieldSheetWorkOrderMetrics(workOrder) {
    const items = getWorkOrderEquipment(workOrder);
    const rows = items.map((item) => ({ item, sheet: fieldSheetsByEquipmentId.get(item.id) ?? null }));
    const created = rows.filter((row) => row.sheet).length;
    const approved = rows.filter((row) => row.sheet?.status === 'approved').length;
    const capture = rows.filter((row) => ['draft', 'in_progress', 'returned_to_technician', 'rejected'].includes(row.sheet?.status)).length;
    const review = rows.filter((row) => ['completed', 'under_review'].includes(row.sheet?.status)).length;
    const pending = Math.max(items.length - created, 0);
    return {
      rows,
      equipmentCount: items.length,
      created,
      approved,
      capture,
      review,
      pending,
      progress: items.length ? Math.round((created / items.length) * 100) : 0,
    };
  }

  function toggleFieldSheetWorkOrder(workOrderId) {
    setExpandedFieldSheetWorkOrders((current) => {
      const next = new Set(current);
      if (next.has(workOrderId)) next.delete(workOrderId);
      else next.add(workOrderId);
      return next;
    });
  }

  function getWorkOrderCertificates(workOrder) {
    const context = workOrderContextFromWorkOrder(workOrder);
    return selectedCertificates.filter((certificate) => {
      const item = equipment.find((candidate) => candidate.id === certificate.equipment_id);
      const sheet = certificate.field_sheet_id ? fieldSheets.find((candidate) => candidate.id === certificate.field_sheet_id) : null;
      return itemMatchesWorkOrderContext(item, context) || sheetMatchesWorkOrderContext(sheet, context);
    });
  }

  const workOrderCapacitySummary = useMemo(() => {
    const groups = relatedWorkOrders.map((workOrder) => {
      const registered = getWorkOrderEquipment(workOrder).length;
      const limit = safeNumber(workOrder.equipment_limit || 10);
      return {
        ...workOrder,
        registered,
        limit,
        available: Math.max(limit - registered, 0),
      };
    });
    return {
      groups,
      totalRegistered: groups.reduce((sum, workOrder) => sum + workOrder.registered, 0),
      totalLimit: groups.reduce((sum, workOrder) => sum + workOrder.limit, 0),
      totalAvailable: groups.reduce((sum, workOrder) => sum + workOrder.available, 0),
    };
  }, [relatedWorkOrders, selectedEquipment, selectedOrder]);

  const hasAvailableWorkOrderCapacity = workOrderCapacitySummary.totalAvailable > 0;
  const shouldShowSignatureLauncher = Boolean(
    selectedOrder &&
      (selectedOrder.has_pending_signature_work_orders ||
        signatureLauncherActiveOrderId === selectedOrder.id)
  );

  const filteredSelectedEquipment = useMemo(() => {
    return selectedEquipment.filter((item) => {
      if (
        technicalSubEtsEquipment &&
        Number(item.id) !==
          Number(technicalSubEtsEquipment.id)
      ) {
        return false;
      }

      if (!itemMatchesWorkOrderContext(item)) {
        return false;
      }

      if (!normalizedEtsSearch) {
        return true;
      }

      const sheet =
        fieldSheetsByEquipmentId.get(item.id);

      const certificate =
        activeCertificatesByEquipmentId.get(item.id);

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
        certificate?.authentication_code,
      ].some((value) =>
        String(value || '')
          .toLowerCase()
          .includes(normalizedEtsSearch)
      );
    });
  }, [
    activeCertificatesByEquipmentId,
    fieldSheetsByEquipmentId,
    normalizedEtsSearch,
    selectedEquipment,
    selectedOrder,
    selectedWorkOrderContext,
    technicalSubEtsEquipment,
  ]);
  const filteredSelectedCertificates = useMemo(() => {
    return selectedCertificates.filter((certificate) => {
      const item = equipment.find((candidate) => candidate.id === certificate.equipment_id);
      const sheet = certificate.field_sheet_id ? fieldSheets.find((candidate) => candidate.id === certificate.field_sheet_id) : null;

      // Tu nueva validación agregada
      if (
        technicalSubEtsEquipment &&
        Number(item?.id) !== Number(technicalSubEtsEquipment.id)
      ) {
        return false;
      }

      if (!itemMatchesWorkOrderContext(item) && !sheetMatchesWorkOrderContext(sheet)) return false;

      if (!normalizedEtsSearch) return true;

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
  }, [equipment, fieldSheets, normalizedEtsSearch, selectedCertificates, selectedWorkOrderContext, technicalSubEtsEquipment, technicalSubEtsEquipment]); 


  const latestCaptureFileByCertificateId = useMemo(() => {
    const selectedIds = new Set(filteredSelectedCertificates.map((certificate) => certificate.id));
    const latest = new Map();
    captureFiles.forEach((file) => {
      if (file.certificate_id && selectedIds.has(file.certificate_id) && !latest.has(file.certificate_id) && !isMacCaptureAuxiliary(file.filename)) {
        latest.set(file.certificate_id, file);
      }
    });
    return latest;
  }, [captureFiles, filteredSelectedCertificates]);

  const authoritativeCaptureReadinessByCertificateId = useMemo(() => new Map(
    captureMasterReadiness.map((row) => [row.certificate_id, {
      masterExpected: Boolean(row.master_expected),
      identified: Boolean(row.identified),
      ready: Boolean(row.ready),
      reason: row.reason || '',
      warnings: Array.isArray(row.warnings) ? row.warnings : [],
      mismatches: Array.isArray(row.mismatches) ? row.mismatches : [],
      master: row.master || null,
    }])
  ), [captureMasterReadiness]);

  const captureMasterMetrics = useMemo(() => {
    const readinessRows = filteredSelectedCertificates.map((certificate) => (
      authoritativeCaptureReadinessByCertificateId.get(certificate.id) || getCaptureMasterReadiness({
        certificate,
        equipment: equipment.find((item) => item.id === certificate.equipment_id),
        captureFile: latestCaptureFileByCertificateId.get(certificate.id),
      })
    ));
    return {
      expected: readinessRows.filter((row) => row.masterExpected).length,
      identified: readinessRows.filter((row) => row.identified).length,
      warnings: readinessRows.reduce((sum, row) => sum + row.warnings.length, 0),
      mismatches: readinessRows.reduce((sum, row) => sum + row.mismatches.length, 0),
      unidentified: readinessRows.filter((row) => row.masterExpected && !row.identified).length,
    };
  }, [authoritativeCaptureReadinessByCertificateId, equipment, filteredSelectedCertificates, latestCaptureFileByCertificateId]);

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
    () => {
      if (!selectedOrder) return {
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
      };
      const metrics = getOrderMetrics(selectedOrder);
      return {
        ...metrics,
        billingPending: certificateReleaseReadiness
          ? !certificateReleaseReadiness.release_allowed
          : metrics.billingPending,
      };
    },
    [selectedOrder, equipment, fieldSheets, certificates, certificateReleaseReadiness]
  );

  const qualityMetrics = useMemo(() => ({
    pending: filteredSelectedCertificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated'].includes(certificate.status)).length,
    review: filteredSelectedCertificates.filter((certificate) => ['quality_review', 'match_validated'].includes(certificate.status)).length,
    approved: filteredSelectedCertificates.filter((certificate) => ['quality_approved', 'approved'].includes(certificate.status)).length,
    releasable: filteredSelectedCertificates.filter((certificate) => certificate.status === 'authenticated').length,
    authenticated: filteredSelectedCertificates.filter((certificate) => certificate.authenticated_pdf_path).length
  }), [filteredSelectedCertificates]);

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
    if (!selectedOrder) {
      return {};
    }

    const summaryReady = Boolean(
      selectedOrder.agenda_date &&
      selectedOrder.service_date &&
      selectedOrder.technician_id
    );

    const equipmentStage =
      getEquipmentStageStatus({
        order: selectedOrder,
        equipment: selectedEquipment,
      });

    const fieldSheetStage =
      getFieldSheetStageStatus({
        equipment: filteredSelectedEquipment,
        fieldSheets: selectedFieldSheets,
        equipmentStage,
      });

    const captureStage =
      getCaptureStageStatus({
        certificates: filteredSelectedCertificates,
        fieldSheetStage,
      });

    const qualityStage =
      getQualityStageStatus({
        certificates: filteredSelectedCertificates,
      });

    const certificateStage =
      getCertificateStageStatus({
        certificates: filteredSelectedCertificates,
        releaseReadiness:
          certificateReleaseReadiness,
      });

    const billingComplete =
      certificateReleaseReadiness?.payment_status ===
        'paid' ||
      certificateReleaseReadiness?.payment_status ===
        'not_required';

    const states = {
      info: {
        label: summaryReady
          ? 'Lista'
          : 'En proceso',
        status: summaryReady
          ? 'done'
          : 'active',
        ready: summaryReady,
      },

      sale: selectedOrderHasSale
        ? {
            label: 'Disponible',
            status: 'active',
            ready: true,
          }
        : undefined,

      maintenance: selectedOrderHasMaintenance
        ? {
            label: 'Disponible',
            status: 'active',
            ready: true,
          }
        : undefined,

      equipment: equipmentStage,

      billing: stageFromPaymentReadiness(
        certificateReleaseReadiness,
        billingComplete
      ),

      documents: {
        label: 'Disponible',
        status: 'active',
        ready: true,
      },

      notes: {
        label: selectedOrder.notes
          ? 'Con notas'
          : 'Disponible',
        status: selectedOrder.notes
          ? 'active'
          : 'pending',
        ready: true,
      },

      history: {
        label: 'Disponible',
        status: 'active',
        ready: true,
      },
    };

    if (
      selectedOrderHasDirectCalibration ||
      technicalSubEtsEquipment
    ) {
      states['field-sheet'] = fieldSheetStage;
      states.capture = captureStage;
      states.quality = qualityStage;
      states.certificates = certificateStage;
    }

    return states;
  }, [
    selectedOrder,
    selectedEquipment,
    selectedFieldSheets,
    filteredSelectedEquipment,
    filteredSelectedCertificates,
    certificateReleaseReadiness,
    selectedOrderHasSale,
    selectedOrderHasMaintenance,
    selectedOrderHasDirectCalibration,
    technicalSubEtsEquipment,
  ]);
  function getOrderMetrics(order) {
    const orderEquipment = equipment.filter((item) => item.service_order_id === order.id && item.is_active !== false);
    const orderEquipmentIds = new Set(orderEquipment.map((item) => item.id));
    const orderSheets = fieldSheets.filter((sheet) => orderEquipmentIds.has(sheet.equipment_id) && sheet.is_active !== false);
    const orderCertificates = certificates.filter((certificate) => certificate.service_order_id === order.id && certificate.is_active !== false);
    const equipmentStage = getEquipmentStageStatus({ order, equipment: orderEquipment });
    const fieldSheetStage = getFieldSheetStageStatus({ equipment: orderEquipment, fieldSheets: orderSheets, equipmentStage });
    const captureStage = getCaptureStageStatus({ certificates: orderCertificates, fieldSheetStage });
    const qualityStage = getQualityStageStatus({ certificates: orderCertificates });
    const certificateStage = getCertificateStageStatus({ certificates: orderCertificates });
    const pdfUploaded = orderCertificates.filter((certificate) => Boolean(certificate.final_pdf_path)).length;
    const capturePending = orderCertificates.filter((certificate) => ['expected', 'field_sheet_ready', 'capture_pending', 'capture_in_progress', 'pdf_uploaded', 'quality_rejected', 'correction_requested', 'returned_to_technician'].includes(certificate.status)).length;
    const qualityPending = orderCertificates.filter((certificate) => ['ready_for_quality', 'quality_review', 'match_validated', 'quality_approved'].includes(certificate.status)).length;
    const authenticated = orderCertificates.filter((certificate) => Boolean(certificate.authenticated_pdf_path)).length;
    const released = orderCertificates.filter((certificate) => certificate.status === 'released_to_client').length;
    const expectedEquipment = equipmentStage.metrics.expected;
    const fieldSheetsDone = orderSheets.filter((sheet) => ['completed', 'under_review', 'approved'].includes(sheet.status)).length;
    const stageChecks = [
      Boolean(order.quotation_id),
      Boolean(order.agenda_date && order.service_date && order.technician_id),
      equipmentStage.status === 'done',
      fieldSheetStage.status === 'done',
      captureStage.status === 'done',
      qualityStage.status === 'done',
      certificateStage.status === 'done',
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

  function updateSignatureForm(field, value) {
    setSignatureForm((current) => ({ ...current, [field]: value }));
  }

  function renderSignatureLauncher() {
    return (
      <aside className="ets-signature-launcher" aria-label="Firmas del ETS">
        <div className="ets-signature-launcher__copy">
          <span>Firmas</span>
          <strong>Firmar órdenes de trabajo</strong>
        </div>

        <ServiceOrderSignatureMorph
          serviceOrder={selectedOrder}
          signatureForm={signatureForm}
          updateSignatureForm={updateSignatureForm}
          saveSignatures={saveSignatures}
          isSaving={isSaving}
          onLifecycleChange={(isActive) => {
            setSignatureLauncherActiveOrderId(
              isActive ? selectedOrder.id : null,
            );
          }}
        />
      </aside>
    );
  }

  async function saveSignatures() {
    if (!selectedOrder) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await updateServiceOrder(selectedOrder.id, {
        technician_signed_name: signatureForm.technicianName.trim() || null,
        technician_signature_data_url: signatureForm.technicianSignature || null,
        client_received_signed_name: signatureForm.clientReceivedName.trim() || null,
        client_received_signature_data_url: signatureForm.clientReceivedSignature || null,
        client_acceptance_signed_name: signatureForm.clientAcceptanceName.trim() || null,
        client_acceptance_signature_data_url: signatureForm.clientAcceptanceSignature || null,
      });
      await confirmServiceOrderSignatures(selectedOrder.id);
      setSelectedOrder(updated);
      setNotice('Firmas del ETS guardadas. Se imprimirán en todas las OT del expediente.');
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function requestServiceOrderException(sourceStage, targetStage, reason) {
    if (!selectedOrder) return;
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const request = await createServiceOrderException(selectedOrder.id, {
        source_stage: sourceStage,
        target_stage: targetStage,
        reason,
      });
      setExceptionRequest(null);
      setExceptionReason('');
      setNotice(`Excepción solicitada (${request.status}): ${sourceStage} → ${targetStage}.`);
      await loadServiceOrderData();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function openExceptionRequest(sourceStage, targetStage) {
    setExceptionRequest({ sourceStage, targetStage });
    setExceptionReason('');
    setError('');
  }

  async function submitExceptionRequest() {
    if (!selectedOrder || !exceptionRequest) return;
    const reason = exceptionReason.trim();
    if (!reason) {
      setError('Captura el motivo de la excepcion.');
      return;
    }
    await requestServiceOrderException(
      exceptionRequest.sourceStage,
      exceptionRequest.targetStage,
      reason
    );
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
    window.sessionStorage.setItem('myc:contextReturn', JSON.stringify({
      target: 'service-order',
      serviceOrderId: selectedOrder.id,
      activeTab,
      workOrderContext: selectedWorkOrderContext,
      fieldSheetWorkspaceView,
      scrollY: window.scrollY,
    }));
    navigate('/dashboard#cotizaciones');
  }

  function openTabFromSummary(tab, options = {}) {
    if (options.workOrder) {
      setSelectedWorkOrderContext(workOrderContextFromWorkOrder(options.workOrder));
    } else if (options.workOrderId || options.workOrderNumber) {
      setSelectedWorkOrderContext({
        id: options.workOrderId && !String(options.workOrderId).startsWith('legacy-') ? options.workOrderId : null,
        number: options.workOrderNumber ?? null,
        label: `OT-${options.workOrderNumber ?? '-'}`,
      });
    }
    if (tab === 'field-sheet') {
      setFieldSheetWorkspaceView(options.fieldSheetView || 'capture');
    }
    setActiveTab(tab);
  }

  useEffect(() => {
    if (activeTab === 'billing') {
      setIsBillingTabMounted(true);
    }
  }, [activeTab]);

  function clearWorkOrderContext() {
    setSelectedWorkOrderContext(null);
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

  async function loadCaptureFilesData(serviceOrderId = selectedOrder?.id) {
    if (!serviceOrderId) {
      setCaptureFiles([]);
      setCaptureMasterReadiness([]);
      return [];
    }
    const [result, readinessResult] = await Promise.all([
      listCaptureFiles(serviceOrderId),
      listCaptureMasterReadiness(serviceOrderId),
    ]);
    const nextFiles = Array.isArray(result) ? result : [];
    setCaptureFiles(nextFiles);
    setCaptureMasterReadiness(Array.isArray(readinessResult) ? readinessResult : []);
    return nextFiles;
  }

  useEffect(() => {
    loadServiceOrderData();
  }, []);

  useEffect(() => {
    setCaptureProcessingResult(null);
    if (!selectedOrder?.id) {
      setCaptureFiles([]);
      setCaptureMasterReadiness([]);
      return;
    }
    loadCaptureFilesData(selectedOrder.id).catch((requestError) => setError(requestError.message));
  }, [selectedOrder?.id]);

  useEffect(() => {
    const rawContext = window.sessionStorage.getItem('myc:contextReturn');
    if (!rawContext || isDetailOpen || !serviceOrders.length) return;
    try {
      const context = JSON.parse(rawContext);
      if (context.target !== 'service-order') return;
      const order = serviceOrders.find((item) => item.id === context.serviceOrderId);
      if (!order) return;
      window.sessionStorage.removeItem('myc:contextReturn');
      openOrderDetail(order);
      window.setTimeout(() => {
        setActiveTab(context.activeTab || 'info');
        setSelectedWorkOrderContext(context.workOrderContext || null);
        setFieldSheetWorkspaceView(context.fieldSheetWorkspaceView || 'capture');
        window.scrollTo({ top: Number(context.scrollY) || 0 });
      }, 0);
    } catch {
      window.sessionStorage.removeItem('myc:contextReturn');
    }
  }, [serviceOrders, isDetailOpen]);

  useEffect(() => {
    if (!selectedOrder?.id) {
      setCertificateReleaseReadiness(null);
      return undefined;
    }
    let isMounted = true;
    getCertificateReleaseReadiness(selectedOrder.id)
      .then((readiness) => {
        if (isMounted) setCertificateReleaseReadiness(readiness);
      })
      .catch(() => {
        if (isMounted) setCertificateReleaseReadiness(null);
      });
    return () => {
      isMounted = false;
    };
  }, [selectedOrder?.id, certificates]);

  useEffect(() => {
    setTechnicianPage(1);
  }, [technicianSearch]);

    useEffect(() => {
    if (!isDetailOpen || !selectedOrder) {
      return undefined;
    }

    const nextPayload = buildOrderUpdatePayload(orderForm);
    const persistedPayload = buildSelectedOrderPayload(selectedOrder);

    if (orderPayloadsAreEqual(nextPayload, persistedPayload)) {
      if (autosaveStatus === 'pending') {
        setAutosaveStatus('saved');
      }

      return undefined;
    }

    setAutosaveStatus('pending');

    if (autosaveTimerRef.current) {
      window.clearTimeout(autosaveTimerRef.current);
    }

    autosaveTimerRef.current = window.setTimeout(() => {
      saveOrderForm({
        payload: nextPayload,
        showNotice: false,
      });
    }, 900);

    return () => {
      if (autosaveTimerRef.current) {
        window.clearTimeout(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }
    };
  }, [
    orderForm,
    isDetailOpen,
    selectedOrder?.id,
  ]);



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

  function openOrderDetail(order) {
    setSignatureLauncherActiveOrderId(null);
    setAutosaveStatus('saved');
    setAutosaveError('');
    setLastAutosaveAt(null);
    autosaveRequestIdRef.current += 1;

    if (autosaveTimerRef.current) {
      window.clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }
    setSelectedOrder(order);
    setOrderForm({
      agendaDate: order.agenda_date ?? '',
      serviceDate: order.service_date ?? '',
      technicianId: order.technician_id ? String(order.technician_id) : '',
      requiresPayment: order.requires_payment !== false,
      notes: order.notes ?? ''
    });
    setSignatureForm({
      technicianName: order.technician_signed_name ?? order.technician_name ?? '',
      technicianSignature: order.technician_signature_data_url ?? '',
      clientReceivedName: order.client_received_signed_name ?? '',
      clientReceivedSignature: order.client_received_signature_data_url ?? '',
      clientAcceptanceName: order.client_acceptance_signed_name ?? '',
      clientAcceptanceSignature: order.client_acceptance_signature_data_url ?? '',
    });
    setActiveTab('info');
    setIsBillingTabMounted(false);
    setFieldSheetWorkspaceView('capture');
    setExpandedFieldSheetWorkOrders(new Set());
    setEtsSearch('');
    setSelectedWorkOrderContext(null);
    setIsAdminActionsOpen(false);
    setExitingEquipmentIds([]);
    setIsDetailOpen(true);
    setError('');
    setNotice('');
  }

  function closeOrderDetail() {
    if (autosaveTimerRef.current) {
      window.clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }

    autosaveRequestIdRef.current += 1;
    setAutosaveStatus('idle');
    setAutosaveError('');
    setLastAutosaveAt(null);
    setSignatureLauncherActiveOrderId(null);
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
    setIsBillingTabMounted(false);
    setEtsSearch('');
    setSelectedWorkOrderContext(null);
    setExitingEquipmentIds([]);
    setIsTechnicianPickerOpen(false);
    setFieldSheetTab('technical');
    setSelectedAuthentication(null);
    setSignatureForm({
      technicianName: '',
      technicianSignature: '',
      clientReceivedName: '',
      clientReceivedSignature: '',
      clientAcceptanceName: '',
      clientAcceptanceSignature: '',
    });
    setExceptionRequest(null);
    setExceptionReason('');
    setError('');
  }

    function buildOrderUpdatePayload(form = orderForm) {
    return {
      agenda_date: form.agendaDate || null,
      service_date: form.serviceDate || null,
      technician_id: form.technicianId
        ? Number(form.technicianId)
        : null,
      requires_payment: Boolean(form.requiresPayment),
      notes: form.notes.trim() || null,
    };
  }

  function buildSelectedOrderPayload(order = selectedOrder) {
    if (!order) return null;

    return {
      agenda_date: order.agenda_date || null,
      service_date: order.service_date || null,
      technician_id: order.technician_id
        ? Number(order.technician_id)
        : null,
      requires_payment: order.requires_payment !== false,
      notes: order.notes?.trim() || null,
    };
  }

  function orderPayloadsAreEqual(left, right) {
    if (!left || !right) return false;

    return (
      left.agenda_date === right.agenda_date &&
      left.service_date === right.service_date &&
      left.technician_id === right.technician_id &&
      left.requires_payment === right.requires_payment &&
      left.notes === right.notes
    );
  }

  function updateOrderForm(field, value) {
    setOrderForm((current) => ({
      ...current,
      [field]: value,
    }));

    setAutosaveStatus('pending');
    setAutosaveError('');
  }

  async function saveOrderForm({
    showNotice = false,
    payload = buildOrderUpdatePayload(),
  } = {}) {
    if (!selectedOrder) return null;

    const persistedPayload = buildSelectedOrderPayload(selectedOrder);

    if (orderPayloadsAreEqual(payload, persistedPayload)) {
      setAutosaveStatus('saved');
      return selectedOrder;
    }

    const requestId = autosaveRequestIdRef.current + 1;
    autosaveRequestIdRef.current = requestId;

    setAutosaveStatus('saving');
    setAutosaveError('');

    try {
      const updated = await updateServiceOrder(
        selectedOrder.id,
        payload,
      );

      if (requestId !== autosaveRequestIdRef.current) {
        return updated;
      }

      setSelectedOrder(updated);

      setServiceOrders((current) =>
        current.map((order) =>
          order.id === updated.id ? updated : order,
        ),
      );

      setAutosaveStatus('saved');
      setLastAutosaveAt(new Date());

      if (showNotice) {
        setNotice(`Orden ${updated.folio} actualizada`);
      }

      return updated;
    } catch (requestError) {
      if (requestId === autosaveRequestIdRef.current) {
        setAutosaveStatus('error');
        setAutosaveError(requestError.message);
        setError(requestError.message);
      }

      return null;
    }
  }

  function updateEquipmentForm(field, value) {
    setEquipmentForm((current) => ({ ...current, [field]: value }));
  }

  async function handleOrderSubmit(event) {
    event?.preventDefault?.();

    if (!selectedOrder) return;

    if (autosaveTimerRef.current) {
      window.clearTimeout(autosaveTimerRef.current);
      autosaveTimerRef.current = null;
    }

    setError('');
    setNotice('');
    setIsSaving(true);

    try {
      await saveOrderForm({
        showNotice: true,
      });
    } finally {
      setIsSaving(false);
    }
  }

  function openEquipmentModal(item = null) {
    setError('');
    setNotice('');

    const expectedEquipment = Number(
      selectedOrderMetrics.expectedEquipment ?? 0
    );
    const registeredEquipment = Number(selectedEquipment.length ?? 0);
    const contextualCapacity = selectedWorkOrderContext
      ? workOrderCapacitySummary.groups.find((workOrder) => {
          if (selectedWorkOrderContext.id) {
            return Number(workOrder.id) === Number(selectedWorkOrderContext.id);
          }

          return String(workOrder.work_order_number ?? '') ===
            String(selectedWorkOrderContext.number ?? '');
        })
      : null;
    const capacity = Number(
      contextualCapacity?.limit ?? workOrderCapacitySummary.totalLimit ?? 0
    );
    const registered = Number(
      contextualCapacity?.registered ??
        workOrderCapacitySummary.totalRegistered ??
        0
    );

    if (
      !item &&
      ((expectedEquipment > 0 && registeredEquipment >= expectedEquipment) ||
        (capacity > 0 && registered >= capacity))
    ) {
      setIsEquipmentLimitNoticeOpen(true);
      return;
    }

    if (!item && capacity <= 0) {
      setError('No hay Orden de Trabajo con capacidad disponible.');
      return;
    }

    const preferredWorkOrder = contextualCapacity?.available > 0
      ? contextualCapacity
      : workOrderCapacitySummary.groups.find((workOrder) => workOrder.available > 0) || relatedWorkOrders[0];
    if (item) {
      setEditingEquipmentId(item.id);
      setEquipmentForm({
        workOrderId: item.work_order_id ? String(item.work_order_id) : '',
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
        workOrderId: preferredWorkOrder && !isLegacyWorkOrder(preferredWorkOrder) ? String(preferredWorkOrder.id) : '',
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
        work_order_id: equipmentForm.workOrderId ? Number(equipmentForm.workOrderId) : null,
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
          setExitingEquipmentIds((current) => [...new Set([...current, item.id])]);
          window.setTimeout(() => {
            setEquipment((current) => current.filter((equipmentItem) => equipmentItem.id !== item.id));
            setExitingEquipmentIds((current) => current.filter((equipmentId) => equipmentId !== item.id));
          }, 220);
          setNotice('Equipo eliminado de la operación visible');
          await new Promise((resolve) => window.setTimeout(resolve, 230));
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

  async function openFieldSheetForEquipment(item, workOrder = null) {
    setError('');
    setNotice('');
    setSelectedEquipmentForSheet(item);
    if (workOrder) {
      setSelectedWorkOrderContext(workOrderContextFromWorkOrder(workOrder));
    }

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

      const suggestion = suggestOfficialFieldSheetTemplate({
        instrumentType: item.instrument_type,
        magnitude: item.magnitude,
        serviceType: item.service_type,
        equipmentName: item.name,
      });
      setPendingFieldSheetEquipment(item);
      setFieldSheetCreateForm({
        templateKey: suggestion.templateKey,
        templateSuggestion: suggestion.matchedBy,
        attention: inheritedCertificateClient?.certificate_client_attention ?? '',
        certificateClientMode: inheritedCertificateClient?.certificate_client_mode ?? 'billing',
        certificateClientCompany: inheritedCertificateClient?.certificate_client_company ?? '',
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
    if (!fieldSheetCreateForm.templateKey || !officialFieldSheetTemplates[fieldSheetCreateForm.templateKey]) {
      setError('No se pudo determinar automáticamente la plantilla. Selecciona una hoja de campo.');
      return;
    }

    setIsSaving(true);
    setError('');
    setNotice('');

    try {
      const sheet = await createFieldSheet({
        equipment_id: pendingFieldSheetEquipment.id,
        template_key: fieldSheetCreateForm.templateKey,
        template_version: officialFieldSheetTemplates[fieldSheetCreateForm.templateKey].version,
        template_snapshot: officialFieldSheetTemplates[fieldSheetCreateForm.templateKey],
        attention: fieldSheetCreateForm.attention.trim() || null,
        certificate_client_mode: fieldSheetCreateForm.certificateClientMode,
        certificate_client_company: fieldSheetCreateForm.certificateClientCompany || null,
        certificate_client_attention: fieldSheetCreateForm.attention.trim() || null,
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
    setFieldSheetValidationErrors({});
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

  function openCertificateClientModal() {
    setError('');
    const billingClient = clientsById.get(selectedOrder?.client_id);
    const profiles = (billingClient?.certificate_profiles ?? []).filter((profile) => profile.is_active !== false);
    const preferred = profiles.find((profile) => profile.is_default) ?? profiles[0];
    const hasCurrentValues = Boolean(
      fieldSheetCreateForm.certificateClientCompany || fieldSheetCreateForm.certificateClientAddress
    );
    setFieldSheetCreateForm((current) => ({ ...current, certificateClientMode: 'different' }));
    setCertificateClientDraft({
      profileId: hasCurrentValues ? '' : preferred ? String(preferred.id) : '',
      label: hasCurrentValues ? '' : preferred?.label ?? '',
      company: hasCurrentValues
        ? fieldSheetCreateForm.certificateClientCompany
        : preferred?.company ?? '',
      address: hasCurrentValues
        ? fieldSheetCreateForm.certificateClientAddress
        : preferred?.address ?? '',
      attention: hasCurrentValues ? fieldSheetCreateForm.attention : preferred?.attention ?? '',
      saveToClient: !preferred && !hasCurrentValues,
      isDefault: false,
    });
    setIsCertificateClientModalOpen(true);
  }

  function closeCertificateClientModal() {
    setIsCertificateClientModalOpen(false);
    if (!fieldSheetCreateForm.certificateClientCompany || !fieldSheetCreateForm.certificateClientAddress) {
      setFieldSheetCreateForm((current) => ({ ...current, certificateClientMode: 'billing' }));
    }
  }

  function selectCertificateProfile(profileId) {
    const billingClient = clientsById.get(selectedOrder?.client_id);
    const profile = (billingClient?.certificate_profiles ?? []).find(
      (item) => String(item.id) === String(profileId)
    );
    setCertificateClientDraft((current) => ({
      ...current,
      profileId,
      label: profile?.label ?? '',
      company: profile?.company ?? '',
      address: profile?.address ?? '',
      attention: profile?.attention ?? '',
      saveToClient: !profile,
      isDefault: false,
    }));
  }

  async function applyCertificateClientDraft() {
    const company = certificateClientDraft.company.trim();
    const address = certificateClientDraft.address.trim();
    if (!company || !address) {
      setError('Captura empresa y domicilio para el cliente del certificado.');
      return;
    }
    setIsSaving(true);
    setError('');
    try {
      if (certificateClientDraft.saveToClient && selectedOrder?.client_id) {
        const savedProfile = await createClientCertificateProfile(selectedOrder.client_id, {
          label: certificateClientDraft.label.trim() || company,
          company,
          address,
          attention: certificateClientDraft.attention.trim() || null,
          is_default: Boolean(certificateClientDraft.isDefault),
        });
        setClients((current) => current.map((client) => {
          if (client.id !== selectedOrder.client_id) return client;
          const profiles = certificateClientDraft.isDefault
            ? (client.certificate_profiles ?? []).map((profile) => ({ ...profile, is_default: false }))
            : (client.certificate_profiles ?? []);
          return { ...client, certificate_profiles: [...profiles, savedProfile] };
        }));
      }
      setFieldSheetCreateForm((current) => ({
        ...current,
        certificateClientMode: 'different',
        certificateClientCompany: company,
        certificateClientAddress: address,
        attention: certificateClientDraft.attention.trim(),
      }));
      setIsCertificateClientModalOpen(false);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
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

  async function downloadMultipartCapture(blob, contentType) {
    const boundary = contentType.match(/boundary=([^;]+)/i)?.[1]?.replaceAll('"', '');
    if (!boundary) throw new Error('La respuesta del paquete de Captura no incluye un límite multipart válido.');
    const payload = new TextDecoder('latin1').decode(await blob.arrayBuffer());
    const parts = payload.split(`--${boundary}`).slice(1, -1);
    if (!parts.length) throw new Error('El paquete de Captura no contiene archivos.');
    let downloads = 0;
    parts.forEach((part) => {
      const separator = part.indexOf('\r\n\r\n');
      if (separator < 0) return;
      const headers = part.slice(0, separator);
      const filename = headers.match(/filename="?([^"\r\n]+)"?/i)?.[1];
      const mime = headers.match(/Content-Type:\s*([^\r\n]+)/i)?.[1] || 'application/octet-stream';
      if (!filename) return;
      const body = part.slice(separator + 4).replace(/\r\n$/, '');
      triggerBlobDownload(new Blob([Uint8Array.from(body, (char) => char.charCodeAt(0))], { type: mime }), filename);
      downloads += 1;
    });
    if (!downloads) throw new Error('El paquete multipart no contiene adjuntos descargables.');
  }

  function openWorkOrderPdf(mode = 'view') {
    if (!selectedOrder) return;

    const workOrderId = selectedWorkOrderContext?.id;
    const url = workOrderId
      ? getServiceWorkOrderPdfUrl(workOrderId)
      : getServiceOrderWorkOrdersPdfUrl(selectedOrder.id);

    const pdfWindow = window.open(url, '_blank', 'noopener,noreferrer');

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
        selectedWorkOrderContext?.number ?? selectedOrder.work_order_number,
        getClientDisplayName(clientsById.get(selectedOrder.client_id)),
        selectedWorkOrderContext?.id ?? null,
        !selectedWorkOrderContext?.id
      );
      triggerBlobDownload(blob, filename);
      setNotice(`PDF ${filename} generado correctamente`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  function getFieldSheetEquipmentName(sheet) {
    if (selectedEquipmentForSheet?.id === sheet?.equipment_id) {
      return selectedEquipmentForSheet.name;
    }
    return equipment.find((item) => item.id === sheet?.equipment_id)?.name || '';
  }

  async function openFieldSheetPdf(mode = 'view', sheet = selectedFieldSheet) {
    if (!sheet) return;
    const pdfWindow = window.open('', '_blank');
    if (!pdfWindow) {
      setError('El navegador bloqueó la vista previa. Permite ventanas emergentes para imprimir.');
      return;
    }

    if (mode === 'print') {
      pdfWindow.addEventListener('load', () => {
        pdfWindow.focus();
        pdfWindow.print();
      }, { once: true });
    }

    setError('');
    try {
      const { blob } = await downloadFieldSheetPdf(
        sheet.id,
        sheet.work_order_number,
        getFieldSheetEquipmentName(sheet)
      );
      const pdfUrl = URL.createObjectURL(blob);
      pdfWindow.location.replace(pdfUrl);
      window.setTimeout(() => URL.revokeObjectURL(pdfUrl), 5 * 60 * 1000);
    } catch (requestError) {
      pdfWindow.close();
      setError(requestError.message);
    }
  }

  async function handleDownloadFieldSheetPdf(sheet = selectedFieldSheet) {
    if (!sheet) return;
    setError('');
    setNotice('');
    try {
      const { blob, filename } = await downloadFieldSheetPdf(
        sheet.id,
        sheet.work_order_number,
        getFieldSheetEquipmentName(sheet)
      );
      triggerBlobDownload(blob, filename);
      setNotice(`PDF ${filename} generado correctamente`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleDownloadCapturePackage(workOrderId = null) {
    if (!selectedOrder) return;
    setError('');
    try {
      const summary = await getCapturePackageSummary(selectedOrder.id);
      if (!summary.ready_total) {
        const reasons = summary.work_orders.flatMap((group) => group.blocked.map((item) => `${item.equipment_name}: ${item.reason}`));
        throw new Error(`No hay equipos listos. ${reasons.join(' · ')}`);
      }
      const fallbackFilename = `${selectedOrder.folio || `ETS-${selectedOrder.id}`}${workOrderId ? `-OT-${selectedWorkOrderContext?.number || workOrderId}` : ''}.zip`;
      const { blob, filename, contentType } = await downloadCapturePackage(selectedOrder.id, workOrderId, fallbackFilename);
      if (contentType.toLowerCase().startsWith('multipart/mixed')) {
        await downloadMultipartCapture(blob, contentType);
      } else {
        triggerBlobDownload(blob, filename);
      }
      setNotice('Paquete de Captura descargado.');
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleDownloadCaptureMaster(certificate) {
    setError('');
    try {
      const captureFile = latestCaptureFileByCertificateId.get(certificate.id);
      const { blob, filename } = await downloadCaptureMaster(certificate.id, captureFile?.filename);
      triggerBlobDownload(blob, filename);
      setNotice(`Master ${filename} descargado para revisión.`);
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function handleCaptureFilesUpload(files, input) {
    if (!selectedOrder || !files?.length) return;
    setError('');
    setNotice('');
    try {
      const serviceOrderId = selectedOrder.id;
      const result = await uploadCaptureFiles(serviceOrderId, files);
      setCaptureProcessingResult(result);
      await Promise.all([
        loadServiceOrderData(),
        loadCaptureFilesData(serviceOrderId),
      ]);
      setNotice('Paquete procesado correctamente. La información de Captura ya está actualizada.');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      if (input) input.value = '';
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
    const validationErrors = getFieldSheetCompletionValidation(fieldSheetForm, selectedFieldSheet?.template_definition
      ? { [fieldSheetForm.templateKey || 'general']: selectedFieldSheet.template_definition }
      : fieldSheetTemplatesByKey);
    if (Object.keys(validationErrors).length) {
      setFieldSheetValidationErrors(validationErrors);
      setError('Completa los campos marcados antes de avanzar.');
      setFieldSheetTab('technical');
      window.setTimeout(() => {
        document.querySelector('.field-sheet-modal [data-validation-error="true"] input, .field-sheet-modal [data-validation-error="true"] textarea, .field-sheet-modal [data-validation-error="true"] select')?.focus();
      }, 0);
      return;
    }
    setFieldSheetValidationErrors({});
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

  async function reviewFieldSheetRecord(sheet) {
    if (!sheet) return null;
    if (sheet.status !== 'completed') {
      setError('Solo una hoja completada puede enviarse a revision.');
      return null;
    }
    setIsSaving(true);
    setError('');
    setNotice('');
    try {
      const reviewed = await reviewFieldSheet(sheet.id);
      if (selectedFieldSheet?.id === reviewed.id) {
        setSelectedFieldSheet(reviewed);
        setFieldSheetForm(fieldSheetToForm(reviewed));
      }
      setFieldSheets((current) =>
        current.map((sheet) => (sheet.id === reviewed.id ? reviewed : sheet))
      );
      setNotice('Hoja de campo enviada a revision');
      await loadServiceOrderData();
      return reviewed;
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
    return null;
  }

  async function reviewCurrentFieldSheet() {
    return reviewFieldSheetRecord(selectedFieldSheet);
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
    if (action === 'request-correction') {
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
      await Promise.all([
        loadServiceOrderData(),
        selectedOrder?.id ? loadCaptureFilesData(selectedOrder.id) : Promise.resolve([]),
      ]);
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

  async function openAuthenticatedCertificatePdf(certificate) {
    if (!certificate.authenticated_pdf_path) {
      setError('El certificado aun no tiene PDF autenticado.');
      return;
    }
    const pdfWindow = window.open('', '_blank');
    if (!pdfWindow) {
      setError('No se pudo abrir el PDF autenticado.');
      return;
    }
    try {
      const { blob } = await downloadAuthenticatedCertificatePdf(
        certificate.id,
        certificate.expected_folio || certificate.folio,
        certificate.authentication_code,
      );
      const pdfUrl = URL.createObjectURL(blob);
      pdfWindow.location.replace(pdfUrl);
      window.setTimeout(() => URL.revokeObjectURL(pdfUrl), 5 * 60 * 1000);
    } catch (requestError) {
      pdfWindow.close();
      setError(requestError.message);
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

  function summarizeBatchResult(result) {
    const processed = result.results?.filter((item) => ['authenticated', 'released'].includes(item.status)).map((item) => item.folio).filter(Boolean) ?? [];
    const actionCount = result.authenticated ?? result.released ?? 0;
    return `${actionCount} procesados, ${result.skipped} omitidos, ${result.errors} errores${processed.length ? `: ${processed.join(', ')}` : ''}`;
  }

  function handleReleaseAuthenticatedBatch() {
    if (!selectedOrder) return;
    openConfirm({
      title: 'Liberar autenticados',
      message: 'Se liberarán al cliente los certificados autenticados que tengan su PDF y cumplan la regla financiera vigente. El lote continuará aunque algún certificado falle.',
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

  function handleDeleteWorkOrder(workOrder) {
    if (!selectedOrder || !workOrder || isLegacyWorkOrder(workOrder)) return;
    const clientName = getClientDisplayName(clientsById.get(selectedOrder.client_id));
    openConfirm({
      title: 'Eliminar orden de trabajo',
      message: `OT-${workOrder.work_order_number}\nCliente: ${clientName || 'No disponible'}\n\nEsta operación eliminará definitivamente la orden y sus equipos, hojas de campo, certificados y demás registros operativos exclusivos. Los recursos compartidos por otras OT se conservarán.`,
      confirmText: 'Eliminar definitivamente',
      variant: 'danger',
      onConfirm: async () => {
        setError('');
        setNotice('');
        setIsSaving(true);
        try {
          await deleteServiceWorkOrder(workOrder.id);
          if (Number(selectedWorkOrderContext?.id) === Number(workOrder.id)) {
            clearWorkOrderContext();
          }
          setNotice(`La OT-${workOrder.work_order_number} fue eliminada definitivamente`);
          await loadServiceOrderData();
        } catch (requestError) {
          setError(requestError.message);
        } finally {
          setIsSaving(false);
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
                        <div
              aria-live="polite"
              className={`ets-autosave-status is-${autosaveStatus}`}
            >
              <span className="ets-autosave-status__dot" />

              <div>
                <strong>
                  {autosaveStatus === 'pending'
                    ? 'Cambios pendientes'
                    : autosaveStatus === 'saving'
                      ? 'Guardando cambios...'
                      : autosaveStatus === 'saved'
                        ? 'Cambios guardados'
                        : autosaveStatus === 'error'
                          ? 'Error al guardar'
                          : 'Autosave activo'}
                </strong>

                <small>
                  {autosaveStatus === 'error'
                    ? autosaveError
                    : lastAutosaveAt
                      ? `Último guardado: ${lastAutosaveAt.toLocaleTimeString(
                          'es-MX',
                          {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          },
                        )}`
                      : 'Los cambios se guardan automáticamente'}
                </small>
              </div>

              {autosaveStatus === 'error' ? (
                <button
                  className="table-button"
                  disabled={isSaving}
                  onClick={() => handleOrderSubmit()}
                  type="button"
                >
                  Reintentar
                </button>
              ) : null}
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
              <button
                className="primary-button"
                disabled={
                  isSaving ||
                  autosaveStatus === 'saving' ||
                  activeTab !== 'info'
                }
                form="service-order-summary-form"
                type="submit"
              >
                {isSaving || autosaveStatus === 'saving'
                  ? 'Guardando...'
                  : <Save size={17} aria-label="Guardar" />}
              </button>
              {canUseAdminActions ? (
                <div className="ets-admin-actions">
                  <button className="table-button" onClick={() => setIsAdminActionsOpen((open) => !open)} type="button">
                    ⋮ Acciones
                  </button>
                  {isAdminActionsOpen ? (
                    <div className="ets-admin-actions__menu">
                      <button onClick={() => setActiveTab('info')} type="button">Editar ETS</button>
                      <button onClick={() => setActiveTab('documents')} type="button">Exportar</button>
                      <button disabled type="button">Duplicar</button>
                      <button disabled type="button">Archivar</button>
                      <button className="is-danger" onClick={handleDeleteServiceOrder} type="button">Eliminar</button>
                    </div>
                  ) : null}
                </div>
              ) : null}
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
            {selectedWorkOrderContext ? (
              <div className="ets-active-context">
                <span>Contexto activo: {selectedWorkOrderContext.label}</span>
                <button className="table-button" onClick={clearWorkOrderContext} type="button">
                  Ver todo el ETS
                </button>
              </div>
            ) : null}
            {technicalSubEtsEquipment ? (
              <div className="ets-subets-context">
                <div>
                  <span>Sub-ETS técnico</span>

                  <strong>
                    {technicalSubEtsEquipment.name ||
                      'Equipo'}
                  </strong>

                  <small>
                    {[
                      technicalSubEtsEquipment.serial_number
                        ? `Serie ${technicalSubEtsEquipment.serial_number}`
                        : null,
                      selectedWorkOrderContext?.label,
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </small>
                </div>
                <button
                  className="table-button"
                  onClick={closeTechnicalSubEts}
                  type="button"
                >
                  ← Volver a Equipos
                </button>
              </div>
            ) : null}
            <div className="ets-folder-tabs" role="tablist" aria-label="Carpetas del expediente">
                {visibleEtsTabs.map(([key, label]) => (
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
                  <section className="quotation-section ets-equipment-condition-section">
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
                      <button
                        className="ets-summary-work-orders ets-summary-card"
                        onClick={() => setIsWorkOrdersModalOpen(true)}
                        type="button"
                        >
                          <span>Órdenes de trabajo</span>
                          <strong>{relatedWorkOrders.length} orden(es)</strong>
                          <small>
                            {relatedWorkOrders.reduce((sum, order) => sum + getWorkOrderEquipmentCount(order), 0)} equipo(s)
                          </small>
                      </button>
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
                        <strong>{workOrderCapacitySummary.totalRegistered} / {workOrderCapacitySummary.totalLimit}</strong>
                        <small>{workOrderCapacitySummary.groups.length} OT</small>
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

                  <div className="quotation-detail-save field-sheet-action-panel">
                    <span>
                      Los cambios se guardan automáticamente. El resumen queda
                      listo cuando exista fecha de agenda, fecha de servicio y
                      técnico asignado.
                    </span>

                    <div className="toolbar-actions">
                      <button
                        className="table-button"
                        disabled={
                          isSaving ||
                          autosaveStatus === 'saving'
                        }
                        type="submit"
                      >
                        {isSaving || autosaveStatus === 'saving'
                          ? 'Guardando...'
                          : <Save size={17} aria-label="Guardar" />}
                      </button>
                    </div>
                  </div>
                </form>
              </>
            ) : null}

            {activeTab === 'sale' && selectedOrderHasSale ? (
              <SaleEtsTab order={selectedOrder} user={user} users={users} />
            ) : null}

            {activeTab === 'maintenance' && selectedOrderHasMaintenance ? (
              <MaintenanceEtsTab order={selectedOrder} user={user} users={users} />
            ) : null}

            {activeTab === 'equipment' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>Equipos de la orden</p>
                    <h3>Equipos registrados: {workOrderCapacitySummary.totalRegistered} / {workOrderCapacitySummary.totalLimit}</h3>
                    <span className={`ets-inline-stage is-${selectedStageState.equipment?.status ?? 'pending'}`}>
                      {selectedStageState.equipment?.label ?? 'Pendiente'}
                    </span>
                  </div>
                  <div className="toolbar-actions">
                    {selectedWorkOrderContext ? (
                      <button className="table-button" onClick={clearWorkOrderContext} type="button">
                        Volver a Ordenes de Trabajo
                      </button>
                    ) : null}
                    {canUseTechnicalActions ? (
                      <button className="primary-button" disabled={isSaving} onClick={() => openEquipmentModal()} type="button">
                        + Agregar equipo
                      </button>
                    ) : null}
                  </div>
                </div>
                <div className="ets-metric-strip">
                  <span className="ets-metric-badge"><strong>{safeNumber(selectedOrderMetrics.expectedEquipment)}</strong>Esperados cotizacion</span>
                  <span className="ets-metric-badge"><strong>{selectedEquipment.length}</strong>Registrados</span>
                  <span className="ets-metric-badge"><strong>{workOrderCapacitySummary.totalRegistered} / {workOrderCapacitySummary.totalLimit}</strong>Capacidad total OT</span>
                  <span className="ets-metric-badge"><strong>{selectedFieldSheets.length} / {workOrderCapacitySummary.totalLimit}</strong>Hojas</span>
                  {['traceable', 'accredited_iso_17025', 'accredited_linked_lab'].map((scope) => (
                    <span className="ets-metric-badge" key={scope}>
                      <strong>
                        {safeNumber(selectedOrderCertificateCapacity[scope]?.used)} / {safeNumber(selectedOrderCertificateCapacity[scope]?.quoted)}
                      </strong>
                      {calibrationScopeBadgeLabels[scope]}
                    </span>
                  ))}
                </div>
                {shouldShowSignatureLauncher && renderSignatureLauncher()}
                {!hasAvailableWorkOrderCapacity ? (
                  <div className="clients-empty">Todas las Ordenes de Trabajo llegaron a su capacidad.</div>
                ) : null}
                <div className="ets-stage-note">
                  Equipos queda lista automaticamente cuando hay equipos vinculados a las Ordenes de Trabajo del ETS.
                </div>
                {!selectedWorkOrderContext ? (
                  <div className="ets-work-order-folder-grid">
                    {workOrderCapacitySummary.groups.map((workOrder) => {
                      const sheets = getWorkOrderFieldSheets(workOrder);
                      const certs = getWorkOrderCertificates(workOrder);
                      return (
                        <article className="ets-work-order-folder" key={workOrder.id}>
                          <div>
                            <span>Orden de Trabajo</span>
                            <strong>OT-{workOrder.work_order_number ?? '-'}</strong>
                          </div>
                          <mark className={`quotation-status status-${workOrder.status}`}>
                            {serviceOrderStatusLabels[workOrder.status] ?? workOrder.status ?? 'Pendiente'}
                          </mark>
                          <dl>
                            <div><dt>Equipos</dt><dd>{workOrder.registered} / {workOrder.limit}</dd></div>
                            <div><dt>Hojas</dt><dd>{sheets.length} / {workOrder.registered}</dd></div>
                            <div><dt>Certificados</dt><dd>{certs.filter((item) => item.authenticated_pdf_path || item.status === 'released_to_client').length} / {certs.length}</dd></div>
                          </dl>
                          <div className="toolbar-actions">
                            <button className="table-button table-button--primary" onClick={() => openTabFromSummary('equipment', { workOrder })} type="button">
                              Abrir
                            </button>
                            <button className="table-button" onClick={() => openTabFromSummary('field-sheet', { workOrder })} type="button">
                              Hojas
                            </button>
                            <button className="table-button" onClick={() => openTabFromSummary('certificates', { workOrder })} type="button">
                              Certificados
                            </button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                ) : null}
                {selectedWorkOrderContext ? (
                <div className="ets-work-order-equipment-groups">
                  {workOrderCapacitySummary.groups.map((workOrder) => {
                    const groupEquipment = filteredSelectedEquipment.filter((item) => getWorkOrderEquipment(workOrder, [item]).length > 0);
                    if (selectedWorkOrderContext && groupEquipment.length === 0) return null;
                    return (
                      <section className="ets-work-order-equipment-group" key={workOrder.id}>
                        <div className="ets-work-order-equipment-group__header">
                          <div>
                            <p>Orden de Trabajo</p>
                            <h4>OT-{workOrder.work_order_number ?? '-'}</h4>
                          </div>
                          <mark className={`quotation-status status-${workOrder.status}`}>
                            {serviceOrderStatusLabels[workOrder.status] ?? workOrder.status ?? 'Pendiente'}
                          </mark>
                          <span className="ets-metric-badge">
                            <strong>{workOrder.registered} / {workOrder.limit}</strong>
                            Capacidad usada
                          </span>
                        </div>
                        <div className="ets-equipment-card-grid ets-animated-list">
                          {groupEquipment.map((item) => {
                            const sheet = fieldSheetsByEquipmentId.get(item.id);

                            const certificate =
                              activeCertificatesByEquipmentId.get(item.id);

                            const operationalContext =
                              getEquipmentOperationalContext(item);

                            const nextStep = getEquipmentNextStep({
                              item,
                              operationalContext,
                              sheet,
                              certificate,
                            });

                            const scopeLabel = item.calibration_scope
                              ? calibrationScopeLabels[item.calibration_scope] ||
                                item.calibration_scope
                              : null;

                            return (
                              <button
                                className={[
                                  'ets-equipment-card',
                                  `ets-equipment-card--${operationalContext.key}`,
                                  'ets-list-item',
                                  exitingEquipmentIds.includes(item.id)
                                    ? 'is-exiting'
                                    : '',
                                ]
                                  .filter(Boolean)
                                  .join(' ')}
                                key={item.id}
                                onClick={() => {
                                  const context =
                                    getEquipmentOperationalContext(item);
                                  if (context.hasMetrology) {
                                    openTechnicalSubEts(item);
                                    return;
                                  }
                                  openEquipmentDetail(item);
                                }}      
                                type="button"
                              >
                                <header className="ets-equipment-card__header">
                                  <div className="ets-equipment-card__heading">
                                    <span
                                      className={`ets-equipment-card__eyebrow is-${operationalContext.key}`}
                                    >
                                      {operationalContext.label}
                                    </span>

                                    <strong className="ets-equipment-card__name">
                                      {item.name || 'Equipo sin nombre'}
                                    </strong>
                                  </div>

                                  <mark
                                    className={`quotation-status status-${item.status}`}
                                  >
                                    {equipmentStatusLabels[item.status] ??
                                      item.status ??
                                      'Pendiente'}
                                  </mark>
                                </header>

                                <div className="ets-equipment-card__identity">
                                  <span>{item.brand || 'Marca pendiente'}</span>

                                  <i aria-hidden="true">·</i>

                                  <span>{item.model || 'Modelo pendiente'}</span>
                                </div>

                                <dl className="ets-equipment-card__identifiers">
                                  <div>
                                    <dt>Serie</dt>
                                    <dd>{item.serial_number || 'Pendiente'}</dd>
                                  </div>

                                  <div>
                                    <dt>ID interno</dt>
                                    <dd>{item.internal_id || 'Pendiente'}</dd>
                                  </div>
                                </dl>

                                <div className="ets-equipment-card__flow">
                                  <article className="ets-equipment-card__flow-state">
                                    <span>Operación</span>
                                    <strong>{operationalContext.label}</strong>

                                    {scopeLabel ? (
                                      <small>{scopeLabel}</small>
                                    ) : (
                                      <small>Sin proceso metrológico</small>
                                    )}
                                  </article>

                                  {operationalContext.hasMetrology ? (
                                    <article className="ets-equipment-card__flow-state">
                                      <span>Proceso técnico</span>

                                      <strong>
                                        {sheet
                                          ? fieldSheetStatusLabels[sheet.status] ??
                                            sheet.status ??
                                            'Hoja creada'
                                          : 'Pendiente'}
                                      </strong>

                                      <small>
                                        {certificate
                                          ? certificateStatusLabels[certificate.status] ??
                                            certificate.status
                                          : 'Certificado pendiente'}
                                      </small>
                                    </article>
                                  ) : null}
                                </div>

                                <footer className="ets-equipment-card__footer">
                                  <div>
                                    <span>{nextStep.label}</span>
                                    <strong>{nextStep.value}</strong>
                                  </div>

                                  <span className="ets-equipment-card__open">
                                    {operationalContext.hasMetrology
                                      ? 'Abrir proceso'
                                      : 'Ver equipo'}
                                    <ChevronRight size={16} />  
                                  </span>  
                                </footer>
                              </button>
                            );
                          })}
                        </div>
                      </section>
                    );
                  })}
                  {!filteredSelectedEquipment.length && (selectedEquipment.length || etsSearch || selectedWorkOrderContext) ? (
                    <div className="clients-empty">No hay equipos que coincidan con el filtro activo.</div>
                  ) : null}
                  {!selectedEquipment.length ? (
                    <div className="clients-empty">Todavia no hay equipos vinculados a esta orden.</div>
                  ) : null}
                </div>
                ) : null}
              </section>
            ) : null}

            {activeTab === 'field-sheet' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Hoja de campo</p>
                  <h3>Preparación y captura del ETS</h3>
                </div>
                <div className="ets-field-sheet-subtabs" role="tablist" aria-label="Vistas de Hojas de Campo del ETS">
                  <button aria-selected={fieldSheetWorkspaceView === 'capture'} className={fieldSheetWorkspaceView === 'capture' ? 'is-active' : ''} onClick={() => setFieldSheetWorkspaceView('capture')} type="button">Captura de hojas</button>
                  <button aria-selected={fieldSheetWorkspaceView === 'work-orders'} className={fieldSheetWorkspaceView === 'work-orders' ? 'is-active' : ''} onClick={() => { setFieldSheetWorkspaceView('work-orders'); clearWorkOrderContext(); }} type="button">Por Orden de Trabajo</button>
                </div>
                <div className="ets-stage-note">
                  Esta carpeta muestra únicamente las hojas, equipos y Órdenes de Trabajo del ETS {selectedOrder.folio}.
                </div>

                {fieldSheetWorkspaceView === 'capture' && selectedWorkOrderContext ? (
                  <div className="ets-stage-note">
                    Mostrando flujo de la {selectedWorkOrderContext.label}.
                    <button className="table-button" onClick={clearWorkOrderContext} type="button">Ver todas</button>
                  </div>
                ) : null}

                {fieldSheetWorkspaceView === 'capture' && selectedEquipment.length ? (
                  <div className="field-sheet-prep-list">
                    {filteredSelectedEquipment
                      .map((item) => {
                        const sheet = fieldSheetsByEquipmentId.get(item.id);
                        return (
                          <article className="glass-card-mini ets-list-item ets-field-sheet-capture-card" key={item.id}>
                            <div><strong>{item.name}</strong><span>{[item.brand, item.model, item.serial_number || 'Sin serie'].filter(Boolean).join(' · ')}</span></div>
                            <div><small>Identificación</small><strong>{item.internal_id || '-'}</strong></div>
                            <div><small>Plantilla</small><strong>{sheet ? getFieldSheetTemplateLabel(sheet.template_key) : 'Por seleccionar'}</strong></div>
                            <mark className={`quotation-status status-${sheet?.status || 'pending'}`}>{sheet ? fieldSheetStatusLabels[sheet.status] ?? sheet.status : 'Sin hoja'}</mark>
                            <div className="toolbar-actions">
                              <button className="table-button table-button--primary" onClick={() => openFieldSheetForEquipment(item)} type="button">{sheet ? ['draft', 'in_progress', 'returned_to_technician', 'rejected'].includes(sheet.status) ? 'Continuar captura' : 'Abrir hoja' : 'Crear hoja'}</button>
                              {sheet ? <button className="table-button" onClick={() => handleDownloadFieldSheetPdf(sheet)} type="button">Descargar PDF</button> : null}
                              {sheet?.status === 'completed' ? <button className="table-button" disabled={isSaving} onClick={() => reviewFieldSheetRecord(sheet)} type="button">Enviar a revisión</button> : null}
                            </div>
                          </article>
                        );
                      })}
                  </div>
                ) : null}

                {fieldSheetWorkspaceView === 'capture' && !selectedEquipment.length ? (
                  <div className="clients-empty">Agrega equipos para preparar hojas de campo.</div>
                ) : null}

                {fieldSheetWorkspaceView === 'work-orders' ? (
                  <div className="ets-field-sheet-work-orders">
                    {workOrderCapacitySummary.groups.map((workOrder) => {
                      const metrics = getFieldSheetWorkOrderMetrics(workOrder);
                      const expanded = expandedFieldSheetWorkOrders.has(workOrder.id);
                      const equipmentListId = `field-sheet-work-order-${workOrder.id}-equipment`;
                      return (
                        <article className={expanded ? 'ets-field-sheet-work-order is-expanded' : 'ets-field-sheet-work-order'} key={workOrder.id}>
                          <button aria-controls={equipmentListId} aria-expanded={expanded} className="ets-field-sheet-work-order__summary" onClick={() => toggleFieldSheetWorkOrder(workOrder.id)} type="button">
                            <span>{expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}</span>
                            <div><small>Orden de Trabajo</small><strong>OT-{workOrder.work_order_number ?? '-'}</strong><span>{getClientDisplayName(clientsById.get(selectedOrder.client_id))}</span></div>
                            <div className="ets-field-sheet-work-order__metrics"><span><strong>{metrics.equipmentCount}</strong>Equipos</span><span><strong>{metrics.created} / {metrics.equipmentCount}</strong>Hojas creadas</span><span><strong>{metrics.approved}</strong>Aprobadas</span><span><strong>{metrics.capture}</strong>En captura</span><span><strong>{metrics.pending}</strong>Pendientes</span></div>
                            <div className="ets-field-sheet-work-order__progress"><div><span style={{ width: `${metrics.progress}%` }} /></div><strong>{metrics.created} / {metrics.equipmentCount} hojas</strong><small>{metrics.progress}%</small></div>
                            <mark className={`quotation-status status-${workOrder.status}`}>{serviceOrderStatusLabels[workOrder.status] ?? workOrder.status ?? 'Pendiente'}</mark>
                          </button>

                          {expanded ? (
                            <div className="ets-field-sheet-work-order__equipment" id={equipmentListId}>
                              {metrics.rows.length ? metrics.rows.map(({ item, sheet }) => {
                                const certificate = activeCertificatesByEquipmentId.get(item.id);
                                return (
                                  <article className="ets-field-sheet-equipment-row" key={item.id}>
                                    <div><strong>{item.name}</strong><span>{[item.brand, item.model].filter(Boolean).join(' · ') || 'Sin marca/modelo'}</span></div>
                                    <dl><div><dt>Serie</dt><dd>{item.serial_number || '-'}</dd></div><div><dt>Identificación</dt><dd>{item.internal_id || '-'}</dd></div><div><dt>Hoja</dt><dd>{sheet ? getFieldSheetTemplateLabel(sheet.template_key) : 'Sin crear'}</dd></div><div><dt>Folio</dt><dd>{sheet?.reserved_certificate_folio || certificate?.expected_folio || certificate?.folio || '-'}</dd></div><div><dt>Actualizada</dt><dd>{sheet ? formatDateTime(sheet.updated_at) : '-'}</dd></div></dl>
                                    <mark className={`quotation-status status-${sheet?.status || 'pending'}`}>{sheet ? fieldSheetStatusLabels[sheet.status] ?? sheet.status : 'Sin hoja'}</mark>
                                    <div className="toolbar-actions">
                                      <button className="table-button table-button--primary" onClick={() => openFieldSheetForEquipment(item, workOrder)} type="button">{sheet ? ['draft', 'in_progress', 'returned_to_technician', 'rejected'].includes(sheet.status) ? 'Continuar captura' : 'Abrir hoja' : 'Crear hoja'}</button>
                                      {sheet ? <button className="table-button" onClick={() => handleDownloadFieldSheetPdf(sheet)} type="button">Descargar PDF</button> : null}
                                      {sheet?.status === 'completed' ? <button className="table-button" disabled={isSaving} onClick={() => reviewFieldSheetRecord(sheet)} type="button">Enviar a revisión</button> : null}
                                    </div>
                                  </article>
                                );
                              }) : <div className="clients-empty">Esta Orden de Trabajo todavía no tiene equipos.</div>}
                            </div>
                          ) : null}
                          <div className="toolbar-actions">
                            <button className="table-button" onClick={() => handleDownloadCapturePackage(workOrder.id)} type="button">Descargar paquete de Captura</button>
                          </div>
                        </article>
                      );
                    })}
                  </div>
                ) : null}
              </section>
            ) : null}

            {activeTab === 'capture' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>Captura</p>
                    <h3>Masters XLSX para revisión de Calidad</h3>
                  </div>
                  <button className="table-button table-button--primary" onClick={() => handleDownloadCapturePackage()} type="button">Descargar paquete de Captura</button>
                  <label className="table-button table-button--file">Sube el ZIP generado por el ERP o los archivos Excel corregidos.<input accept=".xls,.xlsx,.xlsm,.zip" multiple onChange={(event) => handleCaptureFilesUpload(event.target.files, event.target)} type="file" /></label>
                  {canUseAdminActions ? (
                    <button className="table-button" onClick={() => openExceptionRequest('Captura', 'Hojas')} type="button">
                      {exceptionActionLabel()}
                    </button>
                  ) : null}
                </div>
                <CaptureProcessingSummary result={captureProcessingResult} />
                <div className="ets-metric-strip">
                  {[
                    ['Masters esperados', captureMasterMetrics.expected],
                    ['Masters identificados', captureMasterMetrics.identified],
                    ['Alertas Master', captureMasterMetrics.warnings],
                    ['Diferencias Master', captureMasterMetrics.mismatches],
                    ['Masters sin identificar', captureMasterMetrics.unidentified]
                  ].map(([label, value]) => (
                    <span className="ets-metric-badge" key={label}><strong>{safeNumber(value)}</strong>{label}</span>
                  ))}
                </div>
                <div className="ets-stage-note">
                  Cada certificado puede enviarse a Calidad cuando su Master está identificado y no contiene diferencias bloqueantes. Las advertencias no bloquean.
                </div>
                <WorkOrderFlowGroups
                  emptyMessage="No hay certificados pendientes de Captura en este ETS."
                  equipmentById={equipmentById}
                  getGroupState={(items) => items.every((item) => ['ready_for_quality', 'quality_review', 'match_validated', 'quality_approved', 'authenticated', 'released_to_client'].includes(item.status)) ? { label: 'LISTA', tone: 'approved' } : { label: 'EN PROCESO', tone: 'capture_in_progress' }}
                  items={filteredSelectedCertificates}
                  orders={[selectedOrder]}
                  renderItem={(certificate) => {
                    const item = equipmentById.get(certificate.equipment_id);
                    const captureFile = latestCaptureFileByCertificateId.get(certificate.id);
                    const masterReadiness = authoritativeCaptureReadinessByCertificateId.get(certificate.id) || getCaptureMasterReadiness({ certificate, equipment: item, captureFile });
                    const uploadStatuses = ['expected', 'field_sheet_ready', 'capture_pending', 'capture_in_progress', 'pdf_uploaded', 'quality_rejected', 'correction_requested', 'returned_to_technician'];
                    const hasCaptureAction = uploadStatuses.includes(certificate.status) && !certificate.authenticated_pdf_path;
                    return <article className="flow-certificate-card" key={certificate.id}><div className="flow-certificate-card__title"><div><span>Certificado</span><strong>{certificate.expected_folio || certificate.folio}</strong></div><mark className={`quotation-status status-${certificate.status}`}>{certificateStatusLabels[certificate.status] ?? certificate.status}</mark></div><dl><div><dt>Equipo</dt><dd>{item?.name || '-'}</dd></div><div><dt>Serie</dt><dd>{item?.serial_number || '-'}</dd></div><div><dt>Master</dt><dd>{masterReadiness.identified ? 'Identificado' : 'Pendiente'}</dd></div><div><dt>Alertas</dt><dd>{masterReadiness.warnings.length}</dd></div><div><dt>Diferencias</dt><dd>{masterReadiness.mismatches.length}</dd></div><div><dt>Readiness</dt><dd>{masterReadiness.ready ? 'Listo para Calidad' : masterReadiness.reason}</dd></div></dl>{canUseCaptureActions && hasCaptureAction ? <div className="toolbar-actions"><button className="table-button table-button--primary" disabled={isSaving || !masterReadiness.ready} onClick={() => handleCertificateWorkflow(certificate, 'send-to-quality', `Certificado ${certificate.folio} enviado a Calidad`)} title={masterReadiness.ready ? 'Enviar únicamente este certificado a Calidad' : masterReadiness.reason} type="button">Enviar a Calidad</button></div> : <span className="flow-action-complete">Enviado a Calidad</span>}</article>;
                  }}
                />
              </section>
            ) : null}

            {activeTab === 'quality' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <div>
                    <p>Calidad</p>
                    <h3>Revision, aprobacion y autenticación</h3>
                  </div>
                  {canUseQualityActions ? (
                    <div className="toolbar-actions">
                      {canUseAdminActions ? (
                        <button className="table-button" onClick={() => openExceptionRequest('Calidad', 'Captura')} type="button">
                          {exceptionActionLabel()}
                        </button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
                <div className="ets-metric-strip">
                  {[
                    ['Pendientes', qualityMetrics.pending],
                    ['En revision', qualityMetrics.review],
                    ['Aprobados', qualityMetrics.approved],
                    ['Liberables', qualityMetrics.releasable],
                    ['Autenticados', qualityMetrics.authenticated]
                  ].map(([label, value]) => (
                    <span className="ets-metric-badge" key={label}><strong>{safeNumber(value)}</strong>{label}</span>
                  ))}
                </div>
                <WorkOrderFlowGroups
                  emptyMessage="No hay certificados dentro del flujo de Calidad para este ETS."
                  equipmentById={equipmentById}
                  getGroupState={(items) => items.every((item) => ['quality_approved', 'approved'].includes(item.status)) ? { label: 'APROBADA', tone: 'approved' } : { label: 'EN REVISIÓN', tone: 'quality_review' }}
                  items={filteredSelectedCertificates.filter((item) => ['ready_for_quality', 'quality_review', 'match_validated', 'quality_approved', 'approved'].includes(item.status))}
                  orders={[selectedOrder]}
                  renderItem={(certificate) => {
                    const item = equipmentById.get(certificate.equipment_id);
                    const sheet = certificate.field_sheet_id ? fieldSheets.find((candidate) => candidate.id === certificate.field_sheet_id) : null;
                    const captureFile = latestCaptureFileByCertificateId.get(certificate.id);
                    const readiness = authoritativeCaptureReadinessByCertificateId.get(certificate.id) || getCaptureMasterReadiness({ certificate, equipment: item, captureFile });
                    return <button className="flow-certificate-card flow-certificate-card--button" key={certificate.id} onClick={() => setSelectedQualityCertificate(certificate)} type="button"><div className="flow-certificate-card__title"><div><span>Certificado</span><strong>{certificate.expected_folio || certificate.folio}</strong></div><mark className={`quotation-status status-${certificate.status}`}>{certificateStatusLabels[certificate.status] ?? certificate.status}</mark></div><dl><div><dt>Equipo</dt><dd>{item?.name || '-'}</dd></div><div><dt>Hoja</dt><dd>{sheet ? fieldSheetStatusLabels[sheet.status] ?? sheet.status : '-'}</dd></div><div><dt>Master</dt><dd>{readiness.identified ? 'Identificado' : 'Pendiente'}</dd></div><div><dt>Alertas</dt><dd>{readiness.warnings.length}</dd></div><div><dt>Diferencias</dt><dd>{readiness.mismatches.length}</dd></div></dl><span className="flow-primary-hint">Revisar Master en Calidad</span></button>;
                  }}
                />
              </section>
            ) : null}

            {activeTab === 'certificates' ? (
              <section className="quotation-section">
                <div className="quotation-section__title quotation-section__title--stacked">
                  <div>
                    <p>Certificados</p>
                    <h3>Disponibilidad y liberación al cliente</h3>
                  </div>
                  <div className="ets-stage-note" role="status">
                    Pago: {certificateReleaseReadiness?.payment_status === 'paid' ? 'confirmado' : certificateReleaseReadiness?.payment_status === 'not_required' ? 'no requerido' : 'pendiente'} · {certificateReleaseReadiness?.reason || 'Validando reglas de liberación.'}
                  </div>
                </div>
                <WorkOrderFlowGroups
                  emptyMessage="No hay certificados autenticados en este ETS."
                  equipmentById={equipmentById}
                  getGroupState={(items) => getCertificateReleasePresentation({ released: items.every((item) => ['released_to_client', 'released'].includes(item.status)), releaseReadiness: certificateReleaseReadiness })}
                  items={filteredSelectedCertificates.filter((item) => item.authenticated_pdf_path && ['authenticated', 'released_to_client', 'released'].includes(item.status))}
                  orders={[selectedOrder]}
                  renderItem={(certificate) => {
                    const item = equipmentById.get(certificate.equipment_id);
                    const released = ['released_to_client', 'released'].includes(certificate.status);
                    const releasePresentation = getCertificateReleasePresentation({ released, releaseReadiness: certificateReleaseReadiness });
                    return <article className="flow-certificate-card" key={certificate.id}><button className="flow-certificate-card__primary" onClick={() => openAuthenticatedCertificatePdf(certificate)} type="button"><div className="flow-certificate-card__title"><div><span>Certificado autenticado</span><strong>{certificate.expected_folio || certificate.folio}</strong></div><mark className={`quotation-status status-${certificate.status}`}>{getCertificateStatusLabel(certificate)}</mark></div><dl><div><dt>Equipo</dt><dd>{item?.name || '-'}</dd></div><div><dt>Serie</dt><dd>{item?.serial_number || '-'}</dd></div><div><dt>Código</dt><dd>{certificate.authentication_code || '-'}</dd></div><div><dt>Fecha</dt><dd>{certificate.authenticated_pdf_generated_at ? new Date(certificate.authenticated_pdf_generated_at).toLocaleString('es-MX') : '-'}</dd></div></dl><span className="flow-primary-hint">Ver PDF autenticado</span></button><div className={releasePresentation.status === 'blocked' ? 'flow-release-blocked' : 'flow-release-ready'}>{releasePresentation.message}</div><div className="toolbar-actions"><button className="table-button" onClick={() => handleDownloadAuthenticatedCertificatePdf(certificate)} type="button">Descargar</button><button className="table-button" onClick={() => showCertificateAuthentication(certificate)} type="button">Ver autenticación</button>{released ? <span className="flow-action-complete">Liberado</span> : canUseReleaseActions ? <button className="table-button table-button--primary" disabled={isSaving || !releasePresentation.canRelease} onClick={() => handleCertificateWorkflow(certificate, 'release-to-client', `Certificado ${certificate.folio} liberado al cliente`)} title={releasePresentation.canRelease ? 'Liberar al cliente' : releasePresentation.message} type="button">Liberar</button> : null}</div></article>;
                  }}
                />
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
                {shouldShowSignatureLauncher && renderSignatureLauncher()}
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

            {activeTab === 'notes' ? (
              <>
                {orderForm.notes ? (
                  <section className="quotation-section">
                    <div className="quotation-section__title">
                      <p>Dato histórico conservado</p>
                      <h3>Notas previas del ETS</h3>
                    </div>
                    <p>{orderForm.notes}</p>
                  </section>
                ) : null}
                <section className="quotation-section">
                  <div className="quotation-section__title">
                    <p>Comunicación interna</p>
                    <h3>Actividad del expediente</h3>
                  </div>
                  <ActivityPanel
                    entityId={selectedOrder.id}
                    entityType="service_order"
                  />
                </section>
              </>
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

            {activeTab === 'billing' || isBillingTabMounted ? (
              <div
                className="ets-billing-tab-slot"
                hidden={activeTab !== 'billing'}
              >
                <EtsBillingTab
                  onPaymentRegistered={async () => {
                    const readiness = await getCertificateReleaseReadiness(selectedOrder.id);
                    setCertificateReleaseReadiness(readiness);
                  }}
                  serviceOrderId={selectedOrder.id}
                  user={user}
                />
              </div>
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
                  <section className="quotation-section ets-equipment-condition-section">
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
                  <section className="quotation-section">
                    <div className="quotation-section__title">
                      <p>Comunicación interna</p>
                      <h3>Actividad del equipo</h3>
                    </div>
                    <ActivityPanel
                      entityId={selectedEquipmentDetail.id}
                      entityType="equipment"
                    />
                  </section>
                  <div className="quotation-detail-save ets-equipment-detail-actions">
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
                      {canUseAdminActions ? (
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
          <section 
            className="client-modal ets-equipment-form-modal"
            aria-modal="true"
            role="dialog"
          >
            <div className="section-heading">
              <div>
                <p>Equipos</p>
                <h2>{editingEquipmentId ? 'Editar equipo' : 'Agregar equipo'}</h2>
              </div>
            </div>
            {error ? <div className="form-error dashboard-error">{error}</div> : null}
            <form className="client-form client-form--modal" onSubmit={handleEquipmentSubmit}>
              <label>
                Orden de Trabajo
                <select
                  disabled={relatedWorkOrders.length <= 1}
                  onChange={(event) => updateEquipmentForm('workOrderId', event.target.value)}
                  required={relatedWorkOrders.some((workOrder) => !isLegacyWorkOrder(workOrder))}
                  value={equipmentForm.workOrderId}
                >
                  {relatedWorkOrders.some((workOrder) => isLegacyWorkOrder(workOrder)) ? (
                    <option value="">OT {selectedOrder.work_order_number ?? '-'} legacy</option>
                  ) : null}
                  {workOrderCapacitySummary.groups.map((workOrder) => {
                    const isCurrentWorkOrder = editingEquipmentId && String(equipmentForm.workOrderId) === String(workOrder.id);
                    return (
                      <option
                        disabled={!isCurrentWorkOrder && workOrder.available <= 0}
                        key={workOrder.id}
                        value={workOrder.id}
                      >
                        OT-{workOrder.work_order_number} · {workOrder.registered}/{workOrder.limit}
                      </option>
                    );
                  })}
                </select>
              </label>
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
            <section className="client-modal field-sheet-create-modal" aria-modal="true" role="dialog">
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

              <div className="field-sheet-create-form">
                <section className="field-sheet-create-section">
                  <div className="field-sheet-create-section__heading">
                    <div><span>1</span><h3>Cliente del certificado</h3></div>
                    <small>Define qué datos aparecerán en la hoja y el certificado.</small>
                  </div>

                  <div className="field-sheet-client-choice-grid">
                    <button
                      className={fieldSheetCreateForm.certificateClientMode === 'billing' ? 'field-sheet-client-choice is-active' : 'field-sheet-client-choice'}
                      onClick={() => updateFieldSheetCreateForm('certificateClientMode', 'billing')}
                      type="button"
                    >
                      <span className="field-sheet-choice-dot" />
                      <span><strong>Mismo cliente facturado</strong><small>Usar razón social y domicilio del cliente actual.</small></span>
                    </button>
                    <button
                      className={fieldSheetCreateForm.certificateClientMode === 'different' ? 'field-sheet-client-choice is-active' : 'field-sheet-client-choice'}
                      onClick={openCertificateClientModal}
                      type="button"
                    >
                      <span className="field-sheet-choice-dot" />
                      <span><strong>Cliente diferente</strong><small>Elegir o capturar datos específicos para certificados.</small></span>
                    </button>
                  </div>

                  <div className="field-sheet-client-summary">
                    <div><span>Empresa</span><strong>{fieldSheetCreateForm.certificateClientMode === 'different' ? fieldSheetCreateForm.certificateClientCompany || 'Pendiente de capturar' : getClientDisplayName(clientsById.get(selectedOrder.client_id))}</strong></div>
                    <div><span>Domicilio</span><strong>{fieldSheetCreateForm.certificateClientMode === 'different' ? fieldSheetCreateForm.certificateClientAddress || 'Pendiente de capturar' : getClientAddress(clientsById.get(selectedOrder.client_id)) || 'Sin domicilio capturado'}</strong></div>
                    {fieldSheetCreateForm.certificateClientMode === 'different' ? <button className="icon-text-button" onClick={openCertificateClientModal} type="button">Editar datos</button> : null}
                  </div>

                  {fieldSheetCreateForm.certificateClientMode === 'billing' ? (
                    <label className="field-sheet-create-field">
                      Atención
                      <input onChange={(event) => updateFieldSheetCreateForm('attention', event.target.value)} placeholder="Nombre de la persona que recibirá la atención" type="text" value={fieldSheetCreateForm.attention} />
                    </label>
                  ) : (
                    <label className="field-sheet-inline-check">
                      <input checked={fieldSheetCreateForm.applyCertificateClientToOrder} onChange={(event) => updateFieldSheetCreateForm('applyCertificateClientToOrder', event.target.checked)} type="checkbox" />
                      <span><strong>Usar estos datos en las demás hojas de esta orden</strong><small>No cambia el cliente de facturación.</small></span>
                    </label>
                  )}
                </section>

                <section className="field-sheet-create-section">
                  <div className="field-sheet-create-section__heading">
                    <div><span>2</span><h3>Plantilla</h3></div>
                    <small>La sugerencia puede modificarse antes de crear la hoja.</small>
                  </div>

                {fieldSheetCreateForm.templateSuggestion ? (
                  <div className="form-notice">Sugerencia automática por “{fieldSheetCreateForm.templateSuggestion}”. Puedes cambiarla antes de crear.</div>
                ) : (
                  <div className="form-error">No se pudo determinar automáticamente la plantilla. Selecciona una hoja de campo.</div>
                )}

                <label className="field-sheet-create-field">
                  Tipo de hoja de campo
                  <select
                    onChange={(event) => updateFieldSheetCreateForm('templateKey', event.target.value)}
                    value={fieldSheetCreateForm.templateKey}
                  >
                    <option value="">Selecciona una plantilla…</option>
                    {officialFieldSheetTemplateOptions.map((template) => (
                      <option key={template.value} value={template.value}>{template.label}</option>
                    ))}
                  </select>
                </label>

                </section>

                <div className="field-sheet-create-actions">
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
                    disabled={isSaving || !fieldSheetCreateForm.templateKey || (fieldSheetCreateForm.certificateClientMode === 'different' && (!fieldSheetCreateForm.certificateClientCompany || !fieldSheetCreateForm.certificateClientAddress))}
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

        {isCertificateClientModalOpen && selectedOrder ? (
          <div className="modal-backdrop modal-backdrop--nested" role="presentation">
            <section className="client-modal certificate-client-modal" aria-modal="true" aria-labelledby="certificate-client-title" role="dialog">
              <div className="section-heading">
                <div><p>Cliente del certificado</p><h2 id="certificate-client-title">Datos diferentes al facturado</h2></div>
                <button className="icon-text-button" disabled={isSaving} onClick={closeCertificateClientModal} type="button">Cerrar</button>
              </div>
              <p className="certificate-client-help">Estos datos se usarán en la hoja de campo. Puedes guardarlos en el cliente facturado para reutilizarlos después.</p>
              {error ? <div className="form-error dashboard-error">{error}</div> : null}
              {(clientsById.get(selectedOrder.client_id)?.certificate_profiles ?? []).filter((profile) => profile.is_active !== false).length ? (
                <label className="field-sheet-create-field">
                  Datos guardados
                  <select onChange={(event) => selectCertificateProfile(event.target.value)} value={certificateClientDraft.profileId}>
                    <option value="">Capturar datos nuevos…</option>
                    {(clientsById.get(selectedOrder.client_id)?.certificate_profiles ?? []).filter((profile) => profile.is_active !== false).map((profile) => <option key={profile.id} value={profile.id}>{profile.label}{profile.is_default ? ' · Predeterminado' : ''}</option>)}
                  </select>
                </label>
              ) : null}
              <div className="certificate-client-form">
                <label>Empresa<input autoFocus onChange={(event) => setCertificateClientDraft((current) => ({ ...current, company: event.target.value, profileId: '' }))} type="text" value={certificateClientDraft.company} /></label>
                <label>Atención<input onChange={(event) => setCertificateClientDraft((current) => ({ ...current, attention: event.target.value, profileId: '' }))} placeholder="Nombre de la persona" type="text" value={certificateClientDraft.attention} /></label>
                <label className="form-field--wide">Domicilio<textarea onChange={(event) => setCertificateClientDraft((current) => ({ ...current, address: event.target.value, profileId: '' }))} rows={3} value={certificateClientDraft.address} /></label>
              </div>
              <label className="field-sheet-inline-check">
                <input checked={certificateClientDraft.saveToClient} onChange={(event) => setCertificateClientDraft((current) => ({ ...current, saveToClient: event.target.checked }))} type="checkbox" />
                <span><strong>Guardar en “Datos para certificados” del cliente</strong><small>Quedará disponible para futuras órdenes.</small></span>
              </label>
              {certificateClientDraft.saveToClient ? (
                <div className="certificate-client-save-options">
                  <label>Nombre para identificarlo<input onChange={(event) => setCertificateClientDraft((current) => ({ ...current, label: event.target.value }))} placeholder="Ej. Planta Guadalajara" type="text" value={certificateClientDraft.label} /></label>
                  <label className="field-sheet-inline-check"><input checked={certificateClientDraft.isDefault} onChange={(event) => setCertificateClientDraft((current) => ({ ...current, isDefault: event.target.checked }))} type="checkbox" /><span><strong>Usar como predeterminado</strong></span></label>
                </div>
              ) : null}
              <div className="field-sheet-create-actions">
                <button className="icon-text-button" disabled={isSaving} onClick={closeCertificateClientModal} type="button">Cancelar</button>
                <button className="primary-button" disabled={isSaving || !certificateClientDraft.company.trim() || !certificateClientDraft.address.trim()} onClick={applyCertificateClientDraft} type="button">{isSaving ? 'Guardando...' : 'Usar estos datos'}</button>
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
                ['activity', 'Actividad'],
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
                    ...(fieldSheetForm.captureValues || {}),
                    work_order_number: selectedFieldSheet?.work_order_number || selectedOrder?.work_order_number || '',
                    reserved_certificate_folio:
                      selectedFieldSheet?.reserved_certificate_folio ||
                      fieldSheetForm.reservedCertificateFolio ||
                      activeCertificatesByEquipmentId.get(selectedEquipmentForSheet?.id)?.expected_folio ||
                      activeCertificatesByEquipmentId.get(selectedEquipmentForSheet?.id)?.folio ||
                      '',

                    attention: fieldSheetForm.attention || fieldSheetForm.certificateClientAttention || '',
                    company:
                      fieldSheetForm.company ||
                      fieldSheetForm.certificateClientCompany ||
                      clientsById.get(selectedOrder?.client_id)?.commercial_name ||
                      clientsById.get(selectedOrder?.client_id)?.legal_name ||
                      '',
                    address: fieldSheetForm.address || fieldSheetForm.certificateClientAddress || '',
                    instrument: fieldSheetForm.captureValues?.instrument ?? selectedEquipmentForSheet?.name ?? '',
                    scope: fieldSheetForm.captureValues?.scope ?? selectedEquipmentForSheet?.range_or_capacity ?? '',
                    minimum_division: fieldSheetForm.minimumDivision || '',
                    brand: fieldSheetForm.captureValues?.brand ?? selectedEquipmentForSheet?.brand ?? '',
                    serial_number: fieldSheetForm.captureValues?.serial_number ?? selectedEquipmentForSheet?.serial_number ?? '',
                    model: fieldSheetForm.captureValues?.model ?? selectedEquipmentForSheet?.model ?? '',
                    internal_id: fieldSheetForm.captureValues?.internal_id ?? selectedEquipmentForSheet?.internal_id ?? '',
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
                    method: fieldSheetForm.method || '',
                    initial_condition: fieldSheetForm.initialCondition || '',
                    final_condition: fieldSheetForm.finalCondition || '',
                    pattern_used: fieldSheetForm.patternUsed || '',
                    observations: fieldSheetForm.observations || '',
                    evidence_notes: fieldSheetForm.evidenceNotes || '',
                    calibrated_by: fieldSheetForm.calibratedBy || '',
                    reviewed_by: fieldSheetForm.reviewedBy || '',
                    report_made_by: fieldSheetForm.reportMadeBy || '',
                    purchase_order_or_quotation: fieldSheetForm.purchaseOrderOrQuotation || '',
                  }}
                  institution={selectedFieldSheet?.institutional_snapshot || null}
                  signatures={fieldSheetForm.signatures || []}
                  users={users}
                  validationErrors={fieldSheetValidationErrors}
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
                      evidence_notes: 'evidenceNotes',
                      initial_condition: 'initialCondition',
                      final_condition: 'finalCondition',
                      pattern_used: 'patternUsed',
                      method: 'method',
                      calibrated_by: 'calibratedBy',
                      reviewed_by: 'reviewedBy',
                      report_made_by: 'reportMadeBy',
                      purchase_order_or_quotation: 'purchaseOrderOrQuotation',
                    };

                    if (map[key]) {
                      updateFieldSheetForm(map[key], value);
                    } else {
                      setFieldSheetForm((current) => ({
                        ...current,
                        captureValues: { ...(current.captureValues || {}), [key]: value },
                      }));
                    }
                    setFieldSheetValidationErrors((current) => {
                      const next = { ...current };
                      delete next[key];
                      if (key === 'observations' || key === 'evidence_notes') {
                        delete next.observations;
                        delete next.evidence_notes;
                      }
                      return next;
                    });
                  }}
                  onResultChange={(sectionKey, rowNumber, columnKey, value) => {
                    updateFieldSheetResult(sectionKey, rowNumber, columnKey, value);
                    setFieldSheetValidationErrors((current) => {
                      const next = { ...current };
                      delete next.results_rows;
                      return next;
                    });
                  }}
                  onSignatureChange={(index, updates) => {
                    setFieldSheetForm((current) => ({
                      ...current,
                      signatures: (current.signatures || []).map((signature, signatureIndex) =>
                        signatureIndex === index ? { ...signature, ...updates } : signature
                      ),
                    }));
                  }}
                />
                <div className="quotation-detail-save field-sheet-action-panel">
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

                {canUseAdminActions ? (
                  <div className="quotation-detail-save field-sheet-admin-actions">
                    <span>Acciones administrativas de hoja de campo.</span>
                    <button className="table-button table-button--danger" disabled={isSaving} onClick={handleDeleteFieldSheet} type="button">
                      Eliminar hoja de campo
                    </button>
                  </div>
                ) : null}
              </section>
            ) : null}

            {fieldSheetTab === 'activity' ? (
              <section className="quotation-section">
                <div className="quotation-section__title">
                  <p>Comunicación interna</p>
                  <h3>Actividad de la Hoja de Campo</h3>
                </div>
                <ActivityPanel
                  entityId={selectedFieldSheet.id}
                  entityType="field_sheet"
                />
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

      {isWorkOrdersModalOpen && selectedOrder && (
        <div className="modal-backdrop">
          <div className="modal-card ets-work-orders-modal">
            <div className="modal-header">
              <div className="modal-header-content">
                <p className="eyebrow">Expediente tecnico</p>
                <h2>Órdenes de trabajo</h2>
                <p className="muted">
                  {selectedOrder.folio} · {relatedWorkOrders.length} orden(es)
                </p>
              </div>

              <button
                type="button"
                className="ghost-button"
                onClick={() => {
                  setIsWorkOrdersModalOpen(false);
                  setWorkOrderSearch('');
                }}
              >
                Cerrar
              </button>
            </div>

            <div className="form-field">
              <label>Buscar orden</label>
              <input
                type="search"
                value={workOrderSearch}
                onChange={(event) => setWorkOrderSearch(event.target.value)}
                placeholder="Buscar por folio, número de OT o estado..."
              />
            </div>

            <div className="ets-work-orders-list">
              {relatedWorkOrders
                .filter((workOrder) => {
                  const query = workOrderSearch.trim().toLowerCase();
                  if (!query) return true;

                  return [
                    workOrder.work_order_number,
                    workOrder.sequence,
                    workOrder.status,
                  ]
                    .filter(Boolean)
                    .some((value) => String(value).toLowerCase().includes(query));
                })
                .map((workOrder) => {
                  const equipmentCount = getWorkOrderEquipmentCount(workOrder);
                  const capacityLimit = safeNumber(workOrder.equipment_limit || 10);

                  return (
                    <article
                      key={workOrder.id}
                      className="ets-work-order-row"
                    >
                      <div>
                        <strong>OT-{workOrder.work_order_number}</strong>
                        <span>
                          Secuencia {workOrder.sequence || 1} · {equipmentCount}/{capacityLimit} equipo(s)
                        </span>
                      </div>
                      <span className="status-pill">
                        {workOrder.status || 'Pendiente'}
                      </span>
                      <div className="ets-work-order-row__actions">
                        {[
                          ['equipment', 'Equipos'],
                          ['field-sheet', 'Hojas'],
                          ['certificates', 'Certificados'],
                        ].map(([tab, label]) => (
                          <button
                            className="table-button"
                            key={tab}
                            onClick={() => {
                              setIsWorkOrdersModalOpen(false);
                              setWorkOrderSearch('');
                              openTabFromSummary(tab, { workOrder });
                            }}
                            type="button"
                          >
                            {label}
                          </button>
                        ))}
                        {canPermanentlyDeleteWorkOrder && !isLegacyWorkOrder(workOrder) ? (
                          <button
                            className="table-button is-danger"
                            disabled={isSaving}
                            onClick={() => handleDeleteWorkOrder(workOrder)}
                            type="button"
                          >
                            Eliminar orden de trabajo
                          </button>
                        ) : null}
                      </div>
                    </article>
                  );
                })}

              {!relatedWorkOrders.length && (
                <div className="empty-state">
                  No hay órdenes de trabajo registradas para este expediente.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {selectedQualityCertificate ? (() => {
        const certificate = certificates.find((item) => item.id === selectedQualityCertificate.id) || selectedQualityCertificate;
        const item = equipment.find((equipmentItem) => equipmentItem.id === certificate.equipment_id);
        const sheet = certificate.field_sheet_id ? fieldSheets.find((candidate) => candidate.id === certificate.field_sheet_id) : null;
        const captureFile = latestCaptureFileByCertificateId.get(certificate.id);
        const masterReadiness = authoritativeCaptureReadinessByCertificateId.get(certificate.id) || getCaptureMasterReadiness({ certificate, equipment: item, captureFile });
        const canApprove = ['ready_for_quality', 'quality_review'].includes(certificate.status) && masterReadiness.ready;
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
                <article><span>Master XLSX</span><strong>{captureFile?.filename || 'Pendiente'}</strong></article>
                <article><span>Advertencias</span><strong>{masterReadiness.warnings.length}</strong></article>
                <article><span>Diferencias bloqueantes</span><strong>{masterReadiness.mismatches.length}</strong></article>
                <article><span>Estado</span><strong>{certificateStatusLabels[certificate.status] ?? certificate.status}</strong></article>
                <article><span>Autenticacion</span><strong>{certificate.authentication_code || '-'}</strong></article>
              </div>
              <div className="quality-action-ribbon">
                <button className="table-button" disabled={!captureFile} onClick={() => handleDownloadCaptureMaster(certificate)} type="button">1. Descargar Master XLSX</button>
                <button className="table-button" disabled={!canApprove || isSaving} onClick={() => handleCertificateWorkflow(certificate, 'quality-approve', `Master de ${certificate.folio} aprobado`)} type="button">2. Aprobar Master</button>
                <button className="table-button" disabled={!['ready_for_quality', 'quality_review', 'match_validated', 'quality_approved'].includes(certificate.status) || isSaving} onClick={() => handleCertificateWorkflow(certificate, 'request-correction', `Certificado ${certificate.folio} regresado a Captura`)} type="button">3. Rechazar / regresar a Captura</button>
              </div>
              <div className="quotation-history-list">
                <article><strong>Creado</strong><span>{certificate.created_at ? new Date(certificate.created_at).toLocaleString('es-MX') : '-'}</span></article>
                <article><strong>Master recibido</strong><span>{captureFile?.created_at ? new Date(captureFile.created_at).toLocaleString('es-MX') : '-'}</span></article>
                <article><strong>Enviado a calidad</strong><span>{certificate.sent_to_quality_at ? new Date(certificate.sent_to_quality_at).toLocaleString('es-MX') : '-'}</span></article>
                <article><strong>Revision calidad</strong><span>{certificate.quality_reviewed_at ? new Date(certificate.quality_reviewed_at).toLocaleString('es-MX') : '-'}</span></article>
                <article><strong>Autenticado</strong><span>{certificate.authenticated_pdf_generated_at ? new Date(certificate.authenticated_pdf_generated_at).toLocaleString('es-MX') : '-'}</span></article>
              </div>
              <pre className="match-details-panel">{JSON.stringify(captureFile?.validation || {}, null, 2)}</pre>
            </section>
          </div>
        );
      })() : null}

      {returnToTechnicianRequest ? (
        (() => {
          return (
        <div className="modal-backdrop" role="presentation">
          <section aria-modal="true" className="client-modal confirm-dialog" role="dialog">
            <div className="section-heading confirm-dialog__header">
              <div>
                <p>Corrección requerida</p>
                <h2>Motivo obligatorio</h2>
              </div>
            </div>
            <div className="confirm-dialog__body">
              <p>Describe los errores encontrados en el Master XLSX. El certificado regresará a Captura, la hoja conservará su estado y quedará evidencia en auditoría.</p>
              <textarea
                autoFocus
                className="form-textarea"
                onChange={(event) => setReturnToTechnicianReason(event.target.value)}
                placeholder="Marca los errores y la corrección requerida en el Master XLSX"
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
                {isSaving ? 'Procesando...' : 'Regresar a Captura'}
              </button>
            </div>
          </section>
        </div>
          );
        })()
      ) : null}

      {exceptionRequest ? (
        <div className="modal-backdrop" role="presentation">
          <section aria-modal="true" className="client-modal confirm-dialog service-order-exception-dialog" role="dialog">
            <div className="section-heading confirm-dialog__header">
              <div>
                <p>Excepcion operativa</p>
                <h2>{exceptionRequest.sourceStage} - {exceptionRequest.targetStage}</h2>
              </div>
            </div>
            <div className="confirm-dialog__body">
              <p>Registra el motivo. El backend conserva etapa origen, etapa destino, usuario, fecha y comentario en auditoria.</p>
              <textarea
                autoFocus
                className="form-textarea"
                onChange={(event) => setExceptionReason(event.target.value)}
                placeholder="Motivo de la excepcion"
                rows={4}
                value={exceptionReason}
              />
            </div>
            <div className="confirm-dialog__actions">
              <button
                className="confirm-dialog__cancel"
                disabled={isSaving}
                onClick={() => {
                  setExceptionRequest(null);
                  setExceptionReason('');
                }}
                type="button"
              >
                Cancelar
              </button>
              <button
                className="confirm-dialog__confirm"
                disabled={isSaving}
                onClick={submitExceptionRequest}
                type="button"
              >
                {isSaving ? 'Registrando...' : 'Registrar excepcion'}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {isEquipmentLimitNoticeOpen ? (
      <div className="modal-backdrop" role="presentation">
        <section
          aria-modal="true"
          className="client-modal confirm-dialog"
          role="dialog"
        >
          <div className="section-heading confirm-dialog__header">
            <div>
              <p>Equipos del ETS</p>
              <h2>Límite alcanzado</h2>
            </div>
          </div>

          <div className="confirm-dialog__body">
            <p>
              Ya se registraron todos los equipos esperados para este ETS.
              Para agregar otro equipo se requiere una excepción.
            </p>
          </div>

          <div className="confirm-dialog__actions">
            <button
              className="confirm-dialog__cancel"
              onClick={() => setIsEquipmentLimitNoticeOpen(false)}
              type="button"
            >
              Cerrar
            </button>

            <button
              className="confirm-dialog__confirm"
              onClick={() => {
                setIsEquipmentLimitNoticeOpen(false);
                openExceptionRequest('Equipos', 'Equipo adicional');
              }}
              type="button"
            >
              {exceptionActionLabel()}
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
