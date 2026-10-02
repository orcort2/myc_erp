import assert from 'node:assert/strict';
import test from 'node:test';

import {
  createFieldSheetAutosave,
  mergeAuthoritativeSheetFields,
  mergeAutosavedSheet,
  shouldApplySaveResult,
  type AutosaveStatus,
} from './field-sheet-autosave';
import type { LabFieldSheet } from '@/src/types/lab-work-order';

type Values = Record<string, unknown>;

/** Temporizador falso: se dispara a mano con tick(). */
function fakeTimers() {
  let next = 1;
  const pending = new Map<number, () => void>();
  return {
    setTimer: (callback: () => void) => { const id = next++; pending.set(id, callback); return id; },
    clearTimer: (handle: unknown) => { pending.delete(handle as number); },
    tick() { const callbacks = [...pending.values()]; pending.clear(); callbacks.forEach((cb) => cb()); },
    get size() { return pending.size; },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

const settle = () => new Promise((resolve) => setImmediate(resolve));

function harness(save: (values: Values) => Promise<Values>) {
  const timers = fakeTimers();
  const saved: Values[] = [];
  const statuses: AutosaveStatus[] = [];
  const autosave = createFieldSheetAutosave<Values, Values>({
    save,
    onSaved: (result) => saved.push(result),
    onStatusChange: (status) => statuses.push(status),
    setTimer: timers.setTimer,
    clearTimer: timers.clearTimer,
  });
  return { autosave, timers, saved, statuses };
}

test('múltiples onChange rápidos producen una sola operación debounced con el último valor', async () => {
  const calls: Values[] = [];
  const { autosave, timers } = harness(async (values) => { calls.push(values); return values; });
  autosave.change({ brand: 'W' });
  autosave.change({ brand: 'Wi' });
  autosave.change({ brand: 'Winters' });
  assert.equal(timers.size, 1);
  assert.equal(calls.length, 0);
  timers.tick();
  await settle();
  assert.deepEqual(calls, [{ brand: 'Winters' }]);
  assert.equal(autosave.isDirty(), false);
  assert.equal(autosave.getStatus(), 'saved');
});

test('blur (flush) guarda de inmediato lo pendiente sin esperar el debounce', async () => {
  const calls: Values[] = [];
  const { autosave, timers } = harness(async (values) => { calls.push(values); return values; });
  autosave.change({ observations: 'abc' });
  assert.equal(await autosave.flush(), true);
  assert.deepEqual(calls, [{ observations: 'abc' }]);
  assert.equal(timers.size, 0);
});

test('flush sin cambios pendientes no guarda nada', async () => {
  const calls: Values[] = [];
  const { autosave } = harness(async (values) => { calls.push(values); return values; });
  assert.equal(await autosave.flush(), true);
  assert.equal(calls.length, 0);
});

test('mientras un guardado está en vuelo, un cambio nuevo queda dirty y dispara otro guardado en orden', async () => {
  const first = deferred<Values>();
  const calls: Values[] = [];
  const { autosave, timers, saved } = harness((values) => {
    calls.push(values);
    return calls.length === 1 ? first.promise : Promise.resolve(values);
  });
  autosave.change({ brand: 'Winter' });
  timers.tick();
  await settle();
  assert.equal(calls.length, 1);

  autosave.change({ brand: 'Winters' }); // se escribe mientras guarda
  assert.equal(autosave.isDirty(), true);
  timers.tick(); // el debounce no abre un segundo PATCH concurrente
  await settle();
  assert.equal(calls.length, 1);

  first.resolve({ brand: 'Winter' });
  await settle();
  assert.equal(autosave.isDirty(), true, 'el guardado viejo no limpia el cambio nuevo');
  timers.tick();
  await settle();
  assert.deepEqual(calls, [{ brand: 'Winter' }, { brand: 'Winters' }]);
  assert.deepEqual(saved, [{ brand: 'Winter' }, { brand: 'Winters' }]);
  assert.equal(autosave.isDirty(), false);
});

test('flush espera al guardado en vuelo y luego guarda el cambio más nuevo', async () => {
  const first = deferred<Values>();
  const calls: Values[] = [];
  const { autosave, timers } = harness((values) => {
    calls.push(values);
    return calls.length === 1 ? first.promise : Promise.resolve(values);
  });
  autosave.change({ a: 1 });
  timers.tick();
  await settle();
  autosave.change({ a: 2 });
  const flushed = autosave.flush();
  first.resolve({ a: 1 });
  assert.equal(await flushed, true);
  assert.deepEqual(calls, [{ a: 1 }, { a: 2 }]);
  assert.equal(autosave.isDirty(), false);
});

test('autosave fallido: sigue dirty, reporta error y el siguiente flush reintenta', async () => {
  let fail = true;
  const calls: Values[] = [];
  const { autosave, timers, saved, statuses } = harness(async (values) => {
    calls.push(values);
    if (fail) throw new Error('sin red');
    return values;
  });
  const local = { observations: 'texto local' };
  autosave.change(local);
  timers.tick();
  await settle();
  assert.equal(autosave.getStatus(), 'error');
  assert.equal(autosave.isDirty(), true);
  assert.equal(saved.length, 0);
  assert.deepEqual(local, { observations: 'texto local' }); // el controlador no muta los valores
  assert.equal(await autosave.flush(), false);

  fail = false;
  assert.equal(await autosave.flush(), true);
  assert.equal(autosave.isDirty(), false);
  assert.ok(statuses.includes('error') && statuses.at(-1) === 'saved');
});

test('shouldApplySaveResult: un seq viejo o una generación vieja nunca se aplican', () => {
  assert.equal(shouldApplySaveResult({ seq: 2, generation: 0, lastAppliedSeq: 1, currentGeneration: 0 }), true);
  assert.equal(shouldApplySaveResult({ seq: 1, generation: 0, lastAppliedSeq: 2, currentGeneration: 0 }), false);
  assert.equal(shouldApplySaveResult({ seq: 3, generation: 0, lastAppliedSeq: 2, currentGeneration: 1 }), false);
});

test('cambio de contexto con save en vuelo: la respuesta vieja no se aplica y NO se abre un segundo save mientras el anterior sigue vivo', async () => {
  const inFlight = deferred<Values>();
  const calls: Values[] = [];
  const { autosave, timers, saved } = harness((values) => {
    calls.push(values);
    return calls.length === 1 ? inFlight.promise : Promise.resolve(values);
  });
  autosave.change({ equipo: 'A', brand: 'Winter' });
  timers.tick();
  await settle();
  assert.equal(calls.length, 1);

  autosave.invalidateContext(); // el contexto pasa al equipo B
  autosave.change({ equipo: 'B', brand: 'Otra' });
  const flushed = autosave.flush();
  timers.tick();
  await settle();
  assert.equal(calls.length, 1, 'el PATCH de A sigue físicamente en vuelo: B espera');

  inFlight.resolve({ equipo: 'A', brand: 'Winter' }); // respuesta tardía de A
  assert.equal(await flushed, true);
  assert.deepEqual(calls, [{ equipo: 'A', brand: 'Winter' }, { equipo: 'B', brand: 'Otra' }]);
  assert.deepEqual(saved, [{ equipo: 'B', brand: 'Otra' }], 'la respuesta de A nunca llega a la UI de B');
});

test('un fallo del vuelo de otro contexto no hace fallar el flush del contexto nuevo', async () => {
  const inFlight = deferred<Values>();
  let n = 0;
  const { autosave } = harness((values) => (++n === 1 ? inFlight.promise : Promise.resolve(values)));
  autosave.change({ equipo: 'A' });
  assert.equal(autosave.isDirty(), true);
  const first = autosave.flush();
  await settle();
  autosave.invalidateContext();
  autosave.change({ equipo: 'B' });
  const second = autosave.flush();
  inFlight.reject(new Error('A falló'));
  await first;
  assert.equal(await second, true);
});

test('leave: flush fallido al abandonar NO pierde el draft ni invalida el contexto; reintentar funciona', async () => {
  let fail = true;
  const calls: Values[] = [];
  const { autosave, saved } = harness(async (values) => {
    calls.push(values);
    if (fail) throw new Error('sin red');
    return values;
  });
  autosave.change({ observations: 'captura valiosa' });
  assert.equal(await autosave.leave(), false);
  assert.equal(autosave.isDirty(), true);

  fail = false;
  assert.equal(await autosave.leave(), true);
  assert.deepEqual(calls.at(-1), { observations: 'captura valiosa' });
  assert.deepEqual(saved, [{ observations: 'captura valiosa' }], 'el contexto seguía vigente al reintentar');
  assert.equal(autosave.isDirty(), false);
});

test('discard: descarta lo NO enviado, espera al PATCH ya enviado y su respuesta no se aplica', async () => {
  const inFlight = deferred<Values>();
  const calls: Values[] = [];
  const { autosave, timers, saved } = harness((values) => {
    calls.push(values);
    return inFlight.promise;
  });
  autosave.change({ a: 1 });
  timers.tick();
  await settle(); // {a:1} ya enviado
  autosave.change({ a: 2 }); // aún no enviado

  let discarded = false;
  const pending = autosave.discard().then(() => { discarded = true; });
  await settle();
  assert.equal(discarded, false, 'el PATCH enviado no se cancela: se espera a que termine');
  assert.equal(autosave.isDirty(), false, 'lo no enviado se descartó');

  inFlight.resolve({ a: 1 });
  await pending;
  assert.deepEqual(saved, [], 'la respuesta del PATCH enviado no se aplica a la UI');
  assert.equal(await autosave.flush(), true);
  assert.equal(calls.length, 1, 'nada descartado se vuelve a enviar');
});

test('reception_date: valores locales sobreviven y sólo reception_date viene del backend', () => {
  const local = { calibration_date: '2026-10-01', environment_humidity_start: '45', observations: 'sin guardar', reception_date: '2026-08-13' };
  const refreshed = { reception_date: '2026-09-02', calibration_date: null, observations: null } as unknown as LabFieldSheet;
  const merged = mergeAuthoritativeSheetFields(local, refreshed);
  assert.equal(merged.reception_date, '2026-09-02');
  assert.equal(merged.calibration_date, '2026-10-01');
  assert.equal(merged.environment_humidity_start, '45');
  assert.equal(merged.observations, 'sin guardar');
  assert.equal(local.reception_date, '2026-08-13', 'no muta el objeto original');
});

test('respuesta de autosave conserva los results_rows ya persistidos por el workspace', () => {
  const current = { id: 7, results_rows: [{ id: 1, values: { a: 'nuevo' } }] } as unknown as LabFieldSheet;
  const saved = { id: 7, observations: 'x', results_rows: [{ id: 1, values: { a: 'viejo' } }] } as unknown as LabFieldSheet;
  const merged = mergeAutosavedSheet(current, saved);
  assert.deepEqual(merged?.results_rows, current.results_rows);
  assert.equal(merged?.observations, 'x');
  // hoja distinta (o ya sin hoja): la respuesta obsoleta se ignora
  const other = { id: 8, results_rows: [] } as unknown as LabFieldSheet;
  assert.equal(mergeAutosavedSheet(current, other), current);
  assert.equal(mergeAutosavedSheet(null, other), null);
});
