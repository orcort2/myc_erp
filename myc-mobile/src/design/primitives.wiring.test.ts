import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), './primitives.tsx'),
  'utf8',
);

test('Field: maxLength es opt-in -- se pasa al TextInput y activa un contador N/max', () => {
  const fieldMatch = source.match(/export function Field\(\{[\s\S]*?\n\}\)\s*\{[\s\S]*?\n\}/);
  assert.ok(fieldMatch, 'no se encontró la función Field');
  const body = fieldMatch[0];
  assert.match(body, /maxLength\?:\s*number/);
  assert.match(body, /maxLength=\{maxLength\}/);
  // El contador sólo se renderiza cuando el caller pasa maxLength -- no debe
  // ser un texto siempre visible que rompa a los callers existentes.
  assert.match(body, /\{!!maxLength && <Text style=\{styles\.fieldCounter\}>/);
});
