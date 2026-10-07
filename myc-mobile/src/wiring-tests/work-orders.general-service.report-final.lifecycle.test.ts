import assert from 'node:assert/strict';
import test from 'node:test';

import { createLifecycleHarness, type LifecycleHarness } from './support/lifecycle-harness';
import {
  freshInstallationReport,
  generalServiceEquipmentFixture,
  installationProjection,
  workOrderFixture,
} from './support/lab-fixtures';

// SG-4G: tras la entrega, "Generar reporte final" (acción explícita) produce el
// PDF institucional y el reporte pasa a COMPLETADO; la OT NO se cierra.

const REPORT_PATH = '/mobile/v1/technician/lab-work-orders/72/equipment/289/technical-report';

const deliveredStatus = () => ({
  root_work_order_id: 72, total_equipment: 1, delivered_equipment: 1, pending_equipment: [], group_complete: true,
  final_receipt_available: true, final_receipt_version: 1, pending_partial_delivery_ticket_id: null,
  exhibitions: [{
    id: 800, exhibition_number: 1, delivery_type: 'full', status: 'completed', delivered_at: '2026-10-08T17:00:00+00:00',
    recipient_name: 'Persona Recibe', items: [{ id: 1, work_order_id: 72, work_order_folio: 6072, equipment_id: 289 }],
  }],
});

const undeliveredStatus = () => ({
  root_work_order_id: 72, total_equipment: 1, delivered_equipment: 0, group_complete: false, exhibitions: [],
  final_receipt_available: false, final_receipt_version: null, pending_partial_delivery_ticket_id: null,
  pending_equipment: [{
    work_order_id: 72, work_order_folio: 6072, equipment_id: 289, position: 1, instrument: 'Báscula', brand: 'MYC', identification: 'ID',
    serial_number: 'S1', certificate_folio: null, delivery_eligible: true, delivery_blocked_reason: null,
    technical_report_folio: 'MYC-IN10-26-0001', client_conformity_text: 'Texto',
  }],
});

async function open(options: { delivered?: boolean; reportStatus?: string; permissions?: string[] } = {}): Promise<LifecycleHarness> {
  const h = await createLifecycleHarness();
  const reportStatus = options.reportStatus ?? 'ready_for_signatures';
  h.env.detail = workOrderFixture({
    operational_category: 'general_service', status: 'in_progress',
    equipment: [generalServiceEquipmentFixture(installationProjection({ technical_report_status: reportStatus }))],
  });
  h.env.report = freshInstallationReport({ status: reportStatus, performed_by_user_id: 1, performed_by_name_snapshot: 'Tec' });
  h.env.deliveryStatus = options.delivered === false ? undeliveredStatus() : deliveredStatus();
  h.env.params = { workOrderId: '72' };
  if (options.permissions) h.env.user = { ...h.env.user, permissions: options.permissions };
  await h.mount();
  await h.flush();
  return h;
}

const finalizePosts = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'POST' && call.path === `${REPORT_PATH}/finalize`);
const completePosts = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'POST' && /\/complete(\/individual)?(\?.*)?$/.test(call.path));

test('4G: tras una entrega válida aparece "Generar reporte final"; antes de la entrega no', async () => {
  const delivered = await open();
  assert.ok(delivered.text().includes('Generar reporte final'));
  assert.ok(delivered.text().includes('LISTO PARA ENTREGA'));
  const pending = await open({ delivered: false });
  assert.ok(!pending.text().includes('Generar reporte final'));
  assert.ok(pending.text().includes('Proceder a entrega'));
});

test('4G: llama al endpoint /finalize correcto, muestra COMPLETADO y las acciones Ver/Descargar reporte', async () => {
  const h = await open();
  const requestsBefore = h.probe.requests.length;
  await h.press('Generar reporte final');
  await h.flush();
  assert.equal(finalizePosts(h).length, 1);
  assert.equal(finalizePosts(h)[0].body, undefined, 'Mobile no manda estado ni datos: el backend decide');
  assert.ok(h.probe.requests.slice(requestsBefore).some((request) => /^GET .*lab-work-orders\/72$/.test(request)), 'refresca la OT');
  const text = h.text();
  assert.ok(text.includes('COMPLETADO'));
  assert.ok(text.includes('Ver reporte') && text.includes('Descargar reporte'));
  assert.ok(!text.includes('Generar reporte final'));
});

test('4G: muestra loading mientras se genera y no permite doble envío', async () => {
  const h = await open();
  let release!: () => void;
  h.env.finalizeGate = new Promise<void>((resolve) => { release = resolve; });
  await h.observe(async (tools) => {
    await tools.settle();
    const props = h.registry.get('Generar reporte final')!;
    assert.equal(props.loading, true);
    assert.equal(props.disabled, true);
    release();
  }, 'Generar reporte final');
  assert.equal(finalizePosts(h).length, 1);
});

test('4G: un error del backend se muestra y el reporte sigue listo (sin completar)', async () => {
  const h = await open();
  h.env.finalizeError = 'No se encontró el archivo de la evidencia before #1';
  await h.press('Generar reporte final');
  await h.flush();
  assert.ok(h.probe.log.includes('Alert:No fue posible generar el reporte final'));
  assert.ok(!h.text().includes('COMPLETADO'));
  assert.ok(h.text().includes('Generar reporte final'), 'puede reintentar');
});

test('4G: Ver reporte abre el PDF final autenticado; Descargar lo comparte', async () => {
  const h = await open({ reportStatus: 'completed' });
  await h.press('Ver reporte');
  assert.equal(h.probe.downloads.length, 1);
  assert.equal(h.probe.downloads[0].url, `${REPORT_PATH}/pdf`);
  assert.deepEqual(h.probe.downloads[0].headers, { Authorization: 'Bearer t' });
  assert.equal(h.probe.prints.length, 1);
  await h.press('Descargar reporte');
  assert.equal(h.probe.downloads.length, 2);
  assert.equal(h.probe.shares.length, 1);
});

test('4G: reporte completado no muestra edición, fotos ni cierre; la OT no se cierra', async () => {
  const h = await open({ reportStatus: 'completed' });
  assert.ok(!h.text().includes('Continuar a cierre'));
  assert.ok(h.text().includes('La entrega y el reporte están completos. La OT está pendiente de cierre.'));
  await h.press('Abrir reporte');
  const text = h.text();
  assert.ok(text.includes('Reporte final generado'));
  assert.ok(!text.includes('Confirmar captura') && !text.includes('Agregar foto'));
  assert.equal(h.registry.get('Lugar de instalación')?.onChange, undefined, 'campos de sólo lectura');
  assert.equal(completePosts(h).length, 0);
  assert.ok(!h.probe.requests.some((request) => /\/complete/.test(request)));
});

test('4G: sin permiso de captura no se ofrece generar el reporte', async () => {
  const h = await open({ permissions: ['mobile.access', 'work_orders.read_organization', 'technical_reports.read'] });
  assert.ok(!h.text().includes('Generar reporte final'));
});

test('4G: calibración no muestra acciones de reporte final ni cambia su cierre', async () => {
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({ status: 'in_progress', equipment: [] });
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  assert.ok(!h.text().includes('Generar reporte final') && !h.text().includes('Ver reporte'));
  assert.ok(h.text().includes('Continuar a cierre'));
});
