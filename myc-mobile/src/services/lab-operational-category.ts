import type { LabOperationalCategory } from '@/src/types/lab-work-order';
import type { CreationGroupMode } from '@/src/services/lab-erp-calibration';

/**
 * Categoría técnica de la OT LAB (SG-3). Calibración conserva todo el flujo
 * metrológico (FieldSheet, modalidad, folio MYCA/MYCT); Servicio General usa
 * TechnicalReports y NO tiene configuración metrológica. La categoría se elige
 * sólo al crear y es autoridad de backend.
 */

export const DEFAULT_OPERATIONAL_CATEGORY: LabOperationalCategory = 'calibration';

export type OperationalCategoryOption = {
  value: LabOperationalCategory;
  title: string;
  description: string;
};

export const OPERATIONAL_CATEGORY_OPTIONS: OperationalCategoryOption[] = [
  {
    value: 'calibration',
    title: 'Calibración',
    description: 'Hoja de campo, modalidad y folio de certificado.',
  },
  {
    value: 'general_service',
    title: 'Servicio general',
    description: 'Reportes técnicos de instalación, verificación, reparación, mantenimiento o venta.',
  },
];

export function isGeneralService(workOrder: { operational_category?: LabOperationalCategory | null } | null | undefined): boolean {
  return workOrder?.operational_category === 'general_service';
}

/** El selector sólo existe al crear una OT/grupo directo de staff interno:
 * la solicitud externa de grupo conserva su payload histórico (calibración). */
export function canChooseOperationalCategory(
  groupMode: CreationGroupMode,
  isEditingExisting: boolean,
  isInternalActor: boolean,
  canCaptureTechnicalReports: boolean,
): boolean {
  return isInternalActor && canCaptureTechnicalReports && !isEditingExisting && groupMode !== 'request';
}

/** El puente ERP existente (`service_order_id`) es de calibración: con Servicio
 * General se oculta, para que nunca termine en 409 después de elegirlo. */
export function categoryAllowsErpLink(category: LabOperationalCategory): boolean {
  return category === 'calibration';
}

/**
 * Agrega `operational_category` únicamente en la creación interna (OT o grupo
 * directo). Con Servicio General además descarta cualquier `service_order_id`
 * residual: backend lo rechazaría con 409.
 */
type WithCategory<T> = T & { operational_category?: LabOperationalCategory };

export function withOperationalCategory<T extends Record<string, unknown>>(
  body: T,
  category: 'general_service',
  groupMode: CreationGroupMode,
  isEditingExisting: boolean,
): WithCategory<Omit<T, 'service_order_id'>>;
export function withOperationalCategory<T extends Record<string, unknown>>(
  body: T,
  category: LabOperationalCategory,
  groupMode: CreationGroupMode,
  isEditingExisting: boolean,
): WithCategory<T>;
export function withOperationalCategory<T extends Record<string, unknown>>(
  body: T,
  category: LabOperationalCategory,
  groupMode: CreationGroupMode,
  isEditingExisting: boolean,
): WithCategory<T> | WithCategory<Omit<T, 'service_order_id'>> {
  if (isEditingExisting || groupMode === 'request') return body;
  if (category === 'general_service') {
    const { service_order_id: _erpBridge, ...rest } = body;
    return { ...rest, operational_category: category };
  }
  return { ...body, operational_category: category };
}

export type EquipmentFormProfile = {
  /** Textos de pantalla que dependen de la categoría (una sola fuente). */
  technicalSectionTitle: string;
  addEquipmentTitle: string;
  addEquipmentDescription: string;
  editEquipmentDescription: string;
  sectionTitle: string;
  instrumentLabel: string;
  conditionLabel: string;
  /** Cliente documental, modalidad (acreditado/trazable/vinculado) y folio de certificado. */
  showsMetrologicalConfiguration: boolean;
  /** Servicio General: "Folio del reporte" de sólo lectura, colocado por el
   * sistema (technical_report_folio es la única autoridad). */
  showsReportFolio: boolean;
};

/** Una sola fuente de verdad por categoría para el formulario de equipo:
 * evita condicionales dispersos y deja el perfil de calibración intacto. */
export function equipmentFormProfile(category: LabOperationalCategory): EquipmentFormProfile {
  if (category === 'general_service') {
    return {
      technicalSectionTitle: 'Reporte técnico por equipo',
      addEquipmentTitle: 'Añadir equipo / producto',
      addEquipmentDescription: 'Datos del equipo o producto sobre el que se realizará el servicio.',
      editEquipmentDescription: 'Datos del equipo o producto.',
      sectionTitle: 'Datos del equipo / producto',
      instrumentLabel: 'Equipo / producto',
      conditionLabel: 'Condición general',
      showsMetrologicalConfiguration: false,
      showsReportFolio: true,
    };
  }
  return {
    technicalSectionTitle: 'Servicio, folio y hoja por equipo',
    addEquipmentTitle: 'Añadir equipo',
    addEquipmentDescription: 'Datos del equipo, cliente documental y servicio en una sola operación.',
    editEquipmentDescription: 'Datos del equipo, cliente documental y servicio. El folio se muestra de referencia y no se edita aquí.',
    sectionTitle: 'Datos del equipo',
    instrumentLabel: 'Instrumento',
    conditionLabel: 'Estado físico',
    showsMetrologicalConfiguration: true,
    showsReportFolio: false,
  };
}

/** Servicio General no usa FieldSheets, así que `equipment_by_equipment`
 * (hoja completa por equipo antes de la firma final) no aplica: su lifecycle
 * es group -- recepción firmada, captura técnica y reporte. Backend lo exige. */
export function categoryAllowsWorkflowChoice(category: LabOperationalCategory): boolean {
  return category === 'calibration';
}

export const REPORT_FOLIO_LABEL = 'Folio del reporte';
export const REPORT_FOLIO_PENDING_TEXT = 'Se asignará automáticamente';
export const SYSTEM_PLACED_HINT = 'Colocado por el sistema';

/** Valor mostrado en el campo: el folio institucional ya reservado o el aviso
 * de asignación automática. Mobile nunca fabrica ni edita este valor. */
export function reportFolioDisplay(technicalReportFolio: string | null | undefined): string {
  return technicalReportFolio || REPORT_FOLIO_PENDING_TEXT;
}
