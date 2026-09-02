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

test('cada celda enfocada se desplaza a la vista de forma genérica, sin offsets fijos por dispositivo', () => {
  assert.match(source, /onFocus=\{\(\) => scrollCellIntoView\(cellKey\)\}/);
  assert.match(source, /input\.measureLayout\(/);
  // Nada de constantes de alto de teclado por plataforma/dispositivo.
  assert.doesNotMatch(source, /keyboardVerticalOffset=\{\d/);
});

test('el ScrollView de contenido expone el ref que scrollCellIntoView necesita', () => {
  assert.match(source, /ref=\{scrollViewRef\}/);
});
