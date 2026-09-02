import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX 2026-09 (item A): verificación de cableado del flujo de firmas
 * -- estados explícitos de envío (idle/saving/success/error) -- por el mismo
 * patrón de assert.match sobre el source ya usado en
 * LabTechnicalCapture.wiring.test.ts, ya que este proyecto no tiene un
 * framework de render de componentes RN.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './MobileSignatureFlow.tsx'),
  'utf8',
);

test('el botón de guardar muestra un estado "guardando" explícito, no sólo un spinner mudo', () => {
  assert.match(source, /Guardando firmas…/);
  assert.match(source, /submitting \? \(/);
});

test('el éxito se confirma con la respuesta autoritativa antes de avisarle al padre', () => {
  // onComplete se llama SÓLO después de mostrar la confirmación (dentro del
  // setTimeout de SUCCESS_CONFIRMATION_MS), nunca de forma síncrona apenas
  // resuelve onSubmit.
  assert.match(source, /setSuccess\(true\)/);
  assert.match(source, /successTimer\.current = setTimeout\(\(\) => \{\s*onComplete\(\);\s*\}, SUCCESS_CONFIRMATION_MS\)/);
  assert.match(source, /if \(success\) \{/);
});

test('un error de envío conserva la firma capturada -- nunca limpia clientCapture/technicianCapture', () => {
  const catchBlock = source.slice(source.indexOf('catch (submitError)'), source.indexOf('submissionLock.current.finish();\n    setSubmitting(false);\n  }'));
  assert.doesNotMatch(catchBlock, /onStateChange/);
  assert.doesNotMatch(catchBlock, /clientCapture: emptySignatureCapture/);
  assert.doesNotMatch(catchBlock, /technicianCapture: emptySignatureCapture/);
  assert.match(source, /setError\(submitError instanceof Error \? submitError\.message/);
});

test('el candado de envío sigue siendo la única guarda contra doble submit', () => {
  assert.match(source, /submissionLock\.current\.begin\(\)/);
  assert.match(source, /transitioningRef\.current = true/);
});

test('el timer de éxito se limpia al desmontar, igual que el de transición de paso', () => {
  assert.match(source, /if \(successTimer\.current\) clearTimeout\(successTimer\.current\)/);
});
