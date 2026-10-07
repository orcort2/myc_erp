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
  assert.ok(locked.text().includes('Captura confirmada: el reporte quedó bloqueado'));
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

test('4C: la foto subida aparece como miniatura autenticada del grid', async () => {
  const media = mediaProvider(['camera']);
  const h = await openReport({ media });
  await h.press('Agregar foto · Antes');
  const preview = h.registry.get('Foto Antes 1');
  assert.ok(preview, 'miniatura de la foto subida');
  assert.match(preview.source.uri, /technical-report\/evidence\/\d+\/file$/);
  assert.equal(preview.source.headers.Authorization, 'Bearer t');
  assert.equal(preview.cachePolicy, 'memory-disk', 'no se descarga de nuevo');
  assert.ok(h.text().includes('EN CAPTURA'));
  assert.ok(h.text().includes('1 evidencia'));
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

// ------------------------------------------------------------------ SG-4C.2-4: grid y visor

function evidenceReport(counts: { before?: number; during?: number; incident?: number; after?: number }, status = 'in_progress') {
  const evidence: Record<string, unknown>[] = [];
  let id = 100;
  let position = 0;
  for (const [type, count] of Object.entries(counts)) {
    for (let n = 0; n < (count ?? 0); n += 1) evidence.push(evidenceFixture((id += 1), type, (position += 1)));
  }
  return freshInstallationReport({ evidence, status, capture_values: { has_incidents: true, functional_test_performed: true } });
}

const deletes = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'DELETE');

test('4C.2: sin fotos sólo hay la celda Agregar y no hay contador', async () => {
  const h = await openReport({ report: evidenceReport({}) });
  assert.ok(h.registry.has('Agregar foto · Antes'));
  assert.ok(h.text().includes('Agregar'));
  assert.ok(!h.registry.has('Foto Antes 1'));
  assert.ok(!/\d+ evidencias?/.test(h.text().replace('0 de 20', '')), 'sin contador de evidencias en la categoría');
});

test('4C.2: una y varias fotos: miniaturas por categoría y contador correcto', async () => {
  const h = await openReport({ report: evidenceReport({ before: 1, incident: 3 }) });
  assert.ok(h.registry.has('Foto Antes 1'));
  assert.ok(h.text().includes('1 evidencia'));
  assert.ok(h.registry.has('Foto Incidencia 2') && h.registry.has('Foto Incidencia 4'));
  assert.ok(h.text().includes('3 evidencias'));
  assert.ok(h.text().includes('4 de 20 fotografías'), 'el total sigue visible');
  assert.ok(!h.registry.has('Eliminar foto 1'), 'no hay botón de borrado sobre la miniatura');
});

test('4C.4: con muchas fotos se limitan las miniaturas (3 columnas = 5 + "+N") y el total sigue visible', async () => {
  const h = await openReport({ report: evidenceReport({ before: 9 }) });
  for (const position of [1, 2, 3, 4, 5]) assert.ok(h.registry.has(`Foto Antes ${position}`), `miniatura ${position}`);
  assert.ok(!h.registry.has('Foto Antes 6'), 'la sexta ya no es miniatura');
  assert.ok(h.text().includes('+4'));
  assert.ok(h.text().includes('9 evidencias'));
  assert.ok(h.registry.has('Ver 9 fotos'));
  assert.ok(h.registry.has('Agregar foto · Antes'), 'agregar sigue disponible fuera del grid');
});

test('4C.4: en pantallas estrechas el grid usa 2 columnas (3 miniaturas + "+N")', async () => {
  const h = await createLifecycleHarness();
  h.env.windowWidth = 320;
  h.env.detail = workOrderFixture({ operational_category: 'general_service', status: 'in_progress', equipment: [generalServiceEquipmentFixture(installationProjection())] });
  h.env.report = evidenceReport({ before: 9 });
  h.env.params = { workOrderId: '72' };
  h.setMediaProvider(mediaProvider().provider);
  await h.mount(); await h.flush();
  await h.press('Abrir reporte');
  for (const position of [1, 2, 3]) assert.ok(h.registry.has(`Foto Antes ${position}`));
  assert.ok(!h.registry.has('Foto Antes 4'));
  assert.ok(h.text().includes('+6'));
});

test('4C.3: tocar una miniatura abre el visor en esa foto con indicador N de M', async () => {
  const h = await openReport({ report: evidenceReport({ before: 3, incident: 2 }) });
  assert.ok(!h.registry.has('Foto ampliada Antes 2'));
  await h.press('Abrir foto Antes 2');
  assert.ok(h.registry.has('Foto ampliada Antes 2'));
  assert.ok(h.text().includes('2 de 3 · Antes'));
});

test('4C.3: la navegación recorre sólo la categoría de la foto abierta', async () => {
  const h = await openReport({ report: evidenceReport({ before: 3, during: 1, incident: 2, after: 1 }) });
  await h.press('Abrir foto Antes 1');
  for (const position of [1, 2, 3]) assert.ok(h.registry.has(`Foto ampliada Antes ${position}`));
  for (const other of ['Durante', 'Incidencia', 'Resultado final']) {
    assert.ok([...h.registry.keys()].every((key) => !key.startsWith(`Foto ampliada ${other}`)), `no mezcla ${other}`);
  }
  await h.press('Foto siguiente');
  assert.ok(h.text().includes('2 de 3 · Antes'));
  await h.press('Foto siguiente');
  await h.press('Foto siguiente');
  assert.ok(h.text().includes('3 de 3 · Antes'), 'no da la vuelta');
  await h.press('Foto anterior');
  assert.ok(h.text().includes('2 de 3 · Antes'));
});

test('4C.3: la celda "+N" abre el visor con la colección completa de la categoría', async () => {
  const h = await openReport({ report: evidenceReport({ before: 9 }) });
  await h.press('Ver 9 fotos');
  for (let position = 1; position <= 9; position += 1) assert.ok(h.registry.has(`Foto ampliada Antes ${position}`), `foto ${position}`);
  assert.ok(h.text().includes('de 9 · Antes'));
});

test('4C.3: eliminar pide confirmación; cancelar no borra', async () => {
  const h = await openReport({ report: evidenceReport({ before: 2 }) });
  await h.press('Abrir foto Antes 1');
  await h.press('Eliminar evidencia');
  const confirm = h.probe.alerts.find((alert) => alert.title === '¿Eliminar esta evidencia?')!;
  assert.deepEqual(confirm.buttons.map((button) => button.text), ['Cancelar', 'Eliminar']);
  assert.equal(deletes(h).length, 0, 'sin confirmar no hay DELETE');
  await h.act(async () => { confirm.buttons[0].onPress?.(); });
  assert.equal(deletes(h).length, 0);
  assert.ok(h.text().includes('1 de 2 · Antes'));
});

test('4C.3: eliminación confirmada llama al backend, actualiza visor y grid sin tocar el formulario', async () => {
  const h = await openReport({ report: evidenceReport({ before: 3 }) });
  await type(h, 'Lugar de instalación', 'Sin guardar aún');
  await h.press('Abrir foto Antes 2');
  await h.press('Eliminar evidencia');
  await h.act(async () => { alertButton(h, '¿Eliminar esta evidencia?', 'Eliminar')(); });
  await h.flush();
  assert.equal(deletes(h).length, 1);
  assert.ok(h.text().includes('2 evidencias'), 'grid actualizado');
  assert.ok(h.text().includes('2 de 2 · Antes'), 'visor con selección válida');
  assert.equal(h.registry.get('Lugar de instalación')!.value, 'Sin guardar aún', 'el borrador local no se pierde');
});

test('4C.3: eliminar la última fotografía cierra el visor', async () => {
  const h = await openReport({ report: evidenceReport({ before: 1 }) });
  await h.press('Abrir foto Antes 1');
  assert.ok(h.text().includes('1 de 1 · Antes'));
  await h.press('Eliminar evidencia');
  await h.act(async () => { alertButton(h, '¿Eliminar esta evidencia?', 'Eliminar')(); });
  await h.flush();
  assert.ok(!h.text().includes('1 de 1 · Antes'), 'visor cerrado');
  assert.ok(!h.text().includes('1 evidencia'));
  assert.ok(h.registry.has('Agregar foto · Antes'));
});

test('4C.3: un reporte no editable abre el visor pero no ofrece eliminar ni agregar', async () => {
  const h = await openReport({ report: evidenceReport({ before: 2 }, 'ready_for_signatures') });
  await h.press('Abrir foto Antes 1');
  assert.ok(h.text().includes('1 de 2 · Antes'));
  assert.ok(!h.registry.has('Eliminar evidencia'));
  assert.ok(!h.text().includes('Eliminar'));
  assert.ok(!h.text().includes('Agregar'));
});

test('4C.3: el visor usa una superficie translúcida (glass) sin dependencias de blur', async () => {
  const { readFileSync } = await import('node:fs');
  const { dirname, resolve } = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const source = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../components/lab/LabEvidenceGallery.tsx'), 'utf8');
  assert.match(source, /rgba\(20, 43, 58, 0\.62\)/);
  assert.doesNotMatch(source, /expo-blur|BlurView/);
});

// ------------------------------------------------------------------ consistencia incidencias / evidencia

const BLOCK_MESSAGE = 'Elimina primero las evidencias de incidencia para indicar que no hubo incidencias.';

test('incidencias: con evidencia incident no se permite pasar de Sí a No', async () => {
  const h = await openReport({ report: evidenceReport({ incident: 2 }) });
  assert.equal(h.registry.get('¿Hubo incidencias?: Sí')!.accessibilityState.checked, true);
  await h.press('¿Hubo incidencias?: No');
  const alert = h.probe.alerts.find((item) => item.title === 'No se puede cambiar');
  assert.ok(alert, 'se informa el bloqueo');
  assert.equal(h.probe.log.filter((line) => line === 'Alert:No se puede cambiar').length, 1);
  // El valor permanece true, las evidencias siguen visibles y no hay borrados ni PATCH.
  assert.equal(h.registry.get('¿Hubo incidencias?: Sí')!.accessibilityState.checked, true);
  assert.equal(h.registry.get('¿Hubo incidencias?: No')!.accessibilityState.checked, false);
  assert.ok(h.registry.has('Foto Incidencia 1') && h.registry.has('Foto Incidencia 2'));
  assert.ok(h.text().includes('2 evidencias'));
  assert.equal(deletes(h).length, 0);
  assert.equal(patches(h).length, 0);
  assert.ok(h.text().includes('Descripción de la incidencia'), 'la sección sigue visible');
});

test('incidencias: el mensaje de bloqueo es el acordado', async () => {
  const { readFileSync } = await import('node:fs');
  const { dirname, resolve } = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const source = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../components/lab/LabInstallationReport.tsx'), 'utf8');
  assert.ok(source.includes(BLOCK_MESSAGE));
});

test('incidencias: tras borrar todas las evidencias incident ya se puede indicar No', async () => {
  const h = await openReport({ report: evidenceReport({ incident: 1 }) });
  await h.press('¿Hubo incidencias?: No');
  assert.equal(h.registry.get('¿Hubo incidencias?: Sí')!.accessibilityState.checked, true);

  await h.press('Abrir foto Incidencia 1');
  await h.press('Eliminar evidencia');
  await h.act(async () => { alertButton(h, '¿Eliminar esta evidencia?', 'Eliminar')(); });
  await h.flush();
  assert.equal(deletes(h).length, 1);

  await h.press('¿Hubo incidencias?: No');
  assert.equal(h.registry.get('¿Hubo incidencias?: No')!.accessibilityState.checked, true);
  assert.ok(!h.text().includes('Descripción de la incidencia'));
});

test('incidencias: evidencia de otras categorías no bloquea; sin incident se cambia libremente Sí/No', async () => {
  const h = await openReport({ report: evidenceReport({ before: 2, after: 1 }) });
  await h.press('¿Hubo incidencias?: No');
  assert.equal(h.registry.get('¿Hubo incidencias?: No')!.accessibilityState.checked, true);
  await h.press('¿Hubo incidencias?: Sí');
  await h.press('¿Hubo incidencias?: No');
  assert.equal(h.registry.get('¿Hubo incidencias?: No')!.accessibilityState.checked, true);
  assert.ok(!h.probe.log.includes('Alert:No se puede cambiar'));
  assert.ok(h.registry.has('Foto Antes 2') && h.registry.has('Foto Resultado final 3'), 'las demás evidencias intactas');
});

test('incidencias: la regla no afecta a calibración (no existe reporte ni este bloqueo)', async () => {
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({ status: 'received_signed' });
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  assert.ok(!h.registry.has('¿Hubo incidencias?: No'));
  assert.ok(h.probe.requests.every((request) => !/technical-report/.test(request)));
  assert.ok(h.probe.log.some((line) => line.startsWith('LTC mount')), 'la captura de hojas sigue montándose');
});

// ------------------------------------------------------------------ SG-4D/E: confirmar captura

const confirmPosts = (h: LifecycleHarness) => h.probe.calls.filter((call) => call.method === 'POST' && call.path === `${REPORT_PATH}/confirm-capture`);

test('4E: el botón Confirmar captura está separado del autosave y sólo aparece con el reporte editable', async () => {
  const editable = await openReport();
  assert.ok(editable.registry.has('Confirmar captura'));
  assert.ok(editable.text().includes('no finaliza el reporte'));
  assert.equal(confirmPosts(editable).length, 0, 'el autosave no confirma');
  await type(editable, 'Lugar de instalación', 'Bodega');
  await blur(editable, 'Lugar de instalación');
  assert.equal(patches(editable).length, 1);
  assert.equal(confirmPosts(editable).length, 0);

  const locked = await openReport({ report: freshInstallationReport({ status: 'ready_for_signatures' }) });
  assert.ok(!locked.text().includes('Confirmar captura'));
  const readOnly = await openReport({ permissions: ['mobile.access', 'work_orders.read_organization', 'technical_reports.read'] });
  assert.ok(!readOnly.text().includes('Confirmar captura'));
});

test('4E: pide confirmación advirtiendo el bloqueo; cancelar no envía nada', async () => {
  const h = await openReport();
  await h.press('Confirmar captura');
  const confirm = h.probe.alerts.find((alert) => alert.title === '¿Confirmar captura?')!;
  assert.ok(confirm);
  assert.deepEqual(confirm.buttons.map((button) => button.text), ['Cancelar', 'Confirmar captura']);
  assert.equal(confirmPosts(h).length, 0);
  await h.act(async () => { confirm.buttons[0].onPress?.(); });
  assert.equal(confirmPosts(h).length, 0);
  assert.ok(h.registry.has('Lugar de instalación') && h.registry.get('Lugar de instalación')!.onChange);
});

test('4E: el error de validación del backend se muestra completo y el reporte sigue editable', async () => {
  const h = await openReport();
  h.env.confirmCaptureError = 'Faltan: Fecha de instalación, Lugar de instalación.';
  await h.press('Confirmar captura');
  await h.act(async () => { alertButton(h, '¿Confirmar captura?', 'Confirmar captura')(); });
  await h.flush();
  assert.equal(confirmPosts(h).length, 1);
  assert.ok(h.probe.log.includes('Alert:No se puede confirmar la captura'));
  assert.ok(h.text().includes('Confirmar captura'), 'sigue editable');
  assert.ok(!h.text().includes('LISTO PARA FIRMAS'));
});

test('4E: antes de confirmar se guarda lo último escrito; si no se puede guardar no se confirma', async () => {
  const h = await openReport();
  await type(h, 'Lugar de instalación', 'Bodega');
  h.env.failCaptureSave = true;
  await h.press('Confirmar captura');
  await h.act(async () => { alertButton(h, '¿Confirmar captura?', 'Confirmar captura')(); });
  await h.flush();
  assert.equal(confirmPosts(h).length, 0);
  assert.ok(h.text().includes('No se pudo guardar tu captura'));
});

test('4E: confirmación exitosa -> LISTO PARA FIRMAS, formulario de sólo lectura y galería no editable', async () => {
  const h = await openReport({ report: evidenceReport({ before: 2 }) });
  await type(h, 'Lugar de instalación', 'Bodega');
  await h.press('Confirmar captura');
  await h.act(async () => { alertButton(h, '¿Confirmar captura?', 'Confirmar captura')(); });
  await h.flush();
  assert.equal(confirmPosts(h).length, 1);
  assert.equal(patches(h).length, 1, 'el flush previo guardó el último valor antes de confirmar');
  const text = h.text();
  assert.ok(text.includes('LISTO PARA FIRMAS'));
  assert.ok(text.includes('Captura confirmada'));
  assert.ok(text.includes('Técnico responsable'));
  assert.ok(!text.includes('Al confirmar se valida'), 'la sección Confirmar captura desaparece');
  assert.equal(h.registry.get('Lugar de instalación')?.onChange, undefined, 'campos de sólo lectura');
  assert.ok(!text.includes('Agregar'), 'sin agregar foto');
  await h.press('Abrir foto Antes 1');
  assert.ok(!h.registry.has('Eliminar evidencia'), 'sin eliminar foto');
  assert.ok(h.text().includes('1 de 2 · Antes'), 'la galería sigue visible');
});

test('4E: tras confirmar no hay autosave ni cambios (los controles dejan de actuar)', async () => {
  const h = await openReport({ report: freshInstallationReport({ status: 'ready_for_signatures', performed_by_name_snapshot: 'Tec', performed_at: '2026-10-08T15:30:00+00:00' }) });
  assert.ok(h.text().includes('Técnico responsable'));
  await new Promise((resolve) => setTimeout(resolve, 900));
  await h.flush();
  assert.equal(patches(h).length, 0);
  assert.ok(!h.registry.has('¿Hubo incidencias?: Sí'), 'los selectores pasan a texto de sólo lectura');
});

test('4E: calibración no tiene confirmación de captura de reporte', async () => {
  const h = await createLifecycleHarness();
  h.env.detail = workOrderFixture({ status: 'received_signed' });
  h.env.params = { workOrderId: '72' };
  await h.mount();
  await h.flush();
  assert.ok(!h.text().includes('Confirmar captura'));
  assert.ok(h.probe.requests.every((request) => !/confirm-capture/.test(request)));
});
