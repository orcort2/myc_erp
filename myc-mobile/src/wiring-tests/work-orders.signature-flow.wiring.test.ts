import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item A): el desmontaje de MobileSignatureFlow lo decide
 * el propio componente (tras mostrar su confirmación de éxito) vía
 * onComplete -- applySignatures ya no lo hace de forma síncrona apenas
 * responde el backend.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
  'utf8',
);

test('MobileSignatureFlow recibe onComplete para limpiar el estado tras su propia confirmación', () => {
  assert.match(source, /onComplete=\{\(\) => \{ setSignatureFlowState\(null\); setSignatureDrawing\(false\); \}\}/);
});

test('applySignatures ya no limpia signatureFlowState/signatureDrawing en el camino de éxito', () => {
  const start = source.indexOf('async function applySignatures');
  const end = source.indexOf('\n  // Cierre UX 2026-09: cerrar con hojas en borrador', start);
  assert.ok(start > -1 && end > start, 'no se encontró el cuerpo de applySignatures');
  const body = source.slice(start, end);
  assert.match(body, /setWorkOrder\(detail\)/);
  assert.doesNotMatch(body, /setWorkOrder\(detail\);\s*setSignatureFlowState\(null\)/);
});

test('el early-return por cambio de contexto sigue limpiando el estado de inmediato (no hay éxito que confirmar)', () => {
  assert.match(
    source,
    /labClosureContextId\(workOrder, closureScope\) !== capturedContextId\) \{\s*setSignatureFlowState\(null\);\s*setSignatureDrawing\(false\);/,
  );
});
