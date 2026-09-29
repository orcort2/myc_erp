import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const panel = readFileSync(new URL('./EtsMobileExecutionPanel.jsx', import.meta.url), 'utf8');
const capture = readFileSync(new URL('./EtsMobileCapturePanel.jsx', import.meta.url), 'utf8');
const page = readFileSync(new URL('../../pages/ServiceOrdersPage.jsx', import.meta.url), 'utf8');

function slice(source, start, end) {
  const from = source.indexOf(start);
  assert.ok(from >= 0, start);
  return source.slice(from, source.indexOf(end, from + start.length));
}

test('ETS Mobile: sin vínculo ofrece "Vincular servicio MYC Mobile" sólo con permiso de gestión', () => {
  assert.match(panel, /Vincular servicio MYC Mobile/);
  assert.match(panel, /permissions\.canManageLink \? \(/);
  assert.match(panel, /linkServiceOrderLab\(serviceOrderId, candidate\.root_id\)/);
  assert.match(panel, /replaceServiceOrderLab\(serviceOrderId, candidate\.root_id, reason\.trim\(\)\)/);
  assert.match(page, /mobileLabLink\.status === 'linked' \? 'Abrir ejecución técnica' : 'Vincular servicio MYC Mobile'/);
});

test('ETS Mobile: proyección grupo → OT → equipo con identidad, folio y estado de hoja', () => {
  assert.match(panel, /getServiceOrderMobileExecution\(serviceOrderId\)/);
  for (const field of ['serial_number', 'identification', 'certificate_folio', 'folio_status', 'service_type']) {
    assert.ok(panel.includes(`equipment.${field}`), field);
  }
  assert.match(panel, /Ver hoja/);
  assert.match(panel, /sheet\?\.has_final_pdf/);
});

test('un admin ERP NO puede modificar resultados técnicos: el detalle de hoja no tiene inputs', () => {
  const detail = slice(panel, 'function FieldSheetDetail(', '\n// "Enviar a corrección en MYC Mobile"');
  assert.doesNotMatch(detail, /<input|<textarea|<select|contentEditable/);
  assert.doesNotMatch(detail, /onChange=/);
  assert.match(detail, /data-readonly="true"/);
  assert.match(detail, /sólo se capturan y corrigen en MYC Mobile/);
  // Ninguna llamada de escritura técnica LAB/FieldSheet desde el ERP.
  assert.doesNotMatch(panel, /updateFieldSheet|lab-work-orders\/.*field-sheet|method: 'PATCH'/);
});

test('ver PDF final usa el PDF congelado de la proyección', () => {
  assert.match(panel, /downloadServiceOrderMobileFieldSheetPdf\(serviceOrderId, fieldSheetId\)/);
});

test('Captura Mobile: LISTA/BLOQUEADA, bloqueos y descarga PDF sólo cuando está lista, sin carga XLSX', () => {
  assert.match(capture, /captureStateLabel\(summary\)/);
  assert.match(capture, /summary\.blockers\.map/);
  assert.match(capture, /describeCaptureBlocker\(blocker\)/);
  assert.match(capture, /disabled=\{!ready \|\| busy\}/);
  assert.match(capture, /Descargar paquete PDF/);
  assert.doesNotMatch(capture, /uploadCaptureFiles|type="file"|\.xlsx/);
  assert.match(page, /activeTab === 'capture' && selectedOrderManagedByMobile \? \(\s*<EtsMobileCapturePanel/);
  assert.match(page, /activeTab === 'capture' && !selectedOrderManagedByMobile \? \(/);
});

test('acciones administrativas sólo según permisos; enviar a corrección exige motivo', () => {
  assert.match(panel, /permissions\.canRequestCorrection && correctionModeFor\(workOrder, equipment\)/);
  assert.match(panel, /permissions\.canCancelWorkOrders \? \(/);
  const dialog = slice(panel, 'function CorrectionDialog(', '\nexport default function');
  assert.match(dialog, /if \(!reason\.trim\(\)\) \{\s*setError\('El motivo es obligatorio\.'\)/);
  assert.match(dialog, /disabled=\{busy \|\| !reason\.trim\(\)\}/);
  assert.match(dialog, /requestServiceOrderMobileCorrection\(serviceOrderId, target\.equipment\.id/);
  // El único texto editable es el motivo y la política de firmas: nunca valores técnicos.
  assert.equal((dialog.match(/<textarea/g) || []).length, 1);
  assert.equal((dialog.match(/<select/g) || []).length, 1);
  assert.doesNotMatch(dialog, /<input/);
  assert.match(dialog, /exclusivamente en MYC Mobile/);
});
