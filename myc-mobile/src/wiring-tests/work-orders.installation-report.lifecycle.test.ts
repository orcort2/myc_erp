import assert from 'node:assert/strict';
import test from 'node:test';

import { createLifecycleHarness, type LifecycleHarness } from './support/lifecycle-harness';
import {
  evidenceFixture,
  freshInstallationReport,
  generalServiceEquipmentFixture,
  installationProjection,
  workOrderFixture,
} from './support/lab-fixtures';

// SG-4A/B/C: formulario de Instalación, autosave y evidencia, ejecutando
// WorkOrdersScreen + LabInstallationReport reales (React real + DOM mínimo).

const REPORT_PATH = '/mobile/v1/technician/lab-work-orders/72/equipment/289/technical-report';

type Photo = { uri: string; width: number; height: number; mimeType: 'image/jpeg'; fileName: string; sizeBytes: number | null };
const PHOTO: Photo = { uri: 'file:///tmp/foto.jpg', width: 1600, height: 1200, mimeType: 'image/jpeg', fileName: 'foto.jpg', sizeBytes: 300_000 };

function mediaProvider(sources: ('camera' | 'library')[] = ['camera', 'library']) {
  const captured: string[] = [];
  return {
    captured,
    provider: {
      availableSources: sources,
      capture: async (source: 'camera' | 'library'): Promise<Photo | null> => { captured.push(source); return PHOTO; },
    },
  };
}

async function openReport(options: { report?: Record<string, unknown>; permissions?: string[]; status?: string; media?: ReturnType<typeof mediaProvider> | null } = {}): Promise<LifecycleHarness> {
  const h = await createLifecycleHarness();
  const detail = workOrderFixture({
    operational_category: 'general_service', status: options.status ?? 'in_progress',
    equipment: [generalServiceEquipmentFixture(installationProjection())],
  });
  h.env.detail = detail;
  h.env.report = options.report ?? freshInstallationReport();
  h.env.params = { workOrderId: '72' };
  if (options.permissions) h.env.user = { ...h.env.user, permissions: options.permissions };
  if (options.media !== null) h.setMediaProvider((options.media ?? mediaProvider()).provider);
  await h.mount();
  await h.flush();
  await h.press('Abrir reporte');
  return h;
}

const patches = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'PATCH' && call.path === REPORT_PATH);
const evidencePosts = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'POST' && call.path === `${REPORT_PATH}/evidence`);
const type = (h: LifecycleHarness, label: string, text: string) => h.act(async () => { h.registry.get(label)!.onChange(text); });
const blur = (h: LifecycleHarness, label: string) => h.act(async () => { await h.registry.get(label)!.onBlur(); });
const alertButton = (h: LifecycleHarness, title: string, text: string) => {
  const alert = [...h.probe.alerts].reverse().find((item) => item.title === title);
  const button = alert?.buttons.find((item) => item.text === text);
  assert.ok(button?.onPress, `${title} / ${text}`);
  return button!.onPress!;
};

// ------------------------------------------------------------------ SG-4A

test('4A: renderiza las siete secciones y el encabezado desde el snapshot', async () => {
  const h = await openReport();
  const text = h.text();
  for (const section of ['Datos de instalación', 'Condición inicial', 'Trabajo realizado', 'Incidencias / anomalías', 'Verificación de funcionamiento', 'Observaciones finales', 'Evidencia fotográfica']) {
    assert.ok(text.includes(section), section);
  }
  for (const header of ['Reporte de instalación', 'MYC-IN10-26-0001', 'Cliente SG', 'Báscula', 'MYC', 'B-1', 'SER-1', 'ID-1']) assert.ok(text.includes(header), header);
});

test('4A: hidrata los valores guardados y el resto queda vacío', async () => {
  const h = await openReport({ report: freshInstallationReport({ capture_values: { installation_location: 'Planta Norte', has_incidents: false } }) });
  assert.equal(h.registry.get('Lugar de instalación')!.value, 'Planta Norte');
  assert.equal(h.registry.get('Condición inicial del equipo')!.value, '');
  assert.equal(h.registry.get('¿Hubo incidencias?: No')!.accessibilityState.checked, true);
  assert.equal(h.registry.get('¿Hubo incidencias?: Sí')!.accessibilityState.checked, false);
});

test('4A: has_incidents controla los campos de incidencia; efectividad sólo con prueba funcional', async () => {
  const h = await openReport();
  assert.ok(!h.text().includes('Descripción de la incidencia'));
  assert.ok(!h.text().includes('Resultado de efectividad'));
  await h.press('¿Hubo incidencias?: Sí');
  assert.ok(h.text().includes('Descripción de la incidencia'));
  assert.ok(h.text().includes('Acción correctiva'));
  await h.press('¿Hubo incidencias?: No');
  assert.ok(!h.text().includes('Descripción de la incidencia'));
  await h.press('¿Se realizó prueba funcional?: Sí');
  for (const label of ['Satisfactorio', 'Satisfactorio con observaciones', 'No satisfactorio']) assert.ok(h.registry.has(`Efectividad: ${label}`), label);
  await h.press('Efectividad: No satisfactorio');
  await h.press('¿Se realizó prueba funcional?: No');
  assert.ok(!h.text().includes('Resultado de efectividad'), 'sin prueba funcional no hay resultado');
  await h.press('¿Se realizó prueba funcional?: Sí');
  assert.equal(h.registry.get('Efectividad: No satisfactorio')!.accessibilityState.checked, false, 'no se inventa ni conserva un resultado');
});

// ------------------------------------------------------------------ SG-4B

test('4B: editar y salir del campo guarda con un solo PATCH de capture_values (sin snapshot)', async () => {
  const h = await openReport();
  await type(h, 'Lugar de instalación', 'Planta Norte');
  await type(h, 'Lugar de instalación', 'Planta Norte 2');
  await type(h, 'Condición inicial del equipo', 'Empacado');
  assert.equal(patches(h).length, 0, 'no hay PATCH por tecla');
  await blur(h, 'Condición inicial del equipo');
  assert.equal(patches(h).length, 1);
  const body = patches(h)[0].body as { capture_values: Record<string, unknown> };
  assert.deepEqual(Object.keys(body), ['capture_values']);
  assert.equal(body.capture_values.installation_location, 'Planta Norte 2');
  assert.equal(body.capture_values.initial_condition, 'Empacado');
  assert.equal(body.capture_values.has_incidents, null);
  assert.doesNotMatch(JSON.stringify(body), /folio|client|serial|brand|MYC-IN|status|report_type/);
  assert.ok(h.text().includes('Guardado'));
});

test('4B: el autosave por debounce guarda sin salir del campo', async () => {
  const h = await openReport();
  await type(h, 'Lugar de instalación', 'Bodega');
  await new Promise((resolve) => setTimeout(resolve, 1000));
  await h.flush();
  assert.equal(patches(h).length, 1);
});

test('4B: la primera captura promueve el reporte a EN CAPTURA y refresca al salir', async () => {
  const h = await openReport();
  await type(h, 'Lugar de instalación', 'Bodega');
  await h.press('Volver a equipos');
  assert.equal(patches(h).length, 1);
  assert.ok(h.text().includes('EN CAPTURA'));
});

test('4B: error de autosave es visible, conserva lo escrito y bloquea la salida', async () => {
  const h = await openReport();
  h.env.failCaptureSave = true;
  await type(h, 'Lugar de instalación', 'Bodega');
  await blur(h, 'Lugar de instalación');
  assert.ok(h.text().includes('No se pudo guardar automáticamente'));
  assert.equal(h.registry.get('Lugar de instalación')!.value, 'Bodega');
  await h.press('Volver a equipos');
  assert.ok(h.text().includes('No se pudo guardar tu captura'), 'la salida se bloquea');
  assert.ok(h.text().includes('Reporte de instalación'), 'sigue dentro del reporte');
  h.env.failCaptureSave = false;
  await h.press('Volver a equipos');
  assert.ok(!h.text().includes('Datos de instalación'), 'con guardado exitoso sale');
});

test('4B: un reporte listo para firmas o de sólo lectura no es editable', async () => {
  const locked = await openReport({ report: freshInstallationReport({ status: 'ready_for_signatures' }) });
  assert.ok(locked.text().includes('Este reporte ya no es editable'));
  assert.equal(locked.registry.get('Lugar de instalación')?.onChange, undefined, 'sólo lectura: sin campo editable');
  const readOnly = await openReport({ permissions: ['mobile.access', 'work_orders.read_organization', 'technical_reports.read'] });
  assert.ok(readOnly.text().includes('no capturarlo'));
  assert.equal(patches(readOnly).length, 0);
});

// ------------------------------------------------------------------ SG-4C

test('4C: la sección determina evidence_type (before / incident / after) sin preguntarlo', async () => {
  const media = mediaProvider(['camera']);
  const h = await openReport({ media });
  await h.press('¿Hubo incidencias?: Sí');
  await h.press('¿Se realizó prueba funcional?: Sí');
  const expected: [string, string][] = [
    ['Agregar foto · Antes', 'before'], ['Agregar foto · Incidencia', 'incident'], ['Agregar foto · Resultado final', 'after'],
  ];
  for (const [label] of expected) await h.press(label);
  assert.deepEqual(evidencePosts(h).map((call) => (call.body as Record<string, unknown>).evidence_type), expected.map(([, kind]) => kind));
  assert.deepEqual(media.captured, ['camera', 'camera', 'camera']);
  assert.ok(!h.probe.alerts.some((alert) => alert.title === 'Agregar foto'), 'una sola fuente: sin preguntar');
});

test('4C: con cámara y galería se ofrece elegir la fuente', async () => {
  const media = mediaProvider();
  const h = await openReport({ media });
  await h.press('Agregar foto · Antes');
  const sheet = h.probe.alerts.find((alert) => alert.title === 'Agregar foto')!;
  assert.deepEqual(sheet.buttons.map((button) => button.text), ['Tomar foto', 'Elegir de galería', 'Cancelar']);
  await h.act(async () => { sheet.buttons[1].onPress!(); });
  await h.flush();
  assert.deepEqual(media.captured, ['library']);
  assert.equal(evidencePosts(h).length, 1);
});

test('4C: preview autenticado tras subir, eliminar con confirmación y reporte editable', async () => {
  const media = mediaProvider(['camera']);
  const h = await openReport({ media });
  await h.press('Agregar foto · Antes');
  const preview = h.registry.get('Foto Antes 1');
  assert.ok(preview, 'preview de la foto subida');
  assert.match(preview.source.uri, /technical-report\/evidence\/\d+\/file$/);
  assert.equal(preview.source.headers.Authorization, 'Bearer t');
  assert.ok(h.text().includes('EN CAPTURA'));

  await h.press('Eliminar foto 1');
  await h.act(async () => { alertButton(h, 'Eliminar foto', 'Eliminar')(); });
  await h.flush();
  assert.ok(h.probe.calls.some((call) => call.method === 'DELETE' && /evidence\/\d+$/.test(call.path)));
  assert.ok(h.text().includes('Sin fotografías'));
});

test('4C: cancelar la captura no sube nada; un fallo de subida se informa', async () => {
  const cancelled = { availableSources: ['camera'] as ('camera' | 'library')[], capture: async (): Promise<Photo | null> => null };
  const h = await openReport({ media: { captured: [], provider: cancelled } });
  await h.press('Agregar foto · Antes');
  assert.equal(evidencePosts(h).length, 0);

  const failing = await openReport({ media: mediaProvider(['camera']) });
  failing.env.failEvidenceUpload = true;
  await failing.press('Agregar foto · Antes');
  assert.ok(failing.probe.log.includes('Alert:No fue posible agregar la foto'));
  assert.ok(!failing.registry.has('Foto Antes 1'));
});

test('4C: sin proveedor de medios no se ofrece Agregar foto y se explica; la evidencia existente se ve', async () => {
  const report = freshInstallationReport({ evidence: [evidenceFixture(11, 'before', 1)], status: 'in_progress' });
  const h = await openReport({ report, media: null });
  assert.ok(!h.text().includes('Agregar foto'));
  assert.ok(h.text().includes('requiere actualizar la app'));
  assert.ok(h.registry.has('Foto Antes 1'));
});

test('4C: la evidencia no se puede agregar ni eliminar si el reporte no es editable', async () => {
  const report = freshInstallationReport({ evidence: [evidenceFixture(11, 'before', 1)], status: 'ready_for_signatures' });
  const h = await openReport({ report });
  assert.ok(h.registry.has('Foto Antes 1'));
  assert.ok(!h.text().includes('Agregar foto'));
  assert.ok(!h.text().includes('Eliminar'));
});

test('no mezcla FieldSheet: el reporte jamás toca endpoints ni componentes de hoja de campo', async () => {
  const h = await openReport({ media: mediaProvider(['camera']) });
  await type(h, 'Lugar de instalación', 'Bodega');
  await blur(h, 'Lugar de instalación');
  await h.press('Agregar foto · Antes');
  assert.ok(h.probe.requests.every((request) => !/field-sheet/.test(request)));
  assert.ok(!h.probe.log.some((line) => line.startsWith('LTC mount')));
});

test('calibración nunca monta el reporte de instalación', async () => {
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({ status: 'received_signed' });
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  assert.ok(!h.text().includes('Reporte de instalación'));
  assert.ok(!h.text().includes('Seleccionar reporte'));
  assert.ok(h.probe.requests.every((request) => !/technical-report/.test(request)));
});
