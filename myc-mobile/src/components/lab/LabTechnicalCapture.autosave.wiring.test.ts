import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cableo del autosave silencioso de FieldSheet (ver
 * src/services/field-sheet-autosave.ts, que lleva la lógica probada de forma
 * pura): comprueba que LabTechnicalCapture lo usa donde corresponde y que no
 * reintroduce la rehidratación destructiva de reception_date.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './LabTechnicalCapture.tsx'),
  'utf8',
);

function fn(start: string, end: string): string {
  const from = source.indexOf(start);
  assert.ok(from >= 0, `no se encontró ${start}`);
  return source.slice(from, source.indexOf(end, from));
}

test('el autosave PATCHea la misma hoja sin results_rows, sin /complete y sin Alert', () => {
  const block = fn('autosaveRef.current = createFieldSheetAutosave', 'const autosave = autosaveRef.current');
  assert.match(block, /method: 'PATCH'/);
  assert.match(block, /normalizeFieldSheetPayload\(nextValues, currentSheet\)/);
  assert.doesNotMatch(block, /results_rows/);
  assert.doesNotMatch(block, /\/complete/);
  assert.doesNotMatch(block, /Alert\./);
  assert.match(block, /mergeAutosavedSheet\(current, saved\)/);
  assert.doesNotMatch(block, /setValues/, 'una respuesta de autosave jamás rehidrata los valores locales');
});

test('setField programa el autosave sólo cuando la hoja es editable', () => {
  const body = fn('function setField', 'async function updateReceptionDate');
  assert.match(body, /autosaveEnabledRef\.current\) autosave\.change\(next\)/);
});

test('blur de campos de texto hace flush inmediato', () => {
  assert.equal((source.match(/onBlur=\{\(\) => void autosave\.flush\(\)\}/g) ?? []).length, 2);
});

test('cambiar reception_date hace flush antes del PATCH y NO reemplaza los valores locales', () => {
  const body = fn('async function updateReceptionDate', '// Cierre de contrato canónico LAB: un campo canónico readonly');
  assert.ok(body.indexOf('await autosave.flush()') < body.indexOf("method: 'PATCH'"));
  assert.match(body, /mergeAuthoritativeSheetFields\(valuesRef\.current, refreshedSheet\)/);
  assert.doesNotMatch(body, /buildValues\(/);
  assert.doesNotMatch(body, /Alert\.alert/);
});

test('abrir otra hoja y volver a equipos exigen leave() exitoso: si falla no se abandona ni se descarta la captura', () => {
  const open = fn('async function openSheet', 'async function createSheet');
  assert.match(open, /autosave\.isDirty\(\) && !\(await autosave\.leave\(\)\)/);
  assert.match(open, /setFormError\(LEAVE_FAILED_MESSAGE\);\s*return;/);
  assert.match(source, /if \(!\(await autosave\.leave\(\)\)\) \{ setFormError\(LEAVE_FAILED_MESSAGE\); return; \} setActiveEquipment\(null\)/);
});

test('eliminar el borrador usa discard() (espera al PATCH ya enviado) y no reset/flush', () => {
  const body = fn('function confirmDiscardSheet', 'function openChangeTemplate');
  assert.match(body, /await autosave\.discard\(\)/);
  assert.doesNotMatch(body, /autosave\.reset/);
});

test('cambiar de plantilla aborta si el flush falla; no pierde el draft', () => {
  const body = fn('async function confirmChangeTemplate', 'async function downloadFieldSheetPdf');
  assert.match(body, /!\(await autosave\.flush\(\)\)/);
});

test('cambiar de equipo/hoja invalida el contexto del autosave (nunca mezcla drafts)', () => {
  assert.match(source, /autosave\.invalidateContext\(\);\s*\}, \[autosave, activeEquipment\?\.id, sheet\?\.id\]\)/);
  assert.doesNotMatch(source, /autosave\.reset\(/);
});

test('Guardar borrador y Completar siguen siendo manuales: hacen flush, leen refs vigentes y conservan sus Alert/complete', () => {
  const body = fn('async function saveSheet', 'async function requestFolio');
  assert.match(body, /await autosave\.flush\(\)/);
  assert.match(body, /normalizeFieldSheetPayload\(valuesRef\.current, latestSheet\)/);
  assert.match(body, /results_rows: latestSheet\.results_rows/);
  assert.match(body, /Alert\.alert\('Hoja guardada'/);
  assert.match(body, /field-sheet\/complete/);
});

test('Resultados se siguen guardando por su propio camino y no por el autosave', () => {
  const body = fn('async function saveResultsRows', 'async function saveSheet');
  assert.match(body, /body: JSON\.stringify\(\{ results_rows: rows \}\)/);
  assert.match(body, /setSheet\(saved\)/);
});

test('indicador discreto: Guardando… / Guardado, sin Alert de éxito', () => {
  assert.match(source, /saving: 'Guardando…'/);
  assert.match(source, /saved: 'Guardado'/);
});

const workspaceSource = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../field-sheets/FieldSheetResultsWorkspace.tsx'),
  'utf8',
);

test('Resultados NO usa autosave: su dirty depende sólo de sus filas y los campos generales no lo tocan', () => {
  assert.doesNotMatch(workspaceSource, /field-sheet-autosave|createFieldSheetAutosave/);
  assert.doesNotMatch(workspaceSource, /Props = \{[^}]*values/s, 'el workspace no recibe los campos generales');
  const block = fn('autosaveRef.current = createFieldSheetAutosave', 'const autosave = autosaveRef.current');
  assert.doesNotMatch(block, /results_rows/);
  assert.match(source, /onSave=\{saveResultsRows\}/);
});

test('el pie "Cerrar" del workspace reutiliza onClose/requestClose; el encabezado ya no tiene Cerrar', () => {
  assert.doesNotMatch(workspaceSource, /<CloseButton/);
  assert.match(workspaceSource, /label="Cerrar" onPress=\{requestClose\}/);
  assert.match(workspaceSource, /onRequestClose=\{requestClose\}/);
  assert.match(source, /onClose=\{\(\) => setResultsOpen\(false\)\}/);
});
