import assert from 'node:assert/strict';
import test from 'node:test';

import { createTechnicalReportAutosave, TECHNICAL_REPORT_AUTOSAVE_DEBOUNCE_MS } from './technical-report-autosave';

function harness(save: (values: string) => Promise<string>, extra: { onSaved?: (value: string) => void } = {}) {
  const timers = new Map<number, () => void>();
  let nextTimer = 0;
  const statuses: string[] = [];
  const delays: number[] = [];
  const autosave = createTechnicalReportAutosave<string, string>({
    save,
    onSaved: extra.onSaved,
    onStatusChange: (status) => statuses.push(status),
    setTimer: (callback, ms) => { delays.push(ms); timers.set(++nextTimer, callback); return nextTimer; },
    clearTimer: (handle) => { timers.delete(handle as number); },
  });
  const fire = async () => { const [id, callback] = [...timers.entries()][0]; timers.delete(id); callback(); await new Promise((r) => setImmediate(r)); };
  return { autosave, statuses, delays, timers, fire };
}

test('debounce: muchas teclas producen un solo guardado con el último valor', async () => {
  const saved: string[] = [];
  const { autosave, timers, fire, delays } = harness(async (value) => { saved.push(value); return value; });
  autosave.change('a'); autosave.change('ab'); autosave.change('abc');
  assert.equal(timers.size, 1, 'el temporizador se reprograma, no se acumula');
  assert.ok(delays.every((ms) => ms === TECHNICAL_REPORT_AUTOSAVE_DEBOUNCE_MS));
  assert.deepEqual(saved, []);
  await fire();
  assert.deepEqual(saved, ['abc']);
  assert.equal(autosave.isDirty(), false);
  assert.equal(autosave.getStatus(), 'saved');
});

test('un solo guardado en vuelo: lo escrito durante el vuelo se guarda después, en orden', async () => {
  const saved: string[] = [];
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const { autosave, fire } = harness(async (value) => { saved.push(value); if (saved.length === 1) await gate; return value; });
  autosave.change('uno');
  await fire();
  autosave.change('dos');
  const flushing = autosave.flush();
  release();
  assert.equal(await flushing, true);
  assert.deepEqual(saved, ['uno', 'dos']);
});

test('un fallo conserva lo pendiente, se reporta y el siguiente flush reintenta', async () => {
  let fail = true;
  const saved: string[] = [];
  const { autosave, statuses } = harness(async (value) => { if (fail) throw new Error('red'); saved.push(value); return value; });
  autosave.change('a');
  assert.equal(await autosave.flush(), false);
  assert.equal(autosave.isDirty(), true);
  assert.equal(autosave.getStatus(), 'error');
  assert.ok(statuses.includes('error'));
  fail = false;
  assert.equal(await autosave.flush(), true);
  assert.deepEqual(saved, ['a']);
});

test('leave(): con guardado pendiente exitoso invalida el contexto; si falla bloquea y no pierde nada', async () => {
  let fail = true;
  const { autosave } = harness(async (value) => { if (fail) throw new Error('red'); return value; });
  autosave.change('x');
  assert.equal(await autosave.leave(), false);
  assert.equal(autosave.isDirty(), true, 'sigue dirty: nada se perdió');
  fail = false;
  assert.equal(await autosave.leave(), true);
  assert.equal(autosave.isDirty(), false);
  assert.equal(autosave.getStatus(), 'idle');
});

test('una respuesta de un contexto invalidado no se aplica', async () => {
  const applied: string[] = [];
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const { autosave, fire } = harness(async (value) => { await gate; return value; }, { onSaved: (value) => applied.push(value) });
  autosave.change('viejo');
  await fire();
  autosave.invalidateContext();
  release();
  await new Promise((r) => setImmediate(r));
  assert.deepEqual(applied, []);
});

test('no importa nada de FieldSheet: es un módulo propio', async () => {
  const { readFileSync } = await import('node:fs');
  const { dirname, resolve } = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const source = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), 'technical-report-autosave.ts'), 'utf8');
  assert.doesNotMatch(source, /from '[^']*field-sheet/);
});
