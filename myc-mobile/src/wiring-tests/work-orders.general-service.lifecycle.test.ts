import assert from 'node:assert/strict';
import test from 'node:test';

import { createLifecycleHarness, type LifecycleHarness } from './support/lifecycle-harness';
import {
  equipmentFixture,
  generalServiceEquipmentFixture,
  installationProjection,
  freshInstallationReport,
  workOrderFixture,
} from './support/lab-fixtures';

// SG-3: Servicio General en MYC Mobile -- ejecuta el WorkOrdersScreen y los
// componentes LAB reales (React real + DOM mínimo). Sólo se sustituyen los
// puertos nativos, la sesión y la red.

const READ_ONLY = ['mobile.access', 'work_orders.read_organization', 'technical_reports.read'];
const NO_REPORT_ACCESS = ['mobile.access', 'work_orders.read_organization', 'work_orders.create'];

type OrderDetail = { id: number } & Record<string, unknown>;

async function openOrder(detail: OrderDetail, options: { permissions?: string[]; report?: unknown } = {}): Promise<LifecycleHarness> {
  const harness = await createLifecycleHarness();
  harness.env.detail = detail;
  harness.env.report = options.report ?? freshInstallationReport();
  harness.env.params = { workOrderId: String(detail.id) };
  if (options.permissions) harness.env.user = { ...harness.env.user, permissions: options.permissions };
  await harness.mount();
  await harness.flush();
  return harness;
}

const generalOrder = (overrides: Record<string, unknown> = {}) => workOrderFixture({ operational_category: 'general_service', ...overrides });
/** Captura técnica: la recepción ya está firmada. */
const generalInTechnical = (overrides: Record<string, unknown> = {}) => generalOrder({ status: 'received_signed', ...overrides });
const postsTo = (h: LifecycleHarness, pattern: RegExp) => h.probe.calls.filter((call) => call.method === 'POST' && pattern.test(call.path));
const CLIENT = { id: 7, operator_client_id: null, company: 'Cliente SG', address: 'Av. 1', attention: 'Ana', postal_code: '45000', city: 'GDL', state: 'Jal', is_active: true };

async function startCreation(h: LifecycleHarness) {
  await h.press('Generar orden');
  await h.act(async () => { h.registry.get('LabWorkOrderClientField')!.onSelect(CLIENT); });
}

// ---------------------------------------------------------------- SG-3A

test('SG-3A: la creación ofrece Categoría de servicio con Calibración por defecto', async () => {
  const h = await createLifecycleHarness();
  h.env.created = workOrderFixture();
  await h.mount(); await h.flush();
  await startCreation(h);
  assert.ok(h.text().includes('Categoría de servicio'));
  assert.ok(h.registry.has('Categoría de servicio: Calibración'));
  assert.ok(h.registry.has('Categoría de servicio: Servicio general'));
  assert.ok(h.text().includes('Vincular con cotización ERP'), 'calibración conserva el vínculo ERP');
  assert.ok(h.text().includes('Modalidad de trabajo'), 'calibración conserva group / equipment_by_equipment');
  await h.press('Crear OT y capturar equipos');
  const [created] = postsTo(h, /lab-work-orders$/);
  assert.equal(created.body.operational_category, 'calibration');
});

test('SG-3A: al elegir Servicio general se envía general_service y el vínculo ERP deja de ofrecerse', async () => {
  const h = await createLifecycleHarness();
  h.env.created = generalOrder();
  await h.mount(); await h.flush();
  await startCreation(h);
  await h.press('Categoría de servicio: Servicio general');
  assert.ok(!h.text().includes('Vincular con cotización ERP'), 'sin opción que termine en 409');
  assert.ok(!h.text().includes('Modalidad de trabajo'), 'Servicio General sólo admite el flujo por grupo');
  await h.press('Crear OT y capturar equipos');
  const [created] = postsTo(h, /lab-work-orders$/);
  assert.equal(created.body.operational_category, 'general_service');
  assert.equal(created.body.workflow_mode, 'group');
  assert.equal('service_order_id' in created.body, false);
});

test('SG-3A: volver a Calibración restablece el vínculo ERP y envía calibration', async () => {
  const h = await createLifecycleHarness();
  h.env.created = workOrderFixture();
  await h.mount(); await h.flush();
  await startCreation(h);
  await h.press('Categoría de servicio: Servicio general');
  await h.press('Categoría de servicio: Calibración');
  assert.ok(h.text().includes('Vincular con cotización ERP'));
  await h.press('Crear OT y capturar equipos');
  assert.equal(postsTo(h, /lab-work-orders$/)[0].body.operational_category, 'calibration');
});

test('SG-3A: sin technical_reports.capture el selector no aparece y la creación sigue siendo calibración', async () => {
  const h = await createLifecycleHarness();
  h.env.user = { ...h.env.user, permissions: ['mobile.access', 'work_orders.create', 'work_orders.read_organization'] };
  h.env.created = workOrderFixture();
  await h.mount(); await h.flush();
  await startCreation(h);
  assert.ok(!h.text().includes('Categoría de servicio'));
  await h.press('Crear OT y capturar equipos');
  assert.equal(postsTo(h, /lab-work-orders$/)[0].body.operational_category, 'calibration');
});

// ---------------------------------------------------------------- SG-3B

async function openEquipmentForm(h: LifecycleHarness) {
  await h.press('+ Añadir equipo');
}

test('SG-3B: calibración sigue mostrando cliente documental y modalidad metrológica', async () => {
  const h = await openOrder(workOrderFixture());
  await openEquipmentForm(h);
  const text = h.text();
  for (const expected of ['Instrumento', 'Cliente documental', 'Acreditado', 'Trazable', 'Vinculado', 'Servicio', 'Folio de informe']) {
    assert.ok(text.includes(expected), expected);
  }
  assert.ok(!text.includes('Equipo / producto'));
});

test('SG-3B: Servicio General no muestra modalidad, cliente documental ni folio de certificado', async () => {
  const h = await openOrder(generalOrder());
  await openEquipmentForm(h);
  const text = h.text();
  assert.ok(text.includes('Equipo / producto'));
  assert.ok(text.includes('Folio del reporte'));
  assert.ok(text.includes('Se asignará automáticamente'));
  assert.ok(text.includes('Colocado por el sistema'));
  assert.ok(!text.includes('Número de reporte'));
  assert.ok(text.includes('Condición general'));
  for (const forbidden of ['Acreditado', 'Trazable', 'Vinculado', 'Cliente documental', 'Folio de informe', 'Generado por el sistema', 'Empresa vinculada', 'MYCA', 'MYCT']) {
    assert.ok(!text.includes(forbidden), forbidden);
  }
});

test('SG-4C.1: el folio del reporte es un texto de sólo lectura colocado por el sistema (sin input)', async () => {
  const h = await openOrder(generalOrder());
  await openEquipmentForm(h);
  const folio = h.registry.get('Folio del reporte: Se asignará automáticamente');
  assert.ok(folio, 'campo visible con aviso de asignación automática');
  assert.equal(folio.onChange, undefined);
  assert.equal(folio.onChangeText, undefined);
  assert.equal(h.registry.get('Folio del reporte')?.onChange, undefined, 'no es un Field editable');
});

test('SG-4C.1: con reporte creado el folio mostrado es technical_report_folio, y el alta/edición no lo envía', async () => {
  const withReport = generalServiceEquipmentFixture({ ...installationProjection(), report_number: 'LEGADO-77' });
  const h = await openOrder(generalOrder({ equipment: [withReport] }));
  await h.act(async () => { await h.registry.get('pressable:Editar datos')!.onPress(); });
  const text = h.text();
  assert.ok(text.includes('MYC-IN10-26-0001'));
  assert.ok(text.includes('Colocado por el sistema'));
  assert.ok(!text.includes('Se asignará automáticamente'));
  assert.ok(!text.includes('LEGADO-77'), 'report_number no es la autoridad del folio');
  await h.act(async () => { h.registry.get('Marca')!.onChange('Otra marca'); });
  await h.press('Guardar cambios');
  const [patch] = h.probe.calls.filter((call) => call.method === 'PATCH' && /equipment\/289\/configured$/.test(call.path));
  assert.ok(patch);
  assert.deepEqual(Object.keys(patch.body as object), ['equipment']);
  const equipment = (patch.body as { equipment: Record<string, unknown> }).equipment;
  assert.ok(!('report_number' in equipment));
  assert.doesNotMatch(JSON.stringify(patch.body), /MYC-IN|LEGADO|technical_report/);
});

test('SG-3B: alta calibración envía service con modalidad; Servicio General sólo envía el equipo (service_type null)', async () => {
  const fill = async (h: LifecycleHarness, instrumentLabel: string) => {
    await h.act(async () => {
      h.registry.get(instrumentLabel)!.onChange('Equipo nuevo');
      h.registry.get('Marca')!.onChange('MYC');
      h.registry.get('Identificación')!.onChange('ID-9');
      h.registry.get('Serie')!.onChange('SER-9');
    });
  };

  const calibration = await openOrder(workOrderFixture());
  await openEquipmentForm(calibration);
  await fill(calibration, 'Instrumento');
  await calibration.press('Guardar equipo');
  const [calibrationPost] = postsTo(calibration, /equipment\/configured$/);
  assert.equal(calibrationPost.body.service.service_type, 'accredited');
  assert.equal(calibrationPost.body.equipment.instrument, 'Equipo nuevo');

  const general = await openOrder(generalOrder());
  await openEquipmentForm(general);
  await fill(general, 'Equipo / producto');
  await general.press('Guardar equipo');
  const [generalPost] = postsTo(general, /equipment\/configured$/);
  assert.deepEqual(Object.keys(generalPost.body), ['equipment']);
  assert.equal(generalPost.body.equipment.instrument, 'Equipo nuevo');
  assert.doesNotMatch(JSON.stringify(generalPost.body), /service|certificate|linked|installation/);
  assert.equal(generalPost.body.equipment.expected_edit_version, 1);
});

// ---------------------------------------------------------------- SG-3C

test('SG-3C: la tarjeta de calibración conserva modalidad/folio y NO usa reportes técnicos', async () => {
  const h = await openOrder(workOrderFixture());
  const text = h.text();
  assert.ok(text.includes('ACREDITADO'));
  assert.ok(text.includes('MYCA-10-26-0001'));
  assert.ok(!text.includes('Seleccionar reporte'));
  assert.ok(!text.includes('SIN REPORTE'));
});

test('SG-3C: en recepción (draft) Servicio General no ofrece reportes ni muestra modalidad/folio de certificado', async () => {
  const h = await openOrder(generalOrder());
  const text = h.text();
  assert.ok(text.includes('Servicio general'));
  for (const forbidden of ['Seleccionar reporte', 'Abrir reporte', 'SIN REPORTE', 'Seleccionar hoja', 'Abrir hoja', 'ACREDITADO', 'TRAZABLE', 'VINCULADO', 'Sin asignar', 'MYCA', 'MYCT', 'Folio:']) {
    assert.ok(!text.includes(forbidden), forbidden);
  }
});

test('SG-3C: en captura técnica Servicio General usa TechnicalReport: SIN REPORTE y Seleccionar reporte', async () => {
  const h = await openOrder(generalInTechnical());
  const text = h.text();
  assert.ok(text.includes('SIN REPORTE'));
  assert.ok(text.includes('Servicio general'));
  assert.ok(text.includes('Seleccionar reporte'));
  for (const forbidden of ['Seleccionar hoja', 'Abrir hoja', 'ACREDITADO', 'TRAZABLE', 'VINCULADO', 'MYCA', 'MYCT', 'Folio:']) {
    assert.ok(!text.includes(forbidden), forbidden);
  }
});

test('SG-3C: en captura técnica, calibración conserva la hoja y Servicio General muestra reportes sin montar LabTechnicalCapture', async () => {
  const calibration = await openOrder(workOrderFixture({ status: 'received_signed' }));
  assert.ok(calibration.text().includes('Seleccionar hoja'));
  assert.ok(!calibration.text().includes('Seleccionar reporte'));
  assert.ok(calibration.probe.log.some((line) => line.startsWith('LTC mount')));

  const general = await openOrder(generalOrder({ status: 'received_signed' }));
  assert.ok(general.text().includes('Reporte técnico por equipo'));
  assert.ok(general.text().includes('Seleccionar reporte'));
  assert.ok(!general.text().includes('Seleccionar hoja'));
  assert.ok(!general.probe.log.some((line) => line.startsWith('LTC mount')));
});

test('SG-3C: un reporte existente se muestra con folio y estado, y la acción es Abrir reporte', async () => {
  const h = await openOrder(generalInTechnical({ equipment: [generalServiceEquipmentFixture(installationProjection())] }));
  const text = h.text();
  assert.ok(text.includes('MYC-IN10-26-0001'));
  assert.ok(text.includes('BORRADOR'));
  assert.ok(text.includes('Abrir reporte'));
  assert.ok(!text.includes('Seleccionar reporte'));
});

// ---------------------------------------------------------------- SG-3D

test('SG-3D: el selector habilita Instalación y deja los demás como próximamente, sin POST', async () => {
  const h = await openOrder(generalInTechnical());
  await h.press('Seleccionar reporte');
  assert.ok(h.text().includes('Próximamente'));
  assert.ok(!h.registry.get('Tipo de reporte: Instalación')!.disabled);
  for (const title of ['Verificación', 'Reparación', 'Mantenimiento', 'Venta']) {
    const option = h.registry.get(`Tipo de reporte: ${title}`)!;
    assert.equal(option.disabled, true, title);
    // Aun si el toque llegara al handler, no se emite ninguna petición.
    await h.act(async () => { await option.onPress(); });
  }
  assert.equal(postsTo(h, /technical-report$/).length, 0);
});

test('SG-3D/3E: crear Instalación llama al endpoint, refresca la OT y la tarjeta muestra MYC-IN / estado', async () => {
  const h = await openOrder(generalInTechnical());
  // Backend ya proyecta el reporte al refrescar la OT.
  h.env.detail = generalInTechnical({ equipment: [generalServiceEquipmentFixture(installationProjection())] });
  await h.press('Seleccionar reporte');
  await h.press('Tipo de reporte: Instalación');

  const [create] = postsTo(h, /equipment\/289\/technical-report$/);
  assert.equal(create.path, '/mobile/v1/technician/lab-work-orders/72/equipment/289/technical-report');
  assert.deepEqual(create.body, { report_type: 'installation' });
  const text = h.text();
  assert.ok(text.includes('MYC-IN10-26-0001'));
  assert.ok(text.includes('BORRADOR'));
  assert.ok(text.includes('Abrir reporte'));
  assert.ok(!text.includes('Elige el tipo de reporte técnico'), 'el selector se cierra');
  assert.ok(h.probe.published.some((event) => event.event_type === 'work_order.updated' && event.work_order_id === 72));
});

test('SG-3D: un error del backend al crear el reporte se informa y deja el selector abierto', async () => {
  const h = await openOrder(generalInTechnical());
  h.env.failTechnicalReportCreate = true;
  await h.press('Seleccionar reporte');
  await h.press('Tipo de reporte: Instalación');
  assert.ok(h.probe.log.includes('Alert:No fue posible crear el reporte'));
  assert.ok(h.text().includes('Elige el tipo de reporte técnico'));
  assert.ok(!h.text().includes('MYC-IN'));
  assert.equal(h.probe.published.length, 0, 'sin cambio local no se publica nada');
});

// ---------------------------------------------------------------- SG-3E / SG-4A

test('SG-3E/4A: Abrir reporte muestra el encabezado de sólo lectura desde el snapshot, sin duplicarlo en la captura', async () => {
  const h = await openOrder(generalInTechnical({ equipment: [generalServiceEquipmentFixture(installationProjection())] }));
  await h.press('Abrir reporte');
  const text = h.text();
  assert.ok(text.includes('OT 6072 · EQUIPO 1'));
  assert.ok(text.includes('Reporte de instalación'));
  assert.ok(text.includes('MYC-IN10-26-0001'));
  assert.ok(text.includes('BORRADOR'));
  assert.ok(text.includes('Cliente SG'));
  assert.ok(text.includes('Báscula'));
  assert.ok(h.probe.requests.includes('GET /mobile/v1/technician/lab-work-orders/72/equipment/289/technical-report'));
});

// ---------------------------------------------------------------- permisos

test('permisos: lectura sin captura puede abrir un reporte pero no crearlo', async () => {
  const empty = await openOrder(generalInTechnical(), { permissions: READ_ONLY });
  assert.ok(!empty.text().includes('Seleccionar reporte'));
  assert.ok(empty.text().includes('SIN REPORTE'));

  const existing = await openOrder(generalInTechnical({ equipment: [generalServiceEquipmentFixture(installationProjection())] }), { permissions: READ_ONLY });
  assert.ok(existing.text().includes('Abrir reporte'));
});

test('permisos: un actor sin permisos de reportes no ve acción de creación ni de apertura', async () => {
  const empty = await openOrder(generalInTechnical(), { permissions: NO_REPORT_ACCESS });
  assert.ok(!empty.text().includes('Seleccionar reporte'));
  const existing = await openOrder(generalInTechnical({ equipment: [generalServiceEquipmentFixture(installationProjection())] }), { permissions: NO_REPORT_ACCESS });
  assert.ok(!existing.text().includes('Abrir reporte'));
});

test('permisos: technical_reports.capture habilita crear', async () => {
  const h = await openOrder(generalInTechnical(), { permissions: ['mobile.access', 'work_orders.read_organization', 'technical_reports.capture'] });
  assert.ok(h.text().includes('Seleccionar reporte'));
});

// ---------------------------------------------------------------- lifecycle completo

const SIGNATURES = { client: { signer_name: 'Cliente', signature_data_url: 'data:image/png;base64,AA==' }, technician: { signer_name: 'Tec', signature_data_url: 'data:image/png;base64,AA==' } };

/** Mismo recorrido de recepción para ambas categorías: capture -> firmas -> captura técnica. */
async function receiveThroughSignatureModal(h: LifecycleHarness, signedDetail: OrderDetail) {
  assert.ok(h.text().includes('Equipos'), 'paso de equipos');
  await h.press('Continuar a recepción de equipos');
  assert.ok(h.text().includes('RECEPCIÓN DE EQUIPOS'), 'recepción de equipos');
  await h.press('Continuar a firmas');
  const flow = h.registry.get('MobileSignatureFlow');
  assert.ok(flow, 'se reutiliza el flujo/modal de firmas actual');
  h.env.signed = signedDetail;
  await h.act(async () => { await flow.onSubmit(SIGNATURES, flow.currentContextId); });
  assert.ok(h.probe.calls.some((call) => call.method === 'POST' && /\/lab-work-orders\/72\/signatures$/.test(call.path)));
  await h.act(async () => { h.registry.get('MobileSignatureFlow')!.onComplete(); });
  assert.ok(h.text().includes('Recepción firmada'));
  await h.press('Continuar a captura técnica');
}

test('LIFECYCLE general_service: draft -> recepción firmada -> captura técnica -> Seleccionar reporte -> Installation', async () => {
  const draft = generalOrder();
  const h = await openOrder(draft);
  // draft: el reporte NO es accesible (no sirve como bypass de la recepción).
  assert.ok(!h.text().includes('Seleccionar reporte'));

  await receiveThroughSignatureModal(h, generalInTechnical());
  assert.ok(h.text().includes('Reporte técnico por equipo'), 'captura técnica de Servicio General');
  assert.ok(h.text().includes('Seleccionar reporte'));
  assert.ok(!h.probe.log.some((line) => line.startsWith('LTC mount')), 'no se monta la captura de hojas');

  h.env.detail = generalInTechnical({ status: 'in_progress', equipment: [generalServiceEquipmentFixture(installationProjection())] });
  await h.press('Seleccionar reporte');
  await h.press('Tipo de reporte: Instalación');
  assert.deepEqual(postsTo(h, /technical-report$/).map((call) => call.body), [{ report_type: 'installation' }]);
  assert.ok(h.text().includes('MYC-IN10-26-0001'));
  assert.ok(h.text().includes('Abrir reporte'));
});

test('LIFECYCLE calibration: mismo flujo/modal de recepción y la captura técnica sigue usando FieldSheet', async () => {
  const draft = workOrderFixture({ equipment: [equipmentFixture({ field_sheet_id: 91, field_sheet_status: 'in_progress' })] });
  const h = await openOrder(draft);
  assert.ok(h.text().includes('ACREDITADO'));
  await receiveThroughSignatureModal(h, workOrderFixture({ status: 'received_signed', equipment: draft.equipment }));
  assert.ok(h.text().includes('Servicio, folio y hoja por equipo'));
  assert.ok(h.text().includes('Abrir hoja'));
  assert.ok(!h.text().includes('Seleccionar reporte'));
  assert.ok(h.probe.log.some((line) => line.startsWith('LTC mount')));
});

test('LIFECYCLE: Servicio General en recepción firmada o en captura se enruta a captura técnica, nunca queda inalcanzable', async () => {
  for (const status of ['received_signed', 'in_progress']) {
    const h = await openOrder(generalOrder({ status }));
    assert.ok(h.text().includes('Reporte técnico por equipo'), status);
  }
});

// ---------------------------------------------------------------- no regresión

test('no regresión: una OT sin operational_category (histórica) se comporta como calibración', async () => {
  const { operational_category: _removed, ...legacy } = workOrderFixture();
  const h = await openOrder(legacy);
  assert.ok(h.text().includes('ACREDITADO'));
  assert.ok(!h.text().includes('Seleccionar reporte'));
  assert.equal(equipmentFixture().service_type, 'accredited');
});
