import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const deliveryFlowPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../components/lab/LabDeliveryFlow.tsx',
);
const workOrdersPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../app/(technician)/work-orders.tsx',
);

const deliveryFlowSource = readFileSync(deliveryFlowPath, 'utf8');
const workOrdersSource = readFileSync(workOrdersPath, 'utf8');

test('LabDeliveryFlow nunca monta dos MobileSignaturePad al mismo tiempo', () => {
  // Cada <MobileSignaturePad ...> vive dentro de un bloque exclusivo por
  // paso (state.step === 'delivered_by_signature' / 'recipient_signature'),
  // así que sólo debe haber DOS apariciones en todo el archivo -- una por
  // paso -- nunca dos dentro del mismo bloque renderizado a la vez.
  const matches = deliveryFlowSource.match(/<MobileSignaturePad/g) ?? [];
  assert.equal(matches.length, 2, 'se esperan exactamente 2 <MobileSignaturePad>, una por paso de firma');

  const deliveredByBlockStart = deliveryFlowSource.indexOf("state.step === 'delivered_by_signature'");
  const recipientBlockStart = deliveryFlowSource.indexOf("state.step === 'recipient_signature'");
  assert.notEqual(deliveredByBlockStart, -1);
  assert.notEqual(recipientBlockStart, -1);
  assert.ok(deliveredByBlockStart < recipientBlockStart, 'el paso de quien entrega debe preceder al de quien recibe');

  const deliveredByBlock = deliveryFlowSource.slice(deliveredByBlockStart, recipientBlockStart);
  const recipientBlock = deliveryFlowSource.slice(recipientBlockStart);
  assert.equal((deliveredByBlock.match(/<MobileSignaturePad/g) ?? []).length, 1);
  assert.equal((recipientBlock.match(/<MobileSignaturePad/g) ?? []).length, 1);
});

test('el nombre de quien entrega viene de session/user, nunca de un input libre', () => {
  // deliveredByName se recibe como prop (de work-orders.tsx, ver siguiente
  // test) y se pinta readonly -- nunca pasa por un TextInput ni por
  // onChangeText.
  assert.match(deliveryFlowSource, /<Text style=\{styles\.readOnlyValue\}>\{deliveredByName\}<\/Text>/);
  assert.doesNotMatch(deliveryFlowSource, /onChangeText=\{[^}]*deliveredByName/);

  const paramsIndex = deliveryFlowSource.indexOf('deliveredByName: string');
  assert.notEqual(paramsIndex, -1, 'deliveredByName debe seguir declarado como prop tipada');
});

test('work-orders.tsx pasa deliveredByName desde user.full_name (identidad de sesión), no un valor capturado a mano', () => {
  const occurrences = workOrdersSource.match(/deliveredByName=\{user\.full_name\}/g) ?? [];
  assert.equal(occurrences.length, 2, 'los dos usos de LabDeliveryFlow (entrega normal y parcial) deben fijar deliveredByName=user.full_name');
});

test('LabDeliveryFlow nunca cierra el modal principal de la OT -- sólo notifica vía onCancel/onComplete', () => {
  assert.doesNotMatch(deliveryFlowSource, /setOpen\(/);
});

test('las cuatro parejas de acciones de LabDeliveryFlow (review, recipient, delivered_by_signature, recipient_signature) están dentro de OperationalActionStack', () => {
  // Cierre quirúrgico de espaciado (2026-09): antes, cada paso renderizaba
  // <PrimaryButton/><SecondaryButton/> consecutivos sin contenedor -- los
  // botones quedaban pegados verticalmente. Ahora las 4 parejas deben vivir
  // dentro de <OperationalActionStack>, que es quien resuelve la separación.
  const stackMatches = deliveryFlowSource.match(/<OperationalActionStack>/g) ?? [];
  assert.equal(stackMatches.length, 4, 'se esperan exactamente 4 <OperationalActionStack>, uno por paso');

  const stackBlocks = deliveryFlowSource.split('<OperationalActionStack>').slice(1);
  assert.equal(stackBlocks.length, 4);
  for (const block of stackBlocks) {
    const body = block.slice(0, block.indexOf('</OperationalActionStack>'));
    assert.match(body, /<PrimaryButton/, 'cada stack debe contener la acción principal del paso');
    assert.match(body, /<SecondaryButton/, 'cada stack debe contener la acción secundaria del paso');
  }
});

test('LabDeliveryFlow no introduce márgenes manuales entre las acciones apiladas', () => {
  // La separación pertenece al contenedor (OperationalActionStack), nunca a
  // un marginTop/marginBottom puesto a mano sobre PrimaryButton/SecondaryButton.
  assert.doesNotMatch(deliveryFlowSource, /<PrimaryButton[^>]*margin/);
  assert.doesNotMatch(deliveryFlowSource, /<SecondaryButton[^>]*margin/);
});

test('OperationalActionStack está importado desde los primitives compartidos, no reimplementado localmente', () => {
  assert.match(deliveryFlowSource, /import \{[^}]*OperationalActionStack[^}]*\} from '@\/src\/design\/primitives'/);
});
