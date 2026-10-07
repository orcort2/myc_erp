import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { createLifecycleHarness, type LifecycleHarness } from './support/lifecycle-harness';
import {
  freshInstallationReport,
  generalServiceEquipmentFixture,
  installationProjection,
  workOrderFixture,
} from './support/lab-fixtures';

// SG-4F: Servicio General entrega con el LabDeliveryFlow existente (las firmas
// finales viven en LabWorkOrderDelivery), no con MobileSignatureFlow.

const CONFORMITY = 'El cliente confirma que el equipo o producto fue instalado, se verificó su funcionamiento y se recibe de conformidad con el servicio realizado.';
const DELIVERY_PATH = '/mobile/v1/technician/lab-work-orders/72/delivery';
const SIGNED = { delivery_method: 'direct', delivered_by_signature_data_url: 'data:image/png;base64,AA==', recipient_name: 'Persona Recibe', recipient_signature_data_url: 'data:image/png;base64,AA==', notes: null };

function pending(equipmentId: number, instrument: string, overrides: Record<string, unknown> = {}) {
  return {
    work_order_id: 72, work_order_folio: 6072, equipment_id: equipmentId, position: equipmentId - 288, instrument, brand: 'MYC',
    identification: 'ID', serial_number: `S${equipmentId}`, certificate_folio: null,
    delivery_eligible: true, delivery_blocked_reason: null, technical_report_folio: 'MYC-IN10-26-0001', client_conformity_text: CONFORMITY,
    ...overrides,
  };
}

function statusOf(pendingItems: Record<string, unknown>[], extra: Record<string, unknown> = {}) {
  return {
    root_work_order_id: 72, total_equipment: pendingItems.length, delivered_equipment: 0, pending_equipment: pendingItems,
    exhibitions: [], group_complete: false, final_receipt_available: false, final_receipt_version: null,
    pending_partial_delivery_ticket_id: null, ...extra,
  };
}

async function openGeneralService(options: { reportStatus?: string; delivery?: ReturnType<typeof statusOf>; orderStatus?: string } = {}): Promise<LifecycleHarness> {
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({
    operational_category: 'general_service', status: options.orderStatus ?? 'in_progress',
    equipment: [generalServiceEquipmentFixture(installationProjection({ technical_report_status: options.reportStatus ?? 'ready_for_signatures' }))],
  });
  h.env.report = freshInstallationReport({ status: options.reportStatus ?? 'ready_for_signatures' });
  h.env.deliveryStatus = options.delivery ?? statusOf([pending(289, 'Báscula')]);
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  return h;
}

const deliveryPosts = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'POST' && call.path === DELIVERY_PATH);

test('4F: con el reporte listo se muestra "Proceder a entrega" y el reporte se rotula LISTO PARA ENTREGA', async () => {
  const h = await openGeneralService();
  assert.ok(h.text().includes('Proceder a entrega'));
  assert.ok(h.text().includes('LISTO PARA ENTREGA'));
  assert.equal(h.registry.get('Proceder a entrega')!.disabled, false);
  assert.ok(h.probe.requests.includes(`GET ${DELIVERY_PATH}`), 'consulta la elegibilidad antes de cerrar la OT');
});

test('4F: con reportes en captura la entrega no se habilita y se explica qué falta', async () => {
  for (const reportStatus of ['draft', 'in_progress']) {
    const h = await openGeneralService({
      reportStatus,
      delivery: statusOf([pending(289, 'Báscula', { delivery_eligible: false, delivery_blocked_reason: 'El reporte técnico aún no está finalizado', technical_report_folio: null, client_conformity_text: null })]),
    });
    assert.equal(h.registry.get('Proceder a entrega')!.disabled, true, reportStatus);
    assert.ok(h.text().includes('Pendientes de finalizar: Báscula'), reportStatus);
    assert.ok(!h.registry.has('LabDeliveryFlow'));
  }
});

test('4F: abre LabDeliveryFlow (no MobileSignatureFlow) con los equipos y la conformidad del reporte', async () => {
  const h = await openGeneralService();
  await h.press('Proceder a entrega');
  const flow = h.registry.get('LabDeliveryFlow');
  assert.ok(flow, 'se reutiliza el wizard de entrega');
  assert.ok(!h.registry.has('MobileSignatureFlow'), 'no se abre el flujo de firma de recepción/cierre');
  assert.equal(flow.isPartial, false);
  assert.equal(flow.deliveredByName, 'Tec');
  assert.equal(flow.nextExhibitionNumber, 1);
  assert.deepEqual(flow.equipment.map((item: { equipment_id: number }) => item.equipment_id), [289]);
  assert.equal(flow.equipment[0].client_conformity_text, CONFORMITY, 'la declaración viene del backend');
});

test('4F: cancelar no confirma la entrega y vuelve al reporte', async () => {
  const h = await openGeneralService();
  await h.press('Proceder a entrega');
  await h.act(async () => { h.registry.get('LabDeliveryFlow')!.onCancel(); });
  assert.equal(deliveryPosts(h).length, 0);
  assert.ok(h.text().includes('Proceder a entrega'));
});

test('4F: confirmar envía las firmas de entrega/receptor a /delivery, refresca y el equipo deja de estar pendiente', async () => {
  const h = await openGeneralService();
  await h.press('Proceder a entrega');
  const flow = h.registry.get('LabDeliveryFlow')!;
  const requestsBefore = h.probe.requests.length;
  await h.act(async () => { await flow.onSubmit(SIGNED); });
  await h.flush();
  const [post] = deliveryPosts(h);
  assert.equal(deliveryPosts(h).length, 1);
  assert.deepEqual(post.body, SIGNED);
  assert.ok(!h.probe.calls.some((call) => /\/technical-report\/sign$/.test(call.path)), 'las firmas no se duplican en el reporte');
  const after = h.probe.requests.slice(requestsBefore);
  assert.ok(after.includes(`GET ${DELIVERY_PATH}`), 'recarga el estado de entrega');
  assert.ok(after.some((request) => /^GET .*lab-work-orders/.test(request)), 'refresca la OT/listado');
  assert.ok(h.probe.published.some((event) => event.event_type === 'work_order.delivery_completed'));
  await h.act(async () => { h.registry.get('LabDeliveryFlow')!.onComplete(); });
  const text = h.text();
  assert.ok(text.includes('Entrega completada'));
  assert.ok(!text.includes('Proceder a entrega'));
});

test('4F: un rechazo del backend no cierra el flujo ni marca entregado', async () => {
  const h = await openGeneralService();
  h.env.deliveryError = 'El reporte técnico aún no está finalizado';
  await h.press('Proceder a entrega');
  const flow = h.registry.get('LabDeliveryFlow')!;
  await assert.rejects(() => flow.onSubmit(SIGNED));
  assert.ok(h.probe.log.includes('Alert:No fue posible registrar la entrega'));
  assert.ok(h.registry.has('LabDeliveryFlow'));
});

test('4F: entrega parcial: lo entregado no vuelve a pendientes y lo restante sigue entregable', async () => {
  const h = await openGeneralService({
    delivery: statusOf([pending(290, 'Compresor', { technical_report_folio: 'MYC-IN10-26-0002' })], {
      total_equipment: 2, delivered_equipment: 1,
      exhibitions: [{ id: 800, exhibition_number: 1, delivery_type: 'partial', status: 'completed', delivered_at: '2026-10-08T17:00:00+00:00', recipient_name: 'Persona Recibe', items: [] }],
    }),
  });
  assert.ok(h.text().includes('1 de 2 equipos entregados'));
  await h.press('Proceder a entrega');
  const flow = h.registry.get('LabDeliveryFlow')!;
  assert.deepEqual(flow.equipment.map((item: { equipment_id: number }) => item.equipment_id), [290]);
  assert.equal(flow.nextExhibitionNumber, 2);
});

test('4F: con equipos mezclados (uno listo, otro en captura) la entrega completa queda bloqueada y la parcial sólo ofrece los listos', async () => {
  const h = await openGeneralService({
    delivery: statusOf([
      pending(289, 'Báscula'),
      pending(290, 'Compresor', { delivery_eligible: false, delivery_blocked_reason: 'El reporte técnico aún no está finalizado', technical_report_folio: null, client_conformity_text: null }),
    ]),
  });
  assert.equal(h.registry.get('Proceder a entrega')!.disabled, true);
  assert.ok(h.text().includes('Pendientes de finalizar: Compresor'));
  await h.press('Solicitar entrega parcial');
  const request = h.registry.get('LabPartialDeliveryRequest');
  assert.ok(request, 'abre la solicitud parcial existente');
  assert.deepEqual(request.pendingEquipment.map((item: { equipment_id: number }) => item.equipment_id), [289]);
});

// --------------------------------------------------------------- cierre

const completePosts = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'POST' && /\/complete(\/individual)?(\?.*)?$/.test(call.path));
const delivered = (items: Record<string, unknown>[] = []) => statusOf(items, {
  delivered_equipment: 1, group_complete: items.length === 0,
  exhibitions: [{ id: 800, exhibition_number: 1, delivery_type: 'full', status: 'completed', delivered_at: '2026-10-08T17:00:00+00:00', recipient_name: 'Persona Recibe', items: [{ id: 1, work_order_id: 72, work_order_folio: 6072, equipment_id: 289 }] }],
});

test('4F: Servicio General entregado con reporte ready_for_signatures no ofrece cierre ni llama /complete', async () => {
  const h = await openGeneralService({ delivery: delivered() });
  const text = h.text();
  assert.ok(!text.includes('Continuar a cierre'));
  assert.ok(text.includes('La entrega está registrada. Falta generar el reporte técnico final.'));
  assert.equal(completePosts(h).length, 0);
  assert.ok(!h.probe.requests.some((request) => /\/complete/.test(request)));
});

test('4F: Servicio General sin entrega conserva la acción de entrega y no muestra el estado documental', async () => {
  const h = await openGeneralService();
  assert.ok(h.text().includes('Proceder a entrega'));
  assert.ok(!h.text().includes('Falta generar el reporte técnico final'));
});

test('4F: calibración completed conserva "Continuar a cierre" y su cierre histórico', async () => {
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({ status: 'in_progress', equipment: [] });
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  assert.ok(h.text().includes('Continuar a cierre'), 'calibración en captura técnica');
  assert.ok(!h.text().includes('Falta generar el reporte técnico final'));
  await h.press('Continuar a cierre');
  assert.ok(h.text().includes('Confirmar cierre'));
});

// --------------------------------------------------------------- calibración

test('4F: calibración conserva su entrega: sólo con la OT cerrada, sin "Proceder a entrega" ni reglas de reporte', async () => {
  const open = await createLifecycleHarness();
  open.env.detail = workOrderFixture({ status: 'received_signed' });
  open.env.deliveryStatus = statusOf([pending(289, 'Manómetro', { delivery_eligible: undefined, technical_report_folio: null, client_conformity_text: null })]);
  open.env.params = { workOrderId: '72' };
  await open.mount();
  await open.flush();
  assert.ok(!open.probe.requests.includes(`GET ${DELIVERY_PATH}`), 'no consulta entrega antes del cierre');
  assert.ok(!open.text().includes('Proceder a entrega'));

  const closed = await createLifecycleHarness();
  closed.env.detail = workOrderFixture({ status: 'completed' });
  closed.env.deliveryStatus = statusOf([pending(289, 'Manómetro', { delivery_eligible: undefined, technical_report_folio: null, client_conformity_text: null })]);
  closed.env.params = { workOrderId: '72' };
  await closed.mount();
  await closed.flush();
  assert.ok(closed.text().includes('Registrar entrega'));
  assert.ok(!closed.text().includes('Proceder a entrega'));
  await closed.press('Registrar entrega');
  const flow = closed.registry.get('LabDeliveryFlow')!;
  assert.equal(flow.equipment.length, 1);
  assert.equal(flow.equipment[0].client_conformity_text, null);
});

// --------------------------------------------------------------- wizard (fuente)

const here = dirname(fileURLToPath(import.meta.url));
const flowSource = readFileSync(resolve(here, '../components/lab/LabDeliveryFlow.tsx'), 'utf8');

test('4F: la conformidad se presenta en el paso del receptor, antes de confirmar', () => {
  const recipientBlock = flowSource.slice(flowSource.indexOf("state.step === 'recipient_signature'"));
  assert.ok(recipientBlock.indexOf('conformityTexts') > recipientBlock.indexOf('<MobileSignaturePad'), 'el texto acompaña la firma del receptor');
  assert.ok(recipientBlock.indexOf('conformityTexts') < recipientBlock.indexOf('Confirmar entrega'), 'y precede a la confirmación');
  assert.match(flowSource, /deliveryConformityTexts\(equipment\)/);
});

test('4F: salir con una firma capturada pide confirmación; sin firma cancela directo', () => {
  assert.match(flowSource, /hasUnsubmittedSignature\(state\)/);
  assert.match(flowSource, /¿Descartar las firmas capturadas\?/);
  assert.equal((flowSource.match(/onPress=\{requestCancel\}/g) ?? []).length, 3, 'revisión, firma de entrega y firma de receptor cancelan con la misma guarda');
  assert.doesNotMatch(flowSource, /onPress=\{onCancel\}/);
});
