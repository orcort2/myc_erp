import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

// AJUSTE: anulación administrativa de entrega -- regla exacta:
// - activeDeliveryCount === 1: "Anular entrega" SOLO en Acciones
//   administrativas; nunca "Anular esta exhibición" en historial.
// - activeDeliveryCount > 1: "Anular esta exhibición" SOLO en historial, una
//   por exhibición vigente relevante; nunca "Anular entrega" administrativa.
// - activeDeliveryCount === 0: ninguna acción de anulación.
// Estos son wiring tests de inspección estática (mismo estilo que
// lab-delivery-flow.wiring.test.ts): work-orders.tsx es un componente React
// Native grande sin arnés de render en esta suite, así que la garantía viene
// de examinar las condiciones JSX reales, no de montar el componente.

const workOrdersPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../app/(technician)/work-orders.tsx',
);

const source = readFileSync(workOrdersPath, 'utf8');

test('activeDeliveriesForCurrentWorkOrder se deriva de exhibitions completed con al menos un item de la OT actual', () => {
  const derivationStart = source.indexOf('const activeDeliveriesForCurrentWorkOrder = useMemo(');
  assert.notEqual(derivationStart, -1);
  const derivationBlock = source.slice(derivationStart, source.indexOf('const activeDeliveryCount', derivationStart));
  assert.match(derivationBlock, /exhibition\.status === 'completed'/);
  assert.match(derivationBlock, /exhibition\.items\.some\(\s*\(item\) => item\.work_order_id === workOrder\?\.id\s*\)/);

  assert.match(source, /const activeDeliveryCount = activeDeliveriesForCurrentWorkOrder\.length;/);
  assert.match(source, /const hasActiveDeliveryForCurrentWorkOrder = activeDeliveryCount > 0;/);
});

test('CASO 1 (activeDeliveryCount === 1): "Anular entrega" vive únicamente en Acciones administrativas, gateada por canVoidLabDelivery && activeDeliveryCount === 1', () => {
  const matches = source.match(/label="Anular entrega"/g) ?? [];
  assert.equal(matches.length, 1, 'debe existir exactamente un botón "Anular entrega"');

  const buttonIndex = source.indexOf('label="Anular entrega"');
  const gateStart = source.lastIndexOf('{canVoidLabDelivery && activeDeliveryCount === 1 && (', buttonIndex);
  assert.notEqual(gateStart, -1, '"Anular entrega" debe estar gateada exactamente por canVoidLabDelivery && activeDeliveryCount === 1');
  assert.ok(gateStart < buttonIndex && buttonIndex - gateStart < 400, 'el gate debe envolver directamente al botón, sin lógica intermedia');

  const onPressBlock = source.slice(buttonIndex, source.indexOf(')}', buttonIndex));
  assert.match(onPressBlock, /setVoidingDelivery\(activeDeliveriesForCurrentWorkOrder\[0\]\)/, 'debe tomar directamente la única entrega vigente, sin selector');
  assert.match(onPressBlock, /setTicketDialogMode\('void_delivery'\)/);
  assert.match(onPressBlock, /setTicketOpen\(true\)/);
});

test('CASO 2 (activeDeliveryCount > 1): "Anular esta exhibición" vive únicamente en el historial, una por exhibición, nunca sólo por status completed', () => {
  const matches = source.match(/label="Anular esta exhibición"/g) ?? [];
  assert.equal(matches.length, 1, 'debe existir exactamente un botón "Anular esta exhibición" (uno por iteración del historial)');

  const buttonIndex = source.indexOf('label="Anular esta exhibición"');
  const conditionStart = source.lastIndexOf('{activeDeliveryCount > 1 && exhibition.status', buttonIndex);
  assert.notEqual(conditionStart, -1);
  const condition = source.slice(conditionStart, buttonIndex);
  assert.match(condition, /activeDeliveryCount > 1/, 'nunca debe depender solamente de exhibition.status === \'completed\'');
  assert.match(condition, /exhibition\.status === 'completed'/);
  assert.match(condition, /canVoidLabDelivery/);
  assert.match(condition, /exhibition\.items\.some\(\(item\) => item\.work_order_id === workOrder\.id\)/, 'una exhibición que no trae items de la OT actual no debe ofrecer anulación desde aquí');
});

test('NO DUPLICAR: los gates de "Anular entrega" (=== 1) y "Anular esta exhibición" (> 1) son mutuamente excluyentes por construcción', () => {
  // No hace falta ejecutar el componente: activeDeliveryCount no puede ser
  // simultáneamente === 1 y > 1, así que basta con que ambos gates usen
  // exactamente esos operadores sobre la misma variable derivada.
  assert.match(source, /canVoidLabDelivery && activeDeliveryCount === 1/);
  assert.match(source, /activeDeliveryCount > 1 && exhibition\.status === 'completed' && canVoidLabDelivery/);
});

test('CASO 3 (activeDeliveryCount === 0): Cancelar y Eliminar dejan de estar bloqueados por Delivery, vía hasActiveDeliveryForCurrentWorkOrder', () => {
  const cancelIndex = source.indexOf('label="Cancelar y conservar OT"');
  const cancelButtonBlock = source.slice(source.lastIndexOf('<AdministrativeButton', cancelIndex), cancelIndex);
  assert.match(cancelButtonBlock, /disabled=\{busy \|\| deleting \|\| hasActiveDeliveryForCurrentWorkOrder\}/);

  const deleteIndex = source.indexOf('label="Eliminar orden de trabajo"');
  const deleteButtonBlock = source.slice(source.lastIndexOf('<DangerButton', deleteIndex), deleteIndex);
  assert.match(deleteButtonBlock, /disabled=\{busy \|\| deleting \|\| hasActiveDeliveryForCurrentWorkOrder\}/);

  // El texto informativo sólo debe pintarse cuando efectivamente hay bloqueo.
  const noticeIndex = source.indexOf('{hasActiveDeliveryForCurrentWorkOrder && (');
  assert.notEqual(noticeIndex, -1);
  assert.ok(noticeIndex < cancelIndex, 'el aviso debe preceder a los botones que bloquea');
  const noticeBlock = source.slice(noticeIndex, cancelIndex);
  assert.match(noticeBlock, /Anula primero la entrega física vigente de esta OT para habilitar cancelación o eliminación\./);
  assert.match(noticeBlock, /Anula primero las entregas físicas vigentes de esta OT para habilitar cancelación o eliminación\./);
  assert.match(noticeBlock, /activeDeliveryCount > 1\s*\n?\s*\?/, 'debe distinguir singular/plural según activeDeliveryCount');
});

test('no se implementó batch void, selector administrativo adicional ni "anular todas"', () => {
  assert.doesNotMatch(source, /Anular entregas \(/);
  assert.doesNotMatch(source, /anular todas/i);
  assert.doesNotMatch(source, /batchVoid|voidAllDeliveries/);
});

test('exhibición compartida entre OT: el modal void_delivery advierte con los folios de las OT hermanas antes de confirmar', () => {
  const warningStart = source.indexOf("ticketDialogMode === 'void_delivery' && voidingDelivery && (() => {");
  assert.notEqual(warningStart, -1);
  const warningBlock = source.slice(warningStart, source.indexOf('reopen_direct', warningStart));

  assert.match(warningBlock, /item\.work_order_id !== workOrder\?\.id/, 'debe filtrar exactamente los items que NO pertenecen a la OT actual');
  assert.match(warningBlock, /work_order_folio/, 'la advertencia debe listar folios de OT hermanas, no ids internos');
  assert.match(warningBlock, /<AlertBanner tone="warning">/);
  assert.match(warningBlock, /Esta exhibición también contiene equipos de las OT/);
  assert.match(warningBlock, /volverán también a pendientes de entrega/);
  assert.match(warningBlock, /if \(!siblingFolios\.length\) return null;/, 'sin folios hermanos, no debe mostrarse ninguna advertencia');
});

test('la anulación sigue siendo de la exhibición completa -- no hay void a nivel de item', () => {
  assert.doesNotMatch(source, /voidDeliveryItem|itemLevelVoid|void.*item.*id/i);
  // voidDelivery(id, reason) sólo recibe el id de la entrega/exhibición.
  assert.match(source, /async function voidDelivery\(deliveryId: number, reason: string\)/);
});
