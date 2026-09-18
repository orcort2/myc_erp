import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * PENDIENTE 4 (encargo de corrección LAB): "Completar cambios" -- cierra la
 * sesión de corrección de una OT reabierta consumiendo
 * pending_signature_review (ya fresco en toda respuesta de OT) y llamando al
 * endpoint autoritativo POST .../complete-corrections. Mismo patrón
 * assert.match sobre el source que el resto de wiring-tests.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
  'utf8',
);

test('"Completar cambios" se muestra con el mismo gate que "Corregir datos de la orden" (wasReopened && editable)', () => {
  const block = source.slice(
    source.indexOf("{wasReopened(workOrder) && editable && (\n                    <SecondaryButton icon=\"pencil-outline\" label=\"Corregir datos de la orden\""),
    source.indexOf('<View style={styles.sectionRow}><Text style={styles.sectionTitle}>Equipos</Text>'),
  );
  assert.match(block, /\{wasReopened\(workOrder\) && editable && \(\s*<PrimaryButton/);
  assert.match(block, /label="Completar cambios"/);
  assert.match(block, /onPress=\{confirmCompleteCorrections\}/);
});

test('confirmCompleteCorrections consulta pending_signature_review.requires_new_signature antes de completar', () => {
  const fn = source.slice(
    source.indexOf('function confirmCompleteCorrections'),
    source.indexOf('async function completeCorrections'),
  );
  assert.match(fn, /const review = workOrder\.pending_signature_review;/);
  assert.match(fn, /if \(review\.requires_new_signature\) \{/);
  assert.match(fn, /describePendingSignatureReviewFields\(review, workOrder\.equipment\)/);
});

test('el warning de firma requerida se muestra ANTES de completar y exige confirmación explícita -- nunca completa a ciegas', () => {
  const fn = source.slice(
    source.indexOf('function confirmCompleteCorrections'),
    source.indexOf('async function completeCorrections'),
  );
  const warningBranch = fn.slice(fn.indexOf('if (review.requires_new_signature) {'));
  assert.match(warningBranch, /'Se requiere una nueva firma'/);
  assert.match(warningBranch, /\{ text: 'Cancelar', style: 'cancel' \}/);
  assert.match(warningBranch, /onPress: \(\) => \{ void completeCorrections\(\); \}/);
});

test('sin cambios sensibles, igual pide confirmación explícita (nunca completa sin que el técnico decida)', () => {
  const fn = source.slice(
    source.indexOf('function confirmCompleteCorrections'),
    source.indexOf('async function completeCorrections'),
  );
  const noopBranch = fn.slice(fn.lastIndexOf('Alert.alert(\n      \'Completar cambios\''));
  assert.match(noopBranch, /'Completar cambios'/);
  assert.match(noopBranch, /\{ text: 'Cancelar', style: 'cancel' \}/);
  assert.match(noopBranch, /onPress: \(\) => \{ void completeCorrections\(\); \}/);
});

test('completeCorrections llama al endpoint autoritativo y reemplaza la OT completa con la respuesta -- nunca parcha localmente', () => {
  const fn = source.slice(
    source.indexOf('async function completeCorrections'),
    source.indexOf('async function addAdditional'),
  );
  assert.match(fn, /\/mobile\/v1\/technician\/lab-work-orders\/\$\{workOrder\.id\}\/complete-corrections/);
  assert.match(fn, /method:\s*'POST'/);
  assert.match(fn, /setWorkOrder\(detail\)/);
  assert.match(fn, /publishLocalChange\(\{ event_type: detail\.signature_required \? 'ticket\.signature_required' : 'work_order\.updated'/);
});

test('el tipo LabWorkOrder declara pending_signature_review tal cual backend lo devuelve, sin campos opcionales que oculten un olvido', () => {
  const types = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '../types/lab-work-order.ts'),
    'utf8',
  );
  assert.match(types, /pending_signature_review: \{\s*sensitive_fields: string\[\];\s*requires_new_signature: boolean;\s*\};/);
});
