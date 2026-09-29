// Presentación de la ejecución técnica MYC Mobile dentro del ETS (web).
//
// MYC Mobile es la ÚNICA interfaz de escritura técnica. El ERP sólo consulta
// la proyección READ-ONLY y ejecuta acciones administrativas explícitas del
// dominio LAB; nunca edita resultados, identidad técnica, firmas ni folios.
// La autoridad de permisos y estados es el backend: aquí sólo se decide qué
// mostrar; el servidor vuelve a validar cada acción.
import { hasPermission } from '../../utils/accessControl.js';

export const LAB_WORK_ORDER_STATUS_LABELS = {
  draft: 'Borrador',
  received_signed: 'Recepción firmada',
  in_progress: 'En proceso',
  ready_for_signatures: 'Lista para firmas',
  ready_to_close: 'Lista para cierre',
  completed: 'Cerrada',
  partially_closed: 'Cierre parcial',
  cancelled: 'Cancelada',
};

export const LAB_FOLIO_STATUS_LABELS = {
  unassigned: 'Sin folio',
  pending: 'Pendiente',
  reserved: 'Reservado',
  authorized: 'Autorizado',
};

export const LAB_FIELD_SHEET_STATUS_LABELS = {
  draft: 'Borrador',
  in_progress: 'En captura',
  completed: 'Completada',
  under_review: 'En revisión',
  approved: 'Aprobada',
  returned_to_technician: 'Devuelta',
  rejected: 'Rechazada',
};

export const LAB_SERVICE_TYPE_LABELS = {
  accredited: 'Acreditado',
  traceable: 'Trazable',
  linked: 'Vinculado',
};

// Estados LAB en los que el dominio permite enviar una hoja completada a
// corrección (reapertura directa de la hoja o reapertura de la OT cerrada).
const OPEN_CORRECTABLE_STATUSES = new Set(['received_signed', 'in_progress', 'ready_to_close']);
const CLOSED_CORRECTABLE_STATUSES = new Set(['completed', 'partially_closed']);

export const CAPTURE_BLOCKER_LABELS = {
  LAB_LINK_REQUIRED: 'Vincula el servicio MYC Mobile del ETS',
  LAB_NO_ACTIVE_EQUIPMENT: 'El servicio MYC Mobile no tiene equipos activos',
  LAB_WORK_ORDER_NOT_FINAL: 'OT sin cierre técnico en MYC Mobile',
  LAB_CERTIFICATE_FOLIO_MISSING: 'Sin folio de certificado',
  LAB_CERTIFICATE_FOLIO_NOT_READY: 'Folio no reservado/autorizado',
  LAB_FIELD_SHEET_MISSING: 'Sin Hoja de Campo',
  LAB_FIELD_SHEET_NOT_COMPLETED: 'Hoja de Campo no completada',
  LAB_FINAL_PDF_MISSING: 'Sin PDF final congelado',
  LAB_FINAL_PDF_HASH_MISMATCH: 'PDF final alterado (SHA-256)',
};

export function getMobileExecutionPermissions(user) {
  return {
    // Mismo contrato del bridge: create Y update; Técnico puro no administra.
    canManageLink: hasPermission(user, 'service_orders.create') && hasPermission(user, 'service_orders.update'),
    canReadFieldSheets: hasPermission(user, 'field_sheets.read'),
    canRequestCorrection: hasPermission(user, 'work_orders.reopen'),
    canCancelWorkOrders: hasPermission(user, 'lab_work_orders.cancel'),
  };
}

export function correctionModeFor(workOrder, equipment) {
  const sheet = equipment?.field_sheet;
  if (!sheet || sheet.status !== 'completed') return null;
  if (OPEN_CORRECTABLE_STATUSES.has(workOrder?.status)) return 'field_sheet_reopen';
  if (CLOSED_CORRECTABLE_STATUSES.has(workOrder?.status)) return 'work_order_reopen';
  return null;
}

export function summarizeMobileExecution(projection) {
  const workOrders = Array.isArray(projection?.work_orders) ? projection.work_orders : [];
  const equipment = workOrders.flatMap((workOrder) => workOrder.equipment || []);
  return {
    workOrders: workOrders.length,
    equipment: equipment.length,
    completedSheets: equipment.filter((item) => item.field_sheet?.status === 'completed').length,
    finalPdfs: equipment.filter((item) => item.field_sheet?.has_final_pdf).length,
  };
}

export function captureStateLabel(summary) {
  return summary?.ready ? 'LISTA' : 'BLOQUEADA';
}

export function describeCaptureBlocker(blocker) {
  const label = CAPTURE_BLOCKER_LABELS[blocker?.code] || blocker?.message || blocker?.code || 'Bloqueo';
  const where = [
    blocker?.work_order_folio ? `OT ${blocker.work_order_folio}` : null,
    blocker?.position ? `Equipo ${blocker.position}` : null,
    blocker?.instrument || null,
    blocker?.certificate_folio || null,
  ].filter(Boolean).join(' · ');
  return where ? `${where}: ${label}` : label;
}

// ---------------------------------------------------------------------------
// Detalle técnico READ-ONLY (equipo + hoja). Sólo pares etiqueta/valor; nunca
// inputs. Las etiquetas salen de la definición de plantilla cuando existe.
// ---------------------------------------------------------------------------

export function formatReadOnlyValue(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'boolean') return value ? 'Sí' : 'No';
  if (Array.isArray(value)) return value.map(formatReadOnlyValue).filter(Boolean).join(', ');
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([key, item]) => {
        const text = formatReadOnlyValue(item);
        return text ? `${humanizeKey(key)}: ${text}` : '';
      })
      .filter(Boolean)
      .join(' · ');
  }
  return String(value).trim();
}

export function humanizeKey(key) {
  const text = String(key || '').replace(/[_-]+/g, ' ').trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : '';
}

function rows(pairs) {
  return pairs
    .map(([label, value]) => [label, formatReadOnlyValue(value)])
    .filter(([, value]) => value !== '');
}

export function describeEquipmentReadOnly(equipment) {
  if (!equipment) return [];
  return rows([
    ['Instrumento', equipment.instrument],
    ['Marca', equipment.brand],
    ['Modelo', equipment.model],
    ['Serie', equipment.serial_number],
    ['Identificación', equipment.identification],
    ['Número de reporte', equipment.report_number],
    ['Condición al recibir', equipment.is_good_condition === undefined ? null : (equipment.is_good_condition ? 'Buena' : 'Con observaciones')],
    ['Observaciones del técnico', equipment.observations],
    ['Tipo de servicio', LAB_SERVICE_TYPE_LABELS[equipment.service_type] || equipment.service_type],
    ['Empresa vinculada', equipment.linked_company_name_snapshot],
    ['Folio de certificado', equipment.certificate_folio],
    ['Estado del folio', LAB_FOLIO_STATUS_LABELS[equipment.folio_status] || equipment.folio_status],
  ]);
}

export function describeDocumentaryClient(equipment) {
  if (!equipment) return [];
  if (equipment.certificate_client_mode !== 'different') {
    return [['Cliente documental', 'Mismo cliente de la OT']];
  }
  return rows([
    ['Cliente documental', 'Diferente al de la OT'],
    ['Empresa', equipment.final_client_company_snapshot],
    ['Dirección', equipment.final_client_address_snapshot],
    ['Atención', equipment.final_client_attention_snapshot],
  ]);
}

export function describeFieldSheetSections(sheet) {
  if (!sheet) return [];
  return [
    {
      title: 'Datos de calibración',
      rows: rows([
        ['Estado', LAB_FIELD_SHEET_STATUS_LABELS[sheet.status] || sheet.status],
        ['Revisión', sheet.revision_number],
        ['Plantilla', sheet.template_definition?.name || sheet.template_key],
        ['Fecha de recepción', sheet.reception_date],
        ['Fecha de calibración', sheet.calibration_date],
        ['Próxima calibración', sheet.next_calibration_date],
        ['Lugar de calibración', sheet.calibration_place],
        ['Ubicación', sheet.location],
        ['Unidades', sheet.units],
        ['Método', sheet.method],
        ['División mínima', sheet.minimum_division],
        ['Patrón utilizado', sheet.pattern_used],
        ['OC / cotización', sheet.purchase_order_or_quotation],
      ]),
    },
    {
      title: 'Condiciones ambientales',
      rows: rows([
        ['Temperatura inicio', sheet.environment_temperature_start],
        ['Temperatura fin', sheet.environment_temperature_end],
        ['Humedad inicio', sheet.environment_humidity_start],
        ['Humedad fin', sheet.environment_humidity_end],
        ['Condiciones ambientales', sheet.environmental_conditions],
      ]),
    },
    {
      title: 'Condición del equipo',
      rows: rows([
        ['Condición general', sheet.equipment_general_condition === null || sheet.equipment_general_condition === undefined
          ? null
          : (sheet.equipment_general_condition ? 'Buena' : 'Con observaciones')],
        ['Considera desviaciones', sheet.consider_equipment_deviations],
        ['Condición inicial', sheet.initial_condition],
        ['Condición final', sheet.final_condition],
      ]),
    },
    {
      title: 'Responsables',
      rows: rows([
        ['Calibró', sheet.calibrated_by],
        ['Revisó', sheet.reviewed_by],
        ['Elaboró', sheet.report_made_by],
      ]),
    },
    {
      title: 'Notas del técnico',
      rows: rows([
        ['Observaciones', sheet.observations],
        ['Notas de evidencia', sheet.evidence_notes],
        ['Notas técnicas', sheet.technician_notes],
        ['Resultados', sheet.results],
      ]),
    },
  ].filter((section) => section.rows.length);
}

function templateFieldLabels(definition) {
  const labels = new Map();
  for (const block of definition?.blocks || []) {
    for (const field of block.fields || []) {
      if (field?.key && field.label) labels.set(field.key, field.label);
    }
  }
  return labels;
}

// Identidad del equipo ya mostrada en la sección EQUIPO: no se repite.
const CAPTURE_IDENTITY_KEYS = new Set(['instrument', 'brand', 'model', 'serial_number', 'internal_id']);

export function describeCaptureValues(sheet) {
  const values = sheet?.capture_values;
  if (!values || typeof values !== 'object') return [];
  const labels = templateFieldLabels(sheet.template_definition);
  return rows(
    Object.entries(values)
      .filter(([key]) => !CAPTURE_IDENTITY_KEYS.has(key))
      .map(([key, value]) => [labels.get(key) || humanizeKey(key), value])
  );
}

const STANDARD_RESULT_COLUMNS = [
  ['pattern_value', 'Patrón'],
  ['ibc_value_1', 'Lectura 1'],
  ['ibc_value_2', 'Lectura 2'],
  ['ibc_value_3', 'Lectura 3'],
  ['unit', 'Unidad'],
  ['notes', 'Notas'],
];

function templateResultSections(definition) {
  const sections = new Map();
  const add = (section) => {
    if (section?.key && !sections.has(section.key)) sections.set(section.key, section);
  };
  (definition?.result_sections || []).forEach(add);
  (definition?.blocks || []).forEach((block) => (block.sections || []).forEach(add));
  return sections;
}

function resultCell(row, column) {
  const data = row.row_data && typeof row.row_data === 'object' ? row.row_data : {};
  if (data[column.key] !== undefined) return data[column.key];
  if (column.source && row[column.source] !== undefined) return row[column.source];
  return row[column.key];
}

// results_rows → tablas legibles. Usa columnas/títulos de la plantilla y
// representa también row_data dinámico; nunca muestra JSON crudo.
export function describeResultSections(sheet) {
  const resultRows = Array.isArray(sheet?.results_rows) ? sheet.results_rows : [];
  if (!resultRows.length) return [];
  const templates = templateResultSections(sheet.template_definition);
  const bySection = new Map();
  for (const row of resultRows) {
    const key = row.section_key || 'resultados';
    if (!bySection.has(key)) bySection.set(key, []);
    bySection.get(key).push(row);
  }
  return [...bySection.entries()].map(([key, sectionRows]) => {
    const template = templates.get(key);
    const columns = (template?.columns || []).map((column) => ({
      key: column.key, source: column.source, label: column.label || humanizeKey(column.key),
    }));
    if (!columns.length) {
      for (const [field, label] of STANDARD_RESULT_COLUMNS) {
        if (sectionRows.some((row) => formatReadOnlyValue(row[field]) !== '')) columns.push({ key: field, label });
      }
    }
    const known = new Set(columns.flatMap((column) => [column.key, column.source].filter(Boolean)));
    for (const row of sectionRows) {
      for (const dataKey of Object.keys(row.row_data || {})) {
        if (!known.has(dataKey)) {
          known.add(dataKey);
          columns.push({ key: dataKey, label: humanizeKey(dataKey) });
        }
      }
    }
    const orderedRows = [...sectionRows].sort((a, b) => (a.row_number ?? 0) - (b.row_number ?? 0));
    return {
      key,
      title: template?.title || humanizeKey(key),
      columns,
      rows: orderedRows
        .map((row, index) => ({
          id: row.id ?? `${key}-${row.row_number ?? index}`,
          label: template?.row_labels?.[(row.row_number ?? index + 1) - 1] || String(row.row_number ?? index + 1),
          cells: columns.map((column) => formatReadOnlyValue(resultCell(row, column))),
        }))
        .filter((row) => row.cells.some((cell) => cell !== '')),
    };
  }).filter((section) => section.rows.length);
}

// Compatibilidad: resumen breve de una hoja como pares etiqueta/valor.
export function describeFieldSheetReadOnly(sheet) {
  if (!sheet) return [];
  return [
    ['Estado', LAB_FIELD_SHEET_STATUS_LABELS[sheet.status] || sheet.status],
    ['Revisión', sheet.revision_number],
    ['Plantilla', sheet.template_key],
    ['Fecha de calibración', sheet.calibration_date],
    ['Próxima calibración', sheet.next_calibration_date],
    ['Lugar de calibración', sheet.calibration_place],
    ['Calibró', sheet.calibrated_by],
    ['Revisó', sheet.reviewed_by],
    ['Unidades', sheet.units],
    ['Método', sheet.method],
    ['Condición inicial', sheet.initial_condition],
    ['Condición final', sheet.final_condition],
    ['Observaciones', sheet.observations],
    ['Resultados', sheet.results],
  ].filter(([, value]) => value !== null && value !== undefined && value !== '');
}
