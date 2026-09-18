import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * PENDIENTE 7 (encargo de corrección LAB): verificación de cableado --
 * mismo patrón assert.match sobre el source que el resto de wiring-tests --
 * de la integración "LAB EXTERNO" en LabTechnicalCapture.tsx y de los
 * endpoints que LabExternalFieldSheet.tsx realmente llama.
 */
const captureSource = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './LabTechnicalCapture.tsx'),
  'utf8',
);
const externalSource = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './LabExternalFieldSheet.tsx'),
  'utf8',
);

test('un equipo linked nunca ve el selector de plantilla interna -- LAB EXTERNO se crea automáticamente al abrir por primera vez', () => {
  const fn = captureSource.slice(
    captureSource.indexOf('async function openSheet'),
    captureSource.indexOf('async function createSheet'),
  );
  assert.match(fn, /if \(!equipment\.field_sheet_id && isLabExternalEquipment\(equipment\)\) \{/);
  assert.match(fn, /template_key: LAB_EXTERNAL_TEMPLATE_KEY/);
});

test('LabTechnicalCapture delega en LabExternalFieldSheet para un equipo linked, ANTES que cualquier flujo de ticketMode', () => {
  const activeEquipmentBlock = captureSource.slice(captureSource.indexOf('if (activeEquipment) {'));
  const externalBranchIndex = activeEquipmentBlock.indexOf('isLabExternalEquipment(activeEquipment)');
  const firstTicketModeIndex = activeEquipmentBlock.indexOf("ticketMode === 'field_sheet_template'");
  assert.notEqual(externalBranchIndex, -1);
  assert.notEqual(firstTicketModeIndex, -1);
  assert.ok(externalBranchIndex < firstTicketModeIndex, 'LAB EXTERNO debe resolverse antes que los flujos de ticketMode');
});

test('LabExternalFieldSheet recibe canReopenFieldSheetDirectly -- misma autoridad que el resto de la captura, sin permiso nuevo', () => {
  const block = captureSource.slice(
    captureSource.indexOf('isLabExternalEquipment(activeEquipment)) return'),
    captureSource.indexOf('if (ticketMode === \'field_sheet_template\')'),
  );
  assert.match(block, /canReopenFieldSheetDirectly=\{canReopenFieldSheetDirectly\}/);
});

test('la estructura se guarda con PUT .../field-sheet/lab-externo/structure, nunca un endpoint distinto', () => {
  const fn = externalSource.slice(
    externalSource.indexOf('async function saveStructure'),
    externalSource.indexOf('async function saveValues'),
  );
  assert.match(fn, /\/field-sheet\/lab-externo\/structure/);
  assert.match(fn, /method:\s*'PUT'/);
  assert.match(fn, /buildLabExternalStructurePayload\(groups\)/);
});

test('los valores capturados reutilizan el PATCH .../field-sheet ya existente -- ningún endpoint nuevo para esto', () => {
  const fn = externalSource.slice(
    externalSource.indexOf('async function saveValues'),
    externalSource.indexOf('async function completeSheet'),
  );
  assert.match(fn, /\$\{workOrder\.id\}\/equipment\/\$\{equipment\.id\}\/field-sheet`,\s*\n\s*\{ method: 'PATCH'/);
  assert.match(fn, /buildLabExternalValuesPatch\(rows\)/);
});

test('completar la hoja reutiliza POST .../field-sheet/complete ya existente, y exige guardar cambios pendientes primero', () => {
  const fn = externalSource.slice(
    externalSource.indexOf('async function completeSheet'),
    externalSource.indexOf('return (\n    <View>'),
  );
  assert.match(fn, /if \(structureDirty \|\| valuesDirty\) \{/);
  assert.match(fn, /\/field-sheet\/complete/);
  assert.match(fn, /method:\s*'POST'/);
});

test('reabrir reutiliza POST .../field-sheet/reopen ya existente -- mismas reglas que cualquier otra hoja LAB', () => {
  const fn = externalSource.slice(
    externalSource.indexOf('async function reopenSheet'),
    externalSource.indexOf('return (\n    <View>'),
  );
  assert.match(fn, /\/field-sheet\/reopen/);
  assert.match(fn, /method:\s*'POST'/);
  assert.match(fn, /reason: reopenReason\.trim\(\)/);
});

test('la estructura y los valores dejan de ser editables fuera de draft/in_progress -- nunca se edita una hoja completed', () => {
  assert.match(externalSource, /const EDITABLE_STRUCTURE_STATUSES = new Set\(\['draft', 'in_progress'\]\);/);
  assert.match(externalSource, /const editableStructure = EDITABLE_STRUCTURE_STATUSES\.has\(sheet\.status\);/);
});

test('el encabezado dice exactamente Hoja de campo "LAB EXTERNO"', () => {
  assert.match(externalSource, /Hoja de campo "LAB EXTERNO"/);
});
