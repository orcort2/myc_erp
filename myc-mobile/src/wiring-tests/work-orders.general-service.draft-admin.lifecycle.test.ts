import assert from 'node:assert/strict';
import test from 'node:test';

import { createLifecycleHarness, type LifecycleHarness } from './support/lifecycle-harness';
import {
  freshInstallationReport,
  generalServiceEquipmentFixture,
  installationProjection,
  workOrderFixture,
} from './support/lab-fixtures';
import { changeTypeOptions } from '../services/technical-report';

// SG-4I-A: administración del borrador (eliminar / cambiar tipo) y SG-4I-B
// (paquete y reportes después del cierre), con WorkOrdersScreen real.

const REPORT_PATH = '/mobile/v1/technician/lab-work-orders/72/equipment/289/technical-report';
const PACKAGE_PATH = '/mobile/v1/technician/lab-work-orders/72/package?group=false';

async function openDraft(status = 'in_progress', orderStatus = 'in_progress'): Promise<LifecycleHarness> {
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({
    operational_category: 'general_service', status: orderStatus,
    equipment: [generalServiceEquipmentFixture(installationProjection({ technical_report_status: status }))],
  });
  h.env.report = freshInstallationReport({ status });
  h.env.deliveryStatus = null;
  h.env.params = { workOrderId: '72' };
  h.setMediaProvider(null);
  await h.mount();
  await h.flush();
  await h.press('Abrir reporte');
  return h;
}

const deletePosts = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'POST' && call.path === `${REPORT_PATH}/delete-draft`);
const patches = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'PATCH' && call.path === REPORT_PATH);
const alertButton = (h: LifecycleHarness, title: string, text: string) => {
  const alert = [...h.probe.alerts].reverse().find((item) => item.title === title);
  const button = alert?.buttons.find((item) => item.text === text);
  assert.ok(button?.onPress, `${title} / ${text}`);
  return button!.onPress!;
};

test('4I-A: las acciones administrativas sólo aparecen con el reporte editable', async () => {
  for (const status of ['draft', 'in_progress']) {
    const h = await openDraft(status);
    assert.ok(h.text().includes('Eliminar borrador') && h.text().includes('Cambiar tipo de reporte'), status);
    assert.ok(h.text().includes('Confirmar captura'), 'separadas de la acción principal');
  }
  for (const status of ['ready_for_signatures', 'completed']) {
    const h = await openDraft(status);
    assert.ok(!h.text().includes('Eliminar borrador') && !h.text().includes('Cambiar tipo de reporte'), status);
  }
});

test('4I-A: eliminar pide confirmación destructiva y cancelar no elimina', async () => {
  const h = await openDraft();
  await h.press('Eliminar borrador');
  const alert = h.probe.alerts.find((item) => item.title === '¿Eliminar este borrador de reporte?')!;
  assert.ok(alert);
  assert.deepEqual(alert.buttons.map((button) => button.text), ['Cancelar', 'Eliminar borrador']);
  assert.equal(deletePosts(h).length, 0);
  await h.act(async () => { alert.buttons[0].onPress?.(); });
  assert.equal(deletePosts(h).length, 0);
  assert.ok(h.text().includes('Eliminar borrador'), 'el reporte sigue abierto');
});

test('4I-A: al eliminar se cierra el reporte, se refresca la OT y el equipo vuelve a SIN REPORTE', async () => {
  const h = await openDraft();
  await h.press('Eliminar borrador');
  const requestsBefore = h.probe.requests.length;
  await h.act(async () => { alertButton(h, '¿Eliminar este borrador de reporte?', 'Eliminar borrador')(); });
  await h.flush();
  assert.equal(deletePosts(h).length, 1);
  assert.ok(h.probe.requests.slice(requestsBefore).some((request) => /^GET .*lab-work-orders\/72$/.test(request)), 'refresca la OT');
  const text = h.text();
  assert.ok(text.includes('SIN REPORTE'));
  assert.ok(text.includes('Seleccionar reporte'));
  assert.ok(!text.includes('Eliminar borrador'), 'el overlay del reporte se cerró');
});

test('4I-A: el autosave pendiente se descarta: ningún PATCH tardío contra el borrador eliminado', async () => {
  const h = await openDraft();
  await h.act(async () => { h.registry.get('Lugar de instalación')!.onChange('Bodega'); });
  await h.press('Eliminar borrador');
  await h.act(async () => { alertButton(h, '¿Eliminar este borrador de reporte?', 'Eliminar borrador')(); });
  await new Promise((resolve) => setTimeout(resolve, 1000));
  await h.flush();
  assert.equal(deletePosts(h).length, 1);
  assert.equal(patches(h).length, 0);
});

test('4I-A: si el backend rechaza la eliminación el borrador sigue abierto', async () => {
  const h = await openDraft();
  h.env.deleteDraftError = 'El equipo ya tiene una entrega registrada';
  await h.press('Eliminar borrador');
  await h.act(async () => { alertButton(h, '¿Eliminar este borrador de reporte?', 'Eliminar borrador')(); });
  await h.flush();
  assert.ok(h.probe.log.includes('Alert:No fue posible eliminar el borrador'));
  assert.ok(h.text().includes('Eliminar borrador'));
});

test('4I-A: el selector de tipo muestra Installation como actual y los demás Próximamente, sin poder elegirlos', async () => {
  const h = await openDraft();
  await h.press('Cambiar tipo de reporte');
  const text = h.text();
  assert.ok(text.includes('Actual'));
  assert.equal((text.match(/Próximamente/g) ?? []).length, 4);
  for (const title of ['Instalación', 'Verificación', 'Reparación', 'Mantenimiento', 'Venta']) {
    const option = h.registry.get(`Tipo de reporte: ${title}`)!;
    assert.equal(option.disabled, true, title);
  }
  assert.ok(!h.probe.calls.some((call) => /change-type/.test(call.path)), 'ningún tipo no disponible llega a la red');
});

test('4I-A: changeTypeOptions deja el contrato listo para tipos futuros', () => {
  const options = changeTypeOptions('installation');
  assert.deepEqual(options.map((option) => [option.value, option.caption, option.selectable]), [
    ['installation', 'Actual', false], ['verification', 'Próximamente', false], ['repair', 'Próximamente', false],
    ['maintenance', 'Próximamente', false], ['sale', 'Próximamente', false],
  ]);
});

test('4I-A: calibración no muestra administración de reportes', async () => {
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({ status: 'in_progress' });
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  assert.ok(!h.text().includes('Eliminar borrador') && !h.text().includes('Cambiar tipo de reporte'));
});

// ------------------------------------------------------------------ SG-4I-B

async function openClosed(category: 'general_service' | 'calibration'): Promise<LifecycleHarness> {
  const h = await createLifecycleHarness();
  h.env.detail = category === 'general_service'
    ? workOrderFixture({ operational_category: 'general_service', status: 'completed', equipment: [generalServiceEquipmentFixture(installationProjection({ technical_report_status: 'completed' }))] })
    : workOrderFixture({ status: 'completed' });
  h.env.report = freshInstallationReport({ status: 'completed' });
  h.env.deliveryStatus = null;
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  return h;
}

test('4I-B: una OT de Servicio General cerrada ofrece reporte y paquete', async () => {
  const h = await openClosed('general_service');
  const text = h.text();
  assert.ok(text.includes('Ver reporte') && text.includes('Descargar reporte'));
  assert.ok(text.includes('Descargar paquete de esta OT'));
});

test('4I-B: Descargar paquete usa el endpoint existente y comparte el archivo', async () => {
  const h = await openClosed('general_service');
  await h.press('Descargar paquete de esta OT');
  assert.equal(h.probe.downloads.length, 1);
  assert.equal(h.probe.downloads[0].url, PACKAGE_PATH);
  assert.deepEqual(h.probe.downloads[0].headers, { Authorization: 'Bearer t' });
  assert.equal(h.probe.shares.length, 1);
});

test('4I-B: un paquete rechazado muestra el error y no comparte nada', async () => {
  const h = await openClosed('general_service');
  h.env.downloadStatus = 409;
  await h.press('Descargar paquete de esta OT');
  assert.ok(h.probe.log.includes('Alert:No fue posible abrir el paquete'));
  assert.equal(h.probe.shares.length, 0);
});

test('4I-B: Ver reporte abre el PDF final del equipo', async () => {
  const h = await openClosed('general_service');
  await h.press('Ver reporte');
  assert.equal(h.probe.downloads[0].url, `${REPORT_PATH}/pdf`);
  assert.equal(h.probe.prints.length, 1);
});

test('4I-B: calibración conserva su paquete y no muestra acciones de reporte', async () => {
  const h = await openClosed('calibration');
  assert.ok(h.text().includes('Descargar paquete de esta OT'));
  assert.ok(!h.text().includes('Ver reporte') && !h.text().includes('Descargar reporte'));
  await h.press('Descargar paquete de esta OT');
  assert.equal(h.probe.downloads[0].url, PACKAGE_PATH);
});
