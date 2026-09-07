import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

// AJUSTE 2026-09: "Reabrir orden" (canReopenDirectly) se mueve del flujo
// operativo principal a Acciones administrativas, inmediatamente después de
// "Anular entrega". Reglas exactas:
// - Con Delivery activa (hasActiveDeliveryForCurrentWorkOrder === true):
//   "Anular entrega" visible, "Reabrir orden" visible pero disabled, con hint.
// - Sin Delivery activa: "Anular entrega" no visible (ya gateada por
//   activeDeliveryCount === 1), "Reabrir orden" enabled si canReopenDirectly.
// - Sin permiso de reapertura directa (canReopenDirectly === false): "Reabrir
//   orden" no se muestra en ningún lado.
// - OT cancelled: "Reabrir orden" no se muestra (ninguna reapertura aplica a
//   una OT cancelada).
// canReopenDirectly sigue siendo la única autoridad -- no se toca backend ni
// permisos. Wiring test de inspección estática, mismo estilo que
// lab-delivery-void-admin.wiring.test.ts: work-orders.tsx no tiene arnés de
// render en esta suite, así que la garantía viene de examinar las
// condiciones JSX reales.

const workOrdersPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../app/(technician)/work-orders.tsx',
);

const source = readFileSync(workOrdersPath, 'utf8');

test('"Reabrir orden" existe una sola vez en todo el árbol y vive en Acciones administrativas', () => {
  const matches = source.match(/label="Reabrir orden"/g) ?? [];
  assert.equal(matches.length, 1, 'debe existir exactamente un botón "Reabrir orden"');

  const adminSectionStart = source.indexOf('{workOrder && (canDelete || canReopenDirectly) && (');
  assert.notEqual(adminSectionStart, -1, 'la sección de Acciones administrativas debe seguir gateada por canDelete || canReopenDirectly');

  const buttonIndex = source.indexOf('label="Reabrir orden"');
  assert.ok(buttonIndex > adminSectionStart, '"Reabrir orden" debe estar dentro del bloque de Acciones administrativas');
});

test('"Reabrir orden" ya no vive en el flujo operativo principal (fuera de Acciones administrativas)', () => {
  const operationalStackStart = source.indexOf('{canDownloadLabPackages && workOrder.related_work_orders.length > 1');
  const dangerZoneStart = source.indexOf('{workOrder && (canDelete || canReopenDirectly) && (');
  assert.ok(operationalStackStart !== -1 && dangerZoneStart !== -1 && operationalStackStart < dangerZoneStart);

  const operationalBlock = source.slice(operationalStackStart, dangerZoneStart);
  assert.doesNotMatch(operationalBlock, /label="Reabrir orden"/, 'no debe quedar un botón directo de reapertura en el flujo operativo');
  assert.match(operationalBlock, /!canReopenDirectly && canCreateTickets/, '"Solicitar reapertura" (sin autoridad directa) sigue en el flujo operativo');
});

test('CASO 1 (hasActiveDeliveryForCurrentWorkOrder === true): "Anular entrega" visible, "Reabrir orden" justo debajo y disabled, con hint específico', () => {
  const anularIndex = source.indexOf('label="Anular entrega"');
  const reabrirGateIndex = source.lastIndexOf(
    "{workOrder.status !== 'cancelled' && canReopenDirectly && (",
    source.indexOf('label="Reabrir orden"'),
  );
  const reabrirButtonIndex = source.indexOf('label="Reabrir orden"');

  assert.ok(anularIndex !== -1 && reabrirGateIndex !== -1 && reabrirButtonIndex !== -1);
  assert.ok(anularIndex < reabrirGateIndex, '"Reabrir orden" debe quedar inmediatamente después de "Anular entrega"');
  assert.ok(reabrirGateIndex - anularIndex < 500, 'no debe haber otras acciones administrativas intercaladas entre "Anular entrega" y "Reabrir orden"');

  const buttonTagIndex = source.lastIndexOf('<AdministrativeButton', reabrirButtonIndex);
  const buttonBlock = source.slice(buttonTagIndex, source.indexOf(')}', reabrirButtonIndex));
  assert.match(buttonBlock, /disabled=\{busy \|\| hasActiveDeliveryForCurrentWorkOrder\}/, 'debe deshabilitarse mientras haya Delivery activa');

  const hintIndex = source.indexOf(
    "{workOrder.status !== 'cancelled' && canReopenDirectly && hasActiveDeliveryForCurrentWorkOrder && (",
  );
  assert.notEqual(hintIndex, -1);
  assert.ok(hintIndex > reabrirButtonIndex, 'el hint debe aparecer después del botón de "Reabrir orden"');
  const hintBlock = source.slice(hintIndex, source.indexOf(')}', hintIndex));
  assert.match(hintBlock, /Anula primero la entrega registrada para poder reabrir esta orden\./);
});

test('CASO 2 (sin Delivery activa): "Anular entrega" no se muestra y "Reabrir orden" queda enabled si canReopenDirectly', () => {
  const anularGate = source.match(/\{canVoidLabDelivery && activeDeliveryCount === 1 && \(/);
  assert.ok(anularGate, '"Anular entrega" sigue gateada por activeDeliveryCount === 1 (no aparece con 0 entregas activas)');

  const reabrirGateMatch = source.match(/\{workOrder\.status !== 'cancelled' && canReopenDirectly && \(\s*<OperationalActionStack>\s*<AdministrativeButton\s*disabled=\{busy \|\| hasActiveDeliveryForCurrentWorkOrder\}/);
  assert.ok(reabrirGateMatch, '"Reabrir orden" no debe depender de que exista una Delivery activa para habilitarse, sólo de canReopenDirectly y no estar bloqueada por una activa');
});

test('CASO 3 (sin permiso de reapertura directa): "Reabrir orden" no se muestra en ningún lado', () => {
  const reabrirButtonIndex = source.indexOf('label="Reabrir orden"');
  const gateStart = source.lastIndexOf("{workOrder.status !== 'cancelled' && canReopenDirectly && (", reabrirButtonIndex);
  assert.notEqual(gateStart, -1);
  const gateToButton = source.slice(gateStart, reabrirButtonIndex).replace(/\s+/g, ' ').trim();
  assert.equal(
    gateToButton,
    "{workOrder.status !== 'cancelled' && canReopenDirectly && ( <OperationalActionStack> <AdministrativeButton disabled={busy || hasActiveDeliveryForCurrentWorkOrder} icon=\"lock-open-outline\"",
    'entre el gate y el botón sólo debe haber el wrapper directo, sin ternario ni fallback que muestre "Reabrir orden" sin canReopenDirectly',
  );

  // El fallback para quien no tiene autoridad directa es "Solicitar reapertura", nunca "Reabrir orden".
  assert.doesNotMatch(source, /canCreateTickets\s*\?\s*\(\s*<AdministrativeButton[^>]*label="Reabrir orden"/);
});

test('CASO 4 (OT cancelled): "Reabrir orden" no se muestra', () => {
  const reabrirButtonIndex = source.indexOf('label="Reabrir orden"');
  const gateStart = source.lastIndexOf("{workOrder.status !== 'cancelled' && canReopenDirectly && (", reabrirButtonIndex);
  assert.notEqual(gateStart, -1, 'el gate debe excluir explícitamente status === \'cancelled\'');
  const gate = source.slice(gateStart, reabrirButtonIndex);
  assert.match(gate, /workOrder\.status !== 'cancelled'/);
});

test('canReopenDirectly sigue siendo la única autoridad -- Acciones administrativas no se oculta para quien reabre pero no puede eliminar', () => {
  assert.match(source, /\{workOrder && \(canDelete \|\| canReopenDirectly\) && \(/, 'la sección debe seguir visible para canReopenDirectly aunque no haya canDelete, o "Reabrir orden" desaparecería para ese rol');

  const deleteBlockIndex = source.indexOf('label="Eliminar orden de trabajo"');
  const deleteGateIndex = source.lastIndexOf('{canDelete && <>', deleteBlockIndex);
  assert.notEqual(deleteGateIndex, -1, 'Eliminar sigue exigiendo canDelete explícitamente, ahora que el wrapper externo ya no lo garantiza por sí solo');
});

test('no se tocó el backend: reopen_direct sigue siendo el único modo de ticket usado por "Reabrir orden"', () => {
  const buttonIndex = source.indexOf('label="Reabrir orden"');
  const onPressBlock = source.slice(buttonIndex, source.indexOf(')}', buttonIndex));
  assert.match(onPressBlock, /setTicketDialogMode\('reopen_direct'\)/);
  assert.match(onPressBlock, /setReopenSignaturePolicy\('preserve'\)/);
  assert.match(onPressBlock, /setTicketOpen\(true\)/);
});
