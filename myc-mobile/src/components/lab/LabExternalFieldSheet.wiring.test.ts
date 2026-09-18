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

// La decisión post-PR #4 reemplaza la pantalla independiente por resultados
// especializados dentro del formulario común. Los endpoints no cambian.
test('LAB EXTERNO especializa resultados dentro de la captura común', () => {
  assert.match(captureSource, /const definition = labExternal \? undefined/);
  assert.match(captureSource, /readOnly=\{!canCapture \|\| !editable\}/);
  assert.match(captureSource, /onSaved=\{setSheet\}/);
  assert.doesNotMatch(externalSource, /canReopenFieldSheetDirectly/);
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
    externalSource.indexOf('  return ('),
  );
  assert.match(fn, /\$\{workOrder\.id\}\/equipment\/\$\{equipment\.id\}\/field-sheet`,\s*\n\s*\{ method: 'PATCH'/);
  assert.match(fn, /buildLabExternalValuesPatch\(rows\)/);
});

test('completar y reabrir pertenecen al controlador común y protegen cambios pendientes', () => {
  assert.match(captureSource, /if \(externalResultsDirty\)/);
  assert.match(captureSource, /\/field-sheet\/complete/);
  assert.match(captureSource, /\/field-sheet\/reopen/);
  assert.doesNotMatch(externalSource, /async function (completeSheet|reopenSheet)/);
});

test('resultados respetan permiso/modo de edición común y estado editable', () => {
  assert.match(externalSource, /!readOnly && EDITABLE_STRUCTURE_STATUSES.has\(sheet.status\)/);
  assert.match(externalSource, /onDirtyChange\(structureDirty \|\| valuesDirty\)/);
});

test('el encabezado común identifica LAB EXTERNO', () => {
  assert.match(captureSource, /Hoja de campo "LAB EXTERNO"/);
});
