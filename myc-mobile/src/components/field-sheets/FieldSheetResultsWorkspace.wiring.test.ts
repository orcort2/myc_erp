import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item B): el botón "Guardar resultados" y la última
 * fila editable deben quedar visibles por encima del teclado -- verificación
 * de cableado por assert.match sobre el source, mismo patrón que
 * LabTechnicalCapture.wiring.test.ts (no hay framework de render RN aquí).
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './FieldSheetResultsWorkspace.tsx'),
  'utf8',
);

test('el botón de guardar vive DENTRO de KeyboardAvoidingView, no como hermano después de cerrarlo', () => {
  const kavStart = source.indexOf('<KeyboardAvoidingView');
  const kavEnd = source.indexOf('</KeyboardAvoidingView>');
  const kavBody = source.slice(kavStart, kavEnd);
  assert.match(kavBody, /styles\.footer/);
  assert.match(kavBody, /Guardar resultados/);
});

test('el teclado y el scroll principal usan el comportamiento nativo vigente', () => {
  assert.match(source, /<KeyboardAvoidingView/);
  assert.match(source, /automaticallyAdjustKeyboardInsets=\{Platform\.OS === 'ios'\}/);
  assert.match(source, /keyboardShouldPersistTaps="handled"/);
});

test('Next enfoca el siguiente input mediante inputRefs y focusNext', () => {
  assert.match(source, /const inputRefs = useRef\(new Map<string, TextInput \| null>\(\)\)/);
  assert.match(source, /function focusNext\(key: string\) \{\s*inputRefs\.current\.get\(key\)\?\.focus\(\);\s*\}/);
  assert.match(source, /onSubmitEditing=\{\(\) => \{\s*if \(nextKey\) \{\s*focusNext\(nextKey\);/);
});

test('no reintroduce desplazamiento manual incompatible con React Native/Fabric', () => {
  assert.doesNotMatch(source, /\bscrollCellIntoView\b/);
  assert.doesNotMatch(source, /\bmeasureLayout\s*\(/);
  assert.doesNotMatch(source, /\bfindNodeHandle\s*\(/);
});

test('interpreta el DSL genérico de headers agrupados, widths y row labels', () => {
  assert.match(source, /buildGroupedHeaderRows\(section\)/);
  assert.match(source, /declaredWidth\(\s*column\.width/);
  assert.match(source, /segment\.cell\.rowspan/);
  assert.match(source, /segment\.span/);
  assert.match(source, /rowLabel\(section, row\.row_number\)/);
  assert.doesNotMatch(source, /template_key\s*===/);
  assert.doesNotMatch(source, /organization_key\s*===/);
});
