import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const panel = read('./EtsMobileExecutionPanel.jsx');
const capture = read('./EtsMobileCapturePanel.jsx');
const detail = read('./EtsMobileEquipmentDetail.jsx');
const correction = read('./EtsMobileCorrectionDialog.jsx');
const hook = read('./useMobileCaptureSummary.js');
const documents = read('./labDocumentActions.js');
const modal = read('./EtsMobileModal.jsx');
const page = read('../../pages/ServiceOrdersPage.jsx');
const css = read('../../styles/global.css');

// ------------------------------------------------ Captura: autoridad única LAB

test('Captura Mobile: un único loader elevado alimenta pestaña, franja del Resumen y panel', () => {
  assert.match(hook, /getCapturePackageSummary\(serviceOrderId\)/);
  assert.match(page, /useMobileCaptureSummary\(selectedOrderManagedByMobile \? selectedOrder\?\.id : null\)/);
  assert.match(page, /if \(selectedOrderManagedByMobile\) \{\s*states\.capture = getMobileCaptureStageStatus\(mobileCaptureSummary\);/);
  // El panel ya no consulta por su cuenta: recibe el summary y usa el mismo refresh.
  assert.doesNotMatch(capture, /getCapturePackageSummary/);
  assert.match(page, /summary=\{mobileCaptureSummary\}/);
  assert.match(page, /onRefresh=\{refreshMobileCaptureSummary\}/);
  assert.match(capture, /onClick=\{\(\) => onRefresh\?\.\(\)\}/);
  // Pestaña y franja leen el mismo selectedStageState.capture.
  assert.match(page, /selectedStageState\[key\]\?\.label/);
  assert.match(page, /\['Captura', selectedStageState\.capture\?\.ready, selectedStageState\.capture\?\.status\]/);
  // Correcciones/cancelaciones/vínculo refrescan la misma autoridad.
  assert.match(page, /onExecutionChanged=\{refreshMobileCaptureSummary\}/);
});

test('ETS legacy conserva el pipeline ERP de Captura', () => {
  assert.match(page, /const captureStage =\s*getCaptureStageStatus\(\{/);
  assert.match(page, /states\.capture = captureStage;/);
});

test('Captura Mobile no muta el ETS ni carga XLSX', () => {
  for (const source of [capture, hook]) {
    assert.doesNotMatch(source, /updateServiceOrder|changeServiceOrderStatus|method: 'PATCH'|uploadCaptureFiles|type="file"/);
  }
  assert.match(capture, /disabled=\{!ready \|\| busy\}/);
  assert.match(capture, /summary\.blockers\.map/);
  assert.match(capture, /describeCaptureBlocker\(blocker\)/);
});

// ------------------------------------------------ Diseño ERP-native

test('vistas LAB usan el design system del ERP y clases .ets-lab-* sólo de layout', () => {
  for (const source of [panel, capture]) {
    assert.doesNotMatch(source, /ets-mobile-|ets-field-sheet-work-order__summary|ets-field-sheet-equipment-row/);
    for (const className of ['quotation-section ets-lab-work-order', 'quotation-section__title', 'ets-metric-strip', 'ets-metric-badge',
      'glass-card-mini ets-lab-equipment-card', 'read-only-grid ets-lab-readonly-grid', 'quotation-status', 'toolbar-actions', 'table-button']) {
      assert.ok(source.includes(className), className);
    }
  }
  assert.match(panel, /className="section-heading ets-lab-execution__heading"/);
  assert.match(detail, /className="read-only-grid ets-lab-readonly-grid"/);
  assert.match(detail, /className="quotation-section ets-lab-detail__section"/);
  assert.match(modal, /className="client-modal quotation-detail-modal ets-lab-modal"/);
});

test('CSS LAB: layout con minmax(0, …), container queries y variables del ERP; sin tocar clases legacy', () => {
  const block = css.slice(css.indexOf('/* Ejecución técnica LAB dentro del ERP'));
  assert.doesNotMatch(block, /ets-mobile-/);
  assert.match(block, /\.glass-card-mini\.ets-lab-equipment-card \{[^}]*grid-template-columns: minmax\(0, 1\.1fr\) minmax\(0, 2\.6fr\) minmax\(0, auto\);/);
  assert.match(block, /container-type: inline-size;/);
  assert.match(block, /@container \(max-width: 760px\)/);
  assert.doesNotMatch(block, /@media/);
  assert.match(block, /var\(--myc-primary\)/);
  assert.doesNotMatch(block, /^\s*\.(ets-field-sheet-|glass-card-mini|read-only-grid|quotation-section)[^.{]*\{/m);
});

// ------------------------------------------------ Documentos oficiales LAB

test('OT: Ver / Imprimir / Descargar sólo con PDF final; si no, "OT final no disponible"', () => {
  assert.match(panel, /\{header\.hasFinalPdf \? \(/);
  for (const label of ['Ver OT', 'Imprimir OT', 'Descargar OT']) assert.ok(panel.includes(`>${label}</button>`), label);
  assert.match(panel, /OT final no disponible/);
  assert.match(panel, /viewLabPdf\(otLoader/);
  assert.match(panel, /printLabPdf\(otLoader/);
  assert.match(panel, /downloadLabPdf\(otLoader, `OT-\$\{workOrder\.folio\}\.pdf`\)/);
  assert.match(documents, /downloadServiceOrderMobileWorkOrderPdf\(serviceOrderId, workOrderId\)/);
});

test('Imprimir usa el PDF oficial en el visor del navegador, nunca el DOM', () => {
  assert.match(documents, /openQuotationPdfWindow\(loadPdf, \{ print: true/);
  for (const source of [panel, capture, detail, documents]) {
    assert.doesNotMatch(source, /window\.print\(\)/);
  }
});

test('acciones documentales y administrativas separadas en grupos distintos', () => {
  const documentsGroup = panel.indexOf('aria-label="Documentos"');
  const adminGroup = panel.indexOf('aria-label="Administración"');
  assert.ok(documentsGroup > 0 && adminGroup > documentsGroup);
  const documentsBlock = panel.slice(documentsGroup, adminGroup);
  assert.doesNotMatch(documentsBlock, /Cancelar OT|Restaurar OT/);
  assert.match(panel.slice(adminGroup), /Cancelar OT/);
  assert.match(panel, /permissions\.canCancelWorkOrders \? \(\s*<div className="ets-lab-action-group ets-lab-action-group--admin"/);
});

test('cabecera de OT: rol, estado, cliente, recepción, salida, equipos, hojas y PDFs', () => {
  for (const text of ['header.role', 'header.statusLabel', 'workOrder.client_name', 'Recepción', 'Salida',
    'header.equipmentCount', 'header.completedSheets', 'header.finalSheetPdfs']) {
    assert.ok(panel.includes(text), text);
  }
});

test('Captura renderiza por OT el documento OT final y las Hojas de Campo', () => {
  assert.match(capture, /captureGroupDocuments\(group\)\.map/);
  assert.match(capture, /document\.kind === 'work_order'/);
  assert.match(capture, /document\.kind === 'field_sheet' && canReadTechnical/);
  assert.match(capture, /countCaptureDocuments\(summary\)/);
  for (const label of ['Ver OT', 'Ver detalle equipo', 'Ver hoja', 'Captura · handoff documental']) assert.ok(capture.includes(label), label);
  assert.doesNotMatch(capture, /<input|<textarea|<select/);
});

// ------------------------------------------------ Navegación read-only

test('la identidad del equipo abre el detalle desde Ejecución y desde Captura (mismo componente)', () => {
  assert.match(panel, /import EtsMobileEquipmentDetail from '\.\/EtsMobileEquipmentDetail\.jsx'/);
  assert.match(capture, /import EtsMobileEquipmentDetail from '\.\/EtsMobileEquipmentDetail\.jsx'/);
  assert.match(panel, /className="ets-lab-link" onClick=\{\(\) => setDetailEquipmentId\(equipment\.id\)\}/);
  assert.match(capture, /className="ets-lab-link" onClick=\{\(\) => setDetailEquipmentId\(item\.equipment_id\)\}/);
  // Click sobre el estado de la Hoja en Captura también abre el detalle.
  assert.match(capture, /className="ets-lab-inline-link" onClick=\{\(\) => setDetailEquipmentId\(item\.equipment_id\)\}/);
  assert.match(panel, /<small>Ver detalle<\/small>/);
  // La card no es un <button> que contenga otros botones.
  assert.doesNotMatch(panel + capture, /<button[^>]*className="[^"]*ets-lab-equipment-card"/);
  // No hay dos implementaciones del detalle.
  assert.doesNotMatch(panel, /function FieldSheetDetail|getServiceOrderMobileFieldSheet/);
});

test('un admin ERP NO puede modificar resultados técnicos: el detalle no tiene inputs ni PATCH', () => {
  assert.doesNotMatch(detail, /<input|<textarea|<select|contentEditable|onChange=/);
  assert.doesNotMatch(detail + panel + capture, /method: 'PATCH'|updateFieldSheet|lab-work-orders\/.*field-sheet/);
  assert.match(detail, /data-readonly="true"/);
  assert.match(detail, /sólo se capturan y corrigen en MYC Mobile/);
  for (const section of ['<p>Equipo</p>', '<p>Cliente documental</p>', '<p>Hoja de Campo</p>', '<p>Revisiones</p>']) {
    assert.ok(detail.includes(section), section);
  }
  for (const helper of ['describeEquipmentReadOnly', 'describeDocumentaryClient', 'describeFieldSheetSections', 'describeCaptureValues', 'describeResultSections']) {
    assert.ok(detail.includes(`${helper}(`), helper);
  }
});

test('detalle: PDF final congelado y revisiones vigente/histórica con timestamps', () => {
  assert.match(detail, /viewLabPdf\(fieldSheetPdfLoader\(serviceOrderId, fieldSheetId\)/);
  assert.match(detail, /revision\.is_current \? ' · vigente' : ' · histórica'/);
  assert.match(detail, /formatDateTime\(revision\.updated_at\)/);
  assert.match(detail, /currentRevision\?\.has_final_pdf/);
});

test('enviar a corrección: visible en el detalle sólo con work_orders.reopen y modo válido; mismo diálogo', () => {
  assert.match(detail, /const canCorrect = permissions\.canRequestCorrection && Boolean\(correctionMode\);/);
  assert.match(detail, /correctionModeFor\(\{ status: detail\.work_order_status \}, \{ field_sheet: sheet \}\)/);
  assert.match(detail, /\{canCorrect \? \(/);
  assert.match(detail, /import EtsMobileCorrectionDialog from '\.\/EtsMobileCorrectionDialog\.jsx'/);
  assert.match(panel, /import EtsMobileCorrectionDialog from '\.\/EtsMobileCorrectionDialog\.jsx'/);
  // Desde Captura el detalle abierto es el mismo componente y recibe el usuario.
  assert.match(capture, /<EtsMobileEquipmentDetail[\s\S]*?user=\{user\}/);
  assert.match(page, /<EtsMobileCapturePanel[\s\S]*?user=\{user\}/);
  // El diálogo sigue exigiendo motivo; sólo edita motivo/política de firmas.
  assert.match(correction, /if \(!reason\.trim\(\)\) \{\s*setError\('El motivo es obligatorio\.'\)/);
  assert.equal((correction.match(/<textarea/g) || []).length, 1);
  assert.equal((correction.match(/<select/g) || []).length, 1);
  assert.doesNotMatch(correction, /<input/);
  assert.match(correction, /requestServiceOrderMobileCorrection\(serviceOrderId, target\.equipment\.id/);
});

test('vínculo: "Vincular servicio MYC Mobile" sólo con permiso de gestión', () => {
  assert.match(panel, /Vincular servicio MYC Mobile/);
  assert.match(panel, /permissions\.canManageLink \? \(/);
  assert.match(page, /mobileLabLink\.status === 'linked' \? 'Abrir ejecución técnica' : 'Vincular servicio MYC Mobile'/);
});

test('copy de Captura describe el paquete OT + hojas por OT', () => {
  assert.match(capture, /por OT, el PDF final oficial de la OT y las Hojas de Campo finales/);
});
