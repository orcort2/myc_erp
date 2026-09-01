import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

test('crear y completar una FieldSheet refresca la OT desde backend con el helper único', () => {
  const source = readFileSync(resolve(root, 'components/lab/LabTechnicalCapture.tsx'), 'utf8');
  const helper = source.slice(source.indexOf('async function refreshWorkOrder'), source.indexOf('async function assignService'));
  assert.match(helper, /request<LabWorkOrder>/);
  assert.match(helper, /onUpdated\(updated\)/);

  const create = source.slice(source.indexOf('async function createSheet'), source.indexOf('function setField'));
  assert.match(create, /setSheet\(created\)[\s\S]*setValues\(buildValues\(created\)\)[\s\S]*setRows\([\s\S]*await refreshWorkOrder\(\)/);

  const complete = source.slice(source.indexOf('async function saveSheet'), source.indexOf('async function requestFolio'));
  assert.match(complete, /field-sheet\/complete[\s\S]*await refreshWorkOrder\(\)/);
  const exactRefreshRoute = "`/mobile/v1/technician/lab-work-orders/${workOrder.id}`";
  assert.equal(source.split(exactRefreshRoute).length - 1, 1);
});

test('acreditado y trazable muestran folio generado por sistema; vinculado conserva informe editable', () => {
  const source = readFileSync(resolve(root, 'components/lab/LabEquipmentForm.tsx'), 'utf8');
  assert.match(source, /service === 'linked'[\s\S]*Informe \(opcional\)/);
  assert.match(source, /Folio de informe/);
  assert.match(source, /Generado por el sistema/);
});
