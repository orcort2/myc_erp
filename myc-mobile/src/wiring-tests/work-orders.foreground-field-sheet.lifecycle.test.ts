import assert from 'node:assert/strict';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { createLifecycleHarness, type LifecycleHarness } from './support/lifecycle-harness';

// Lifecycle real (React reconciler + WorkOrdersScreen y LabTechnicalCapture
// reales): background -> foreground dentro del MISMO proceso. Cold start /
// process kill de iOS queda fuera de alcance a propósito (sin persistencia).

const here = dirname(fileURLToPath(import.meta.url));
const FOREGROUND = { event_type: 'app.foreground', source: 'foreground' };

function equipmentFixture(overrides: Record<string, unknown> = {}) {
  return {
    id: 289, position: 1, instrument: 'Manómetro', brand: 'B', identification: 'ID', serial_number: 'S1', model: null,
    report_number: null, is_good_condition: true, service_type: 'accredited', linked_company_id: null,
    linked_company_name_snapshot: null, linked_company_prefix_snapshot: null, certificate_folio: 'F-1',
    automatic_certificate_folio: null, folio_status: 'authorized', folio_ticket_id: null, field_sheet_id: 91,
    field_sheet_status: 'in_progress', certificate_client_mode: 'order', final_lab_client_id: null,
    final_client_company_snapshot: null, final_client_address_snapshot: null, final_client_attention_snapshot: null,
    ...overrides,
  };
}

function workOrderFixture(overrides: Record<string, unknown> = {}) {
  const id = (overrides.id as number | undefined) ?? 72;
  const status = (overrides.status as string | undefined) ?? 'in_progress';
  const workflowMode = (overrides.workflow_mode as string | undefined) ?? 'group';
  return {
    id, folio: 6000 + id, root_work_order_id: 72, previous_work_order_id: null, sequence_number: 1,
    signature_session_id: 1, signature_scope: 'group', reception_date: '2026-09-17', departure_date: null,
    client_name: 'Cliente base', address: 'A', contact_name: 'N', contact_phone: null, contact_email: null,
    postal_code: null, city: null, state_name: null, purchase_order: null, notes: null, status,
    workflow_mode: workflowMode, lab_client_id: 1, revision_number: 1, edit_version: 1, reopen_ticket_id: null,
    signature_required: true, signature_preserved: false, partial_close_ticket_id: null, cancellation_reason: null,
    previous_status: null, equipment: [equipmentFixture()],
    related_work_orders: [{ id, folio: 6000 + id, sequence_number: 1, status, workflow_mode: workflowMode, signature_session_id: 1, equipment_count: 1 }],
    pending_signature_review: { sensitive_fields: [], requires_new_signature: false },
    ...overrides,
  };
}

const sheetFixture = { id: 91, status: 'in_progress', revision_number: 1, is_current: true, supersedes_field_sheet_id: null, template_key: 'x', template_definition: { template_key: 'x', blocks: [], result_sections: [] }, capture_values: {}, results_rows: [], work_order_number: 6072, company: 'C' };

async function openOrder(detail: any, navigation: string[] = [], sheet: Record<string, unknown> = {}): Promise<LifecycleHarness> {
  const harness = await createLifecycleHarness();
  harness.env.detail = detail;
  harness.env.sheet = { ...structuredClone(sheetFixture), ...sheet };
  harness.env.params = { workOrderId: String(detail.id) };
  await harness.mount();
  await harness.flush();
  for (const label of navigation) await harness.press(label);
  return harness;
}
const mounts = (h: LifecycleHarness) => h.probe.log.filter((l) => l.startsWith('LTC'));
const sheetOpen = (h: LifecycleHarness) => h.text().includes('EQUIPO 1');

test('group/in_progress + Captura Técnica + FieldSheet abierta: foreground conserva la misma hoja', async () => {
  const h = await openOrder(workOrderFixture());
  await h.press('Abrir hoja');
  assert.ok(sheetOpen(h));
  await h.emit(FOREGROUND);
  assert.ok(sheetOpen(h));
  assert.deepEqual(mounts(h), ['LTC mount ltc1']);
});

test('OT ready_to_close revisada desde "Revisar captura técnica": foreground NO expulsa de la hoja abierta', async () => {
  const h = await openOrder(workOrderFixture({ status: 'ready_to_close' }), ['Revisar captura técnica']);
  await h.press('Abrir hoja');
  assert.ok(sheetOpen(h));
  await h.emit(FOREGROUND);
  assert.ok(sheetOpen(h), 'la hoja debe seguir abierta');
  assert.deepEqual(mounts(h), ['LTC mount ltc1'], 'LabTechnicalCapture no debe desmontarse');
});

test('OT reabierta (draft, firma preservada) en Captura Técnica: foreground conserva la hoja', async () => {
  const detail = workOrderFixture({ status: 'draft', signature_required: false, signature_preserved: true });
  const h = await openOrder(detail, ['Continuar proceso']);
  await h.press('Abrir hoja');
  assert.ok(sheetOpen(h));
  await h.emit(FOREGROUND);
  assert.ok(sheetOpen(h));
  assert.deepEqual(mounts(h), ['LTC mount ltc1']);
});

test('"Volver a equipos" limpia el contexto: foreground no reabre la hoja', async () => {
  const h = await openOrder(workOrderFixture());
  await h.press('Abrir hoja');
  assert.ok(sheetOpen(h));
  await h.press('Volver a equipos');
  assert.ok(!sheetOpen(h));
  await h.emit(FOREGROUND);
  assert.ok(!sheetOpen(h), 'no debe reabrir una hoja que el técnico cerró');
});

test('valores locales no confirmados sobreviven al foreground (mismo componente, sin remount)', async () => {
  // LAB EXTERNO usa el contrato común completo: expone campos editables sin plantilla.
  const detail = workOrderFixture({ equipment: [equipmentFixture({ service_type: 'linked' })] });
  const h = await openOrder(detail, [], { template_key: 'lab_externo', template_definition: { kind: 'lab_externo', groups: [] } });
  await h.press('Abrir hoja');
  // Una hoja existente abre en consulta; el técnico pasa a edición.
  await h.press('Editar');
  const textLabel = [...h.registry.entries()].find(([, props]) => typeof props.onChange === 'function' && typeof props.value === 'string')?.[0];
  assert.ok(textLabel, 'la hoja debe exponer al menos un campo de texto editable');
  await h.act(async () => { h.registry.get(textLabel)!.onChange('Valor sin confirmar'); });
  assert.equal(h.registry.get(textLabel)!.value, 'Valor sin confirmar');
  await h.emit(FOREGROUND);
  assert.equal(h.registry.get(textLabel)!.value, 'Valor sin confirmar');
  assert.deepEqual(mounts(h), ['LTC mount ltc1']);
});

test('LAB EXTERNO abierta: foreground conserva la hoja sin volver al selector', async () => {
  const detail = workOrderFixture({ equipment: [equipmentFixture({ service_type: 'linked' })] });
  const h = await openOrder(detail);
  await h.press('Abrir hoja');
  assert.ok(sheetOpen(h));
  assert.ok(h.text().includes('LAB EXTERNO'));
  await h.emit(FOREGROUND);
  assert.ok(sheetOpen(h));
  assert.ok(h.text().includes('LAB EXTERNO'));
  assert.deepEqual(mounts(h), ['LTC mount ltc1']);
});

test('status terminal de backend sigue mandando: la hoja se cierra y el paso es completed', async () => {
  const h = await openOrder(workOrderFixture({ status: 'ready_to_close' }), ['Revisar captura técnica']);
  await h.press('Abrir hoja');
  h.env.detail = workOrderFixture({ status: 'completed' });
  await h.emit(FOREGROUND);
  assert.ok(!sheetOpen(h));
  assert.deepEqual(mounts(h), ['LTC mount ltc1', 'LTC unmount ltc1']);
});

test('equipo retirado por backend: no queda hoja fantasma y se avisa', async () => {
  const h = await openOrder(workOrderFixture());
  await h.press('Abrir hoja');
  h.env.detail = workOrderFixture({ equipment: [equipmentFixture({ id: 300, position: 2, field_sheet_id: null })] });
  await h.emit(FOREGROUND);
  assert.ok(!sheetOpen(h));
  assert.ok(h.probe.log.includes('Alert:La hoja cambió'));
});

test('hoja reemplazada por otra revisión en backend: se reconcilia explícitamente', async () => {
  const h = await openOrder(workOrderFixture());
  await h.press('Abrir hoja');
  h.env.detail = workOrderFixture({ equipment: [equipmentFixture({ field_sheet_id: 92 })] });
  await h.emit(FOREGROUND);
  assert.ok(!sheetOpen(h));
  assert.ok(h.probe.log.includes('Alert:La hoja cambió'));
});

test('refresh de la misma OT con metadata nueva conserva la hoja', async () => {
  const h = await openOrder(workOrderFixture());
  await h.press('Abrir hoja');
  h.env.detail = workOrderFixture({ client_name: 'Cliente actualizado', notes: 'nota nueva', edit_version: 2 });
  await h.emit(FOREGROUND);
  assert.ok(sheetOpen(h));
  assert.deepEqual(mounts(h), ['LTC mount ltc1']);
});

test('cambio real de OT no reutiliza equipo/hoja de la anterior', async () => {
  const h = await openOrder(workOrderFixture());
  await h.press('Abrir hoja');
  assert.ok(sheetOpen(h));
  h.env.details[73] = workOrderFixture({ id: 73, equipment: [equipmentFixture({ id: 500, field_sheet_id: null, field_sheet_status: null })] });
  await h.navigateTo(73);
  assert.ok(!sheetOpen(h), 'la OT nueva no debe mostrar la hoja de la anterior');
  assert.ok(h.probe.log.includes('LTC unmount ltc1'));
});

test('eventos foreground rápidos: una respuesta vieja no gana a la más reciente', async () => {
  const h = await openOrder(workOrderFixture());
  await h.press('Abrir hoja');
  let release!: () => void;
  // La siguiente lectura (primer foreground) queda retenida con un estado
  // terminal que ya es viejo cuando por fin llega.
  h.env.detailGates[1] = new Promise<void>((resolve) => { release = resolve; });
  h.env.detail = workOrderFixture({ status: 'completed' });
  await h.emitBurst([FOREGROUND, FOREGROUND], (index) => {
    // Tras el primer evento ya está en vuelo; backend refleja la OT vigente
    // antes del segundo, y la respuesta retenida se libera al final.
    if (index === 0) h.env.detail = workOrderFixture();
    if (index === 1) release();
  });
  await h.flush();
  assert.ok(sheetOpen(h), 'la respuesta vieja (completed) no puede cerrar la hoja');
  assert.deepEqual(mounts(h), ['LTC mount ltc1']);
});

function gate() {
  let release!: () => void;
  let fail!: () => void;
  const promise = new Promise<void>((resolve, reject) => { release = resolve; fail = () => reject(new Error('red')); });
  return { promise, release, fail };
}

test('reconciliación diferida: detalle incompatible durante busy no cierra; al terminar busy se valida contra el último detalle', async () => {
  const h = await openOrder(workOrderFixture());
  await h.press('Abrir hoja');
  await h.press('Editar');
  const patch = gate();
  h.env.sheetWriteGates[0] = patch.promise;
  await h.observe(async ({ fire }) => {
    // El backend ya reemplazó la hoja 91 por la 92 mientras este guardado sigue en vuelo.
    h.env.detail = workOrderFixture({ equipment: [equipmentFixture({ field_sheet_id: 92 })] });
    await fire(FOREGROUND);
    assert.ok(sheetOpen(h), 'durante busy no se reconcilia');
    patch.release();
  }, 'Guardar borrador');
  assert.ok(!sheetOpen(h), 'al terminar busy se valida contra el último snapshot');
  assert.ok(h.probe.log.includes('Alert:La hoja cambió'));
});

test('reconciliación diferida: si al terminar busy el último snapshot es compatible, la hoja se conserva', async () => {
  const h = await openOrder(workOrderFixture());
  await h.press('Abrir hoja');
  await h.press('Editar');
  const patch = gate();
  h.env.sheetWriteGates[0] = patch.promise;
  await h.observe(async ({ fire }) => {
    h.env.detail = workOrderFixture({ equipment: [equipmentFixture({ field_sheet_id: 92 })] });
    await fire(FOREGROUND);
    h.env.detail = workOrderFixture();
    await fire(FOREGROUND);
    patch.release();
  }, 'Guardar borrador');
  assert.ok(sheetOpen(h));
  assert.ok(!h.probe.log.includes('Alert:La hoja cambió'));
});

const externalWithoutSheet = () => workOrderFixture({ equipment: [equipmentFixture({ service_type: 'linked', field_sheet_id: null, field_sheet_status: null })] });
const externalWithSheet = () => workOrderFixture({ equipment: [equipmentFixture({ service_type: 'linked' })] });
const externalSheet = { template_key: 'lab_externo', template_definition: { kind: 'lab_externo', groups: [] } };

test('A. creación local en curso + snapshot null anterior: no se cierra y la confirmación lo respalda', async () => {
  const h = await openOrder(externalWithoutSheet(), [], externalSheet);
  const post = gate(); const staleForeground = gate(); const confirmation = gate();
  h.env.sheetWriteGates[0] = post.promise;
  h.env.detailGates[1] = staleForeground.promise; // foreground, payload ANTERIOR (equipo sin hoja)
  h.env.detailGates[2] = confirmation.promise; // refresh propio tras crear
  await h.observe(async ({ fire, settle }) => {
    await fire(FOREGROUND); // snapshot con field_sheet_id null queda retenido
    h.env.detail = externalWithSheet();
    post.release(); await settle();
    assert.ok(sheetOpen(h), 'hoja recién creada abierta');
    staleForeground.release(); await settle(); // llega el snapshot viejo (null)
    assert.ok(sheetOpen(h), 'un null anterior a la creación local no prueba nada');
    confirmation.release(); await settle();
  }, 'Seleccionar hoja');
  assert.ok(sheetOpen(h));
  assert.ok(!h.probe.log.includes('Alert:La hoja cambió'));
});

test('A2. creación local sin confirmar (el refresh propio falló) + snapshot null viejo con busy ya en false: sigue abierta', async () => {
  const h = await openOrder(externalWithoutSheet(), [], externalSheet);
  const staleForeground = gate(); const failedRefresh = gate();
  h.env.detailGates[1] = staleForeground.promise;
  h.env.detailGates[2] = failedRefresh.promise;
  await h.observe(async ({ fire, settle }) => {
    await fire(FOREGROUND);
    failedRefresh.fail(); await settle(); // termina la creación (busy=false) sin confirmación
    assert.ok(sheetOpen(h));
    staleForeground.release(); await settle();
    assert.ok(sheetOpen(h), 'sin confirmación, un null anterior no puede cerrar la hoja recién creada');
  }, 'Seleccionar hoja');
  assert.ok(sheetOpen(h));
  assert.ok(!h.probe.log.includes('Alert:La hoja cambió'));
});

test('B. creación ya confirmada + snapshot posterior con field_sheet_id null: el contexto se invalida', async () => {
  const h = await openOrder(externalWithoutSheet(), [], externalSheet);
  h.env.detail = externalWithSheet();
  await h.press('Seleccionar hoja');
  assert.ok(sheetOpen(h));
  h.env.detail = externalWithoutSheet(); // otro actor retiró/descartó la hoja
  await h.emit(FOREGROUND);
  assert.ok(!sheetOpen(h), 'no debe quedar una hoja fantasma');
  assert.ok(h.probe.log.includes('Alert:La hoja cambió'));
});

test('carrera A→B: la respuesta tardía del foreground de la OT A nunca vuelve a aplicar workOrder/step/contexto', async () => {
  const two = (id: number, status = 'in_progress') => workOrderFixture({
    id, status,
    related_work_orders: [72, 73].map((rid) => ({ id: rid, folio: 6000 + rid, sequence_number: 1, status: 'in_progress', workflow_mode: 'group', signature_session_id: 1, equipment_count: 1 })),
  });
  const h = await openOrder(two(72));
  h.env.details[73] = two(73);
  await h.press('Abrir hoja');
  const lateA = gate();
  h.env.detailGates[1] = lateA.promise;
  h.env.details[72] = two(72, 'completed'); // el payload retenido de A ya es terminal
  await h.observe(async ({ fire, tapRelated, settle }) => {
    await fire(FOREGROUND); // GET de A en vuelo
    await tapRelated(6073); // el técnico cambia a B
    assert.ok(h.text().includes('OT LAB · 6073'), 'B es la OT abierta');
    lateA.release(); await settle(); // responde tarde A
  });
  assert.ok(h.text().includes('OT LAB · 6073'), 'A no reemplaza a B');
  assert.ok(!h.text().includes('Grupo histórico'), 'el status terminal de A no se aplica a B');
  assert.ok(!sheetOpen(h));
});

test('carrera A→B→A: la lectura vieja de A no pisa la lectura fresca de A al volver', async () => {
  const two = (id: number, status = 'in_progress') => workOrderFixture({
    id, status,
    related_work_orders: [72, 73].map((rid) => ({ id: rid, folio: 6000 + rid, sequence_number: 1, status: 'in_progress', workflow_mode: 'group', signature_session_id: 1, equipment_count: 1 })),
  });
  const h = await openOrder(two(72));
  h.env.details[73] = two(73);
  const lateA = gate();
  h.env.detailGates[1] = lateA.promise;
  h.env.details[72] = two(72, 'completed'); // lectura vieja retenida
  await h.observe(async ({ fire, tapRelated, settle }) => {
    await fire(FOREGROUND);
    await tapRelated(6073);
    h.env.details[72] = two(72); // lectura fresca de A al volver
    await tapRelated(6072);
    assert.ok(h.text().includes('OT LAB · 6072'));
    lateA.release(); await settle();
  });
  assert.ok(!h.text().includes('Grupo histórico'), 'la respuesta vieja de A no puede cerrar la OT');
  assert.ok(h.text().includes('Captura técnica'));
});

test('cold start / process kill queda fuera de alcance: no existe persistencia durable del contexto', async () => {
  const { readFileSync } = await import('node:fs');
  const files = ['app/(technician)/work-orders.tsx', 'src/components/lab/LabTechnicalCapture.tsx', 'src/services/field-sheet-context.ts'];
  for (const file of files) {
    const source = readFileSync(resolve(here, '../..', file), 'utf8');
    assert.doesNotMatch(source, /AsyncStorage|SecureStore|writeSession|localStorage/, file);
  }
});
