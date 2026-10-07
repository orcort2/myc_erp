import type {
  LabEquipment,
  TechnicalReportStatus,
  TechnicalReportType,
} from '@/src/types/lab-work-order';

/**
 * TechnicalReport (Servicio General) en MYC Mobile. SG-3 sólo crea el reporte
 * Installation y muestra su estado; el formulario, evidencias, firmas y PDF
 * pertenecen a fases posteriores.
 */

export type TechnicalReportTypeOption = {
  value: TechnicalReportType;
  title: string;
  description: string;
  enabled: boolean;
};

/** Un reporte sólo se captura/edita antes de quedar listo para firmas. */
export const EDITABLE_REPORT_STATUSES: ReadonlySet<TechnicalReportStatus> = new Set<TechnicalReportStatus>(['draft', 'in_progress']);

const COMING_SOON = 'Próximamente';

export const TECHNICAL_REPORT_TYPE_OPTIONS: TechnicalReportTypeOption[] = [
  { value: 'installation', title: 'Instalación', description: 'Instalación del equipo o producto en sitio.', enabled: true },
  { value: 'verification', title: 'Verificación', description: COMING_SOON, enabled: false },
  { value: 'repair', title: 'Reparación', description: COMING_SOON, enabled: false },
  { value: 'maintenance', title: 'Mantenimiento', description: COMING_SOON, enabled: false },
  { value: 'sale', title: 'Venta', description: COMING_SOON, enabled: false },
];

export function technicalReportTypeLabel(type: TechnicalReportType | null | undefined): string {
  return TECHNICAL_REPORT_TYPE_OPTIONS.find((option) => option.value === type)?.title ?? 'Reporte técnico';
}

export function isReportTypeEnabled(type: TechnicalReportType): boolean {
  return TECHNICAL_REPORT_TYPE_OPTIONS.some((option) => option.value === type && option.enabled);
}

export function technicalReportPdfPath(workOrderId: number, equipmentId: number): string {
  return `${technicalReportPath(workOrderId, equipmentId)}/pdf`;
}

export function technicalReportPath(workOrderId: number, equipmentId: number): string {
  return `/mobile/v1/technician/lab-work-orders/${workOrderId}/equipment/${equipmentId}/technical-report`;
}

/** Cuerpo exacto del POST. Los tipos no habilitados nunca llegan a la red. */
export function buildCreateTechnicalReportRequest(
  workOrderId: number,
  equipmentId: number,
  type: TechnicalReportType,
): { path: string; init: { method: 'POST'; body: string } } | null {
  if (!isReportTypeEnabled(type)) return null;
  return {
    path: technicalReportPath(workOrderId, equipmentId),
    init: { method: 'POST', body: JSON.stringify({ report_type: type }) },
  };
}

export type TechnicalReportBadgeTone = 'neutral' | 'info' | 'warning' | 'success' | 'danger';

const STATUS_PRESENTATION: Record<TechnicalReportStatus, { label: string; tone: TechnicalReportBadgeTone }> = {
  draft: { label: 'BORRADOR', tone: 'info' },
  in_progress: { label: 'EN CAPTURA', tone: 'info' },
  // Internamente sigue siendo ready_for_signatures; significa captura finalizada / lista para entrega.
  ready_for_signatures: { label: 'LISTO PARA ENTREGA', tone: 'warning' },
  completed: { label: 'COMPLETADO', tone: 'success' },
  cancelled: { label: 'CANCELADO', tone: 'danger' },
};

type ReportProjection = Pick<
  LabEquipment,
  'technical_report_id' | 'technical_report_type' | 'technical_report_folio' | 'technical_report_status'
>;

export type TechnicalReportCardState = {
  hasReport: boolean;
  badgeLabel: string;
  badgeTone: TechnicalReportBadgeTone;
  folio: string | null;
  typeLabel: string | null;
  actionLabel: 'Seleccionar reporte' | 'Abrir reporte';
};

/** Estado visual de la tarjeta de equipo de Servicio General. */
export function describeTechnicalReportCard(equipment: ReportProjection): TechnicalReportCardState {
  if (equipment.technical_report_id == null || !equipment.technical_report_status) {
    return {
      hasReport: false,
      badgeLabel: 'SIN REPORTE',
      badgeTone: 'neutral',
      folio: null,
      typeLabel: null,
      actionLabel: 'Seleccionar reporte',
    };
  }
  const presentation = STATUS_PRESENTATION[equipment.technical_report_status];
  return {
    hasReport: true,
    badgeLabel: presentation.label,
    badgeTone: presentation.tone,
    folio: equipment.technical_report_folio,
    typeLabel: technicalReportTypeLabel(equipment.technical_report_type),
    actionLabel: 'Abrir reporte',
  };
}

/** Crear exige technical_reports.capture; abrir uno existente basta con lectura. */
export function technicalReportAction(
  equipment: ReportProjection,
  permissions: { canRead: boolean; canCapture: boolean },
): 'select' | 'open' | null {
  if (equipment.technical_report_id != null) return permissions.canRead || permissions.canCapture ? 'open' : null;
  return permissions.canCapture ? 'select' : null;
}

export type GeneralServiceClosureState = {
  /** Sólo el backend decide: la OT debe estar en `ready_to_close`. */
  canClose: boolean;
  message: string | null;
};

/** Qué mostrar en el paso técnico de una OT de Servicio General respecto al cierre.
 * `canClose` no se deduce de reportes/entregas: lo dicta el estado de la OT que
 * calcula el backend (autoridad técnica category-aware). Los reportes/entregas
 * sólo eligen el mensaje de lo que falta. */
export function describeGeneralServiceClosure(input: {
  orderStatus: string;
  equipment: Pick<LabEquipment, 'id' | 'technical_report_status'>[];
  deliveredEquipmentIds: ReadonlySet<number | null>;
}): GeneralServiceClosureState {
  if (input.orderStatus === 'ready_to_close') {
    return { canClose: true, message: 'La entrega y documentación técnica están completas.' };
  }
  const reportCompletedWithoutDelivery = input.equipment.some(
    (item) => item.technical_report_status === 'completed' && !input.deliveredEquipmentIds.has(item.id),
  );
  if (reportCompletedWithoutDelivery) {
    return { canClose: false, message: 'El reporte técnico está completo, pero falta registrar la entrega.' };
  }
  const deliveredWithoutFinalReport = input.equipment.some(
    (item) => item.technical_report_status === 'ready_for_signatures' && input.deliveredEquipmentIds.has(item.id),
  );
  if (deliveredWithoutFinalReport) {
    return { canClose: false, message: 'La entrega está registrada. Falta generar el reporte técnico final.' };
  }
  return { canClose: false, message: null };
}
