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
import { describeGeneralServiceClosure } from '../services/technical-report';

// SG-4H: el cierre de Servicio General lo habilita el backend (OT en
// ready_to_close); /complete es el mismo endpoint de siempre.

const exhibition = (equipmentIds: number[]) => ({
  id: 800, exhibition_number: 1, delivery_type: 'full', status: 'completed', delivered_at: '2026-10-08T17:00:00+00:00', recipient_name: 'Persona Recibe',
  items: equipmentIds.map((id) => ({ id, work_order_id: 72, work_order_folio: 6072, equipment_id: id })),
});

const statusFor = (deliveredIds: number[], total: number) => ({
  root_work_order_id: 72, total_equipment: total, delivered_equipment: deliveredIds.length, pending_equipment: [],
  exhibitions: deliveredIds.length ? [exhibition(deliveredIds)] : [], group_complete: deliveredIds.length === total,
  final_receipt_available: false, final_receipt_version: null, pending_partial_delivery_ticket_id: null,
});

type Equipment = { id: number; reportStatus: string };

async function open(options: { orderStatus: string; equipment?: Equipment[]; delivered?: number[] }): Promise<LifecycleHarness> {
  const equipment = options.equipment ?? [{ id: 289, reportStatus: 'completed' }];
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({
    operational_category: 'general_service', status: options.orderStatus,
    equipment: equipment.map((item) => generalServiceEquipmentFixture(installationProjection({ technical_report_status: item.reportStatus }), )).map((item, index) => ({
      ...item, id: equipment[index].id, position: index + 1,
    })),
  });
  h.env.report = freshInstallationReport({ status: equipment[0].reportStatus });
  h.env.deliveryStatus = statusFor(options.delivered ?? equipment.map((item) => item.id), equipment.length);
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  return h;
}

const completePosts = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'POST' && /\/complete(\/individual)?(\?.*)?$/.test(call.path));
const toTechnicalStep = async (h: LifecycleHarness) => { if (h.registry.has('Revisar captura técnica') && !h.text().includes('CAPTURA TÉCNICA')) await h.press('Revisar captura técnica'); };

test('4H: con la OT en ready_to_close el cierre está disponible y el mensaje lo confirma', async () => {
  const h = await open({ orderStatus: 'ready_to_close' });
  assert.ok(h.text().includes('Cerrar OT 6072'), 'el cierre lo habilita el estado del backend');
  await toTechnicalStep(h);
  assert.ok(h.text().includes('La entrega y documentación técnica están completas.'));
  assert.ok(h.text().includes('Continuar a cierre'));
});

test('4H: cerrar llama /complete una vez, refresca y la OT queda CERRADA', async () => {
  const h = await open({ orderStatus: 'ready_to_close' });
  const requestsBefore = h.probe.requests.length;
  await h.press('Cerrar OT 6072');
  await h.flush();
  assert.equal(completePosts(h).length, 1);
  assert.ok(/\/lab-work-orders\/72\/complete$/.test(completePosts(h)[0].path), 'el mismo endpoint histórico');
  assert.ok(!h.probe.requests.some((request) => /complete-general|general-service/.test(request)));
  assert.ok(h.probe.requests.slice(requestsBefore).some((request) => /^GET .*lab-work-orders/.test(request)), 'refresca el listado');
  assert.ok(h.text().includes('CERRADA'));
  assert.ok(h.probe.published.some((event) => event.event_type === 'work_order.completed'));
});

test('4H: reporte completo pero sin entrega registrada -> mensaje de entrega y sin cierre', async () => {
  const h = await open({ orderStatus: 'in_progress', delivered: [] });
  const text = h.text();
  assert.ok(text.includes('El reporte técnico está completo, pero falta registrar la entrega.'));
  assert.ok(!text.includes('Continuar a cierre'));
  assert.equal(completePosts(h).length, 0);
});

test('4H: entrega registrada pero reporte final pendiente -> mensaje y sin cierre', async () => {
  const h = await open({ orderStatus: 'in_progress', equipment: [{ id: 289, reportStatus: 'ready_for_signatures' }] });
  assert.ok(h.text().includes('La entrega está registrada. Falta generar el reporte técnico final.'));
  assert.ok(!h.text().includes('Continuar a cierre'));
});

test('4H: con varios equipos no se habilita el cierre hasta que el backend marque ready_to_close', async () => {
  const h = await open({
    orderStatus: 'in_progress',
    equipment: [{ id: 289, reportStatus: 'completed' }, { id: 290, reportStatus: 'in_progress' }, { id: 291, reportStatus: 'completed' }],
    delivered: [289, 291],
  });
  assert.ok(!h.text().includes('Continuar a cierre'));
  assert.ok(!h.text().includes('Cerrar OT 6072'));
  assert.equal(completePosts(h).length, 0);
});

test('4H: el contador X/Y del listado es el del backend', async () => {
  const h = await createLifecycleHarness();
  h.env.list = [{
    id: 72, folio: 6072, root_work_order_id: 72, sequence_number: 1, client_name: 'Cliente SG', reception_date: '2026-10-07', status: 'in_progress',
    workflow_mode: 'group', operational_category: 'general_service', equipment_count: 3, completed_equipment_count: 2, created_at: '2026-10-07T00:00:00Z',
    revision_number: 1, signature_required: false,
  }];
  await h.mount();
  await h.flush();
  assert.ok(h.text().includes('2/3 equipos'));
});

test('4H: la pantalla de Servicio General no usa terminología de hojas de campo', async () => {
  const h = await open({ orderStatus: 'in_progress', equipment: [{ id: 289, reportStatus: 'ready_for_signatures' }] });
  const text = h.text().toLowerCase();
  assert.ok(!text.includes('hoja') && !text.includes('fieldsheet') && !text.includes('myca') && !text.includes('myct'));
});

test('4H: describeGeneralServiceClosure sólo habilita el cierre desde el estado del backend', () => {
  const equipment = [{ id: 1, technical_report_status: 'completed' as const }];
  assert.deepEqual(describeGeneralServiceClosure({ orderStatus: 'ready_to_close', equipment, deliveredEquipmentIds: new Set([1]) }), { canClose: true, message: 'La entrega y documentación técnica están completas.' });
  assert.equal(describeGeneralServiceClosure({ orderStatus: 'in_progress', equipment, deliveredEquipmentIds: new Set([1]) }).canClose, false, 'reportes completos no bastan: manda el backend');
  assert.equal(describeGeneralServiceClosure({ orderStatus: 'completed', equipment, deliveredEquipmentIds: new Set([1]) }).canClose, false);
  assert.equal(describeGeneralServiceClosure({ orderStatus: 'in_progress', equipment: [{ id: 1, technical_report_status: 'in_progress' }], deliveredEquipmentIds: new Set() }).message, null);
});

test('4H: los errores de cierre de Servicio General se humanizan con el mensaje del backend', () => {
  const source = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'), 'utf8');
  assert.match(source, /error\.code\?\.startsWith\('TECHNICAL_REPORT_'\)/);
  assert.match(source, /Alert\.alert\('No se puede cerrar todavía', error\.message\)/);
});

test('4H: calibración conserva su cierre histórico (mismo /complete, sin mensajes de Servicio General)', async () => {
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({ status: 'ready_to_close' });
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  assert.ok(!h.text().includes('documentación técnica'));
  await h.press('Cerrar OT 6072');
  await h.flush();
  assert.equal(completePosts(h).length, 1);
  assert.ok(h.text().includes('CERRADA'));
});
