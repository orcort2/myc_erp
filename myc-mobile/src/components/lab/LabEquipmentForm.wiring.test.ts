import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './LabEquipmentForm.tsx'),
  'utf8',
);

test('Vinculado usa un solo input con etiqueta y ayuda según autoridad de folio', () => {
  assert.equal((source.match(/label="Folio de informe vinculado"/g) ?? []).length, 1);
  assert.match(source, /canResolveLabFolios/);
  assert.match(source, /Se autorizará directamente con tu permiso/);
  assert.match(source, /Si no, se solicitará/);
});

test('LabEquipmentForm usa Field compartido, muestra error y limpia sólo el campo editado', () => {
  assert.match(source, /import \{ Field \} from '@\/src\/design\/primitives'/);
  assert.match(source, /error=\{fieldErrors\.serial_number\}/);
  assert.match(source, /onFieldChange\?\.\(field\)/);
  assert.doesNotMatch(source, /function Field\(/);
});
