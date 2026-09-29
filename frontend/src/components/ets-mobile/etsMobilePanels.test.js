import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const panel = read('./EtsMobileExecutionPanel.jsx');
const capture = read('./EtsMobileCapturePanel.jsx');
const detail = read('./EtsMobileEquipmentDetail.jsx');
const correction = read('./EtsMobileCorrectionDialog.jsx');
const hook = read('./useMobileCaptureSummary.js');
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

// ------------------------------------------------ Layout dedicado

test('vista Mobile usa clases propias y no los grids legacy de Hojas de Campo', () => {
  for (const source of [panel, capture]) {
    assert.doesNotMatch(source, /ets-field-sheet-work-order__summary|ets-field-sheet-equipment-row|ets-field-sheet-work-order is-expanded/);
    for (const className of [
      'ets-mobile-work-order', 'ets-mobile-work-order__header', 'ets-mobile-equipment-card',
      'ets-mobile-equipment-card__identity', 'ets-mobile-equipment-card__meta', 'ets-mobile-equipment-card__actions',
    ]) {
      assert.ok(source.includes(`"${className}"`), className);
    }
  }
  assert.match(panel, /"ets-mobile-work-order__actions"/);
});

test('CSS dedicado: minmax(0, …) y container queries por ancho del contenedor', () => {
  const block = css.slice(css.indexOf('/* Ejecución técnica MYC Mobile'));
  assert.match(block, /\.ets-mobile-work-order__header \{[^}]*grid-template-columns: minmax\(0, 1fr\) auto auto;/);
  assert.match(block, /\.ets-mobile-equipment-card \{[^}]*grid-template-columns: minmax\(0, 1\.2fr\) minmax\(0, 2\.4fr\) minmax\(0, auto\);/);
  assert.match(block, /container-type: inline-size;/);
  assert.match(block, /@container \(max-width: 720px\)/);
  assert.doesNotMatch(block, /@media/);
  assert.match(block, /\.ets-mobile-equipment-card__actions \{[^}]*flex-wrap: wrap;/);
  assert.match(block, /overflow-wrap: anywhere/);
  // Las clases legacy no se tocaron en este bloque.
  assert.doesNotMatch(block, /^\s*\.ets-field-sheet-[^{]*\{/m);
});

// ------------------------------------------------ Navegación read-only

test('la identidad del equipo abre el detalle desde Ejecución y desde Captura (mismo componente)', () => {
  assert.match(panel, /import EtsMobileEquipmentDetail from '\.\/EtsMobileEquipmentDetail\.jsx'/);
  assert.match(capture, /import EtsMobileEquipmentDetail from '\.\/EtsMobileEquipmentDetail\.jsx'/);
  assert.match(panel, /className="ets-mobile-equipment-card__link"\s*onClick=\{\(\) => setDetailEquipmentId\(equipment\.id\)\}/);
  assert.match(capture, /className="ets-mobile-equipment-card__link"\s*onClick=\{\(\) => setDetailEquipmentId\(item\.equipment_id\)\}/);
  // Click sobre el estado de la Hoja en Captura también abre el detalle.
  assert.match(capture, /className="ets-mobile-equipment-card__inline-link"\s*onClick=\{\(\) => setDetailEquipmentId\(item\.equipment_id\)\}/);
  assert.match(panel, /<small>Ver detalle<\/small>/);
  // La card no es un <button> que contenga otros botones.
  assert.doesNotMatch(panel + capture, /<button[^>]*className="ets-mobile-equipment-card"/);
  // No hay dos implementaciones del detalle.
  assert.doesNotMatch(panel, /function FieldSheetDetail|getServiceOrderMobileFieldSheet/);
});

test('un admin ERP NO puede modificar resultados técnicos: el detalle no tiene inputs ni PATCH', () => {
  assert.doesNotMatch(detail, /<input|<textarea|<select|contentEditable|onChange=/);
  assert.doesNotMatch(detail + panel + capture, /method: 'PATCH'|updateFieldSheet|lab-work-orders\/.*field-sheet/);
  assert.match(detail, /data-readonly="true"/);
  assert.match(detail, /sólo se capturan y corrigen en MYC Mobile/);
  for (const section of ['<h3>Equipo</h3>', '<h3>Cliente documental</h3>', '<h3>Hoja de Campo</h3>', '<h3>Revisiones</h3>']) {
    assert.ok(detail.includes(section), section);
  }
  for (const helper of ['describeEquipmentReadOnly', 'describeDocumentaryClient', 'describeFieldSheetSections', 'describeCaptureValues', 'describeResultSections']) {
    assert.ok(detail.includes(`${helper}(`), helper);
  }
});

test('detalle: PDF final congelado y revisiones vigente/histórica con timestamps', () => {
  assert.match(detail, /downloadServiceOrderMobileFieldSheetPdf\(serviceOrderId, fieldSheetId\)/);
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

test('copy de Captura describe la estructura plana del ZIP', () => {
  assert.match(capture, /una carpeta por OT y cada archivo nombrado con\s+el folio de certificado LAB/);
});
