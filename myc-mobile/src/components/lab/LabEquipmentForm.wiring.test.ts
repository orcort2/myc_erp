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
  // El import puede venir agrupado con otros nombres del mismo módulo
  // (prettier reformatea la lista a multilinea según su longitud) -- lo que
  // importa es que Field se importe de primitives, no el layout exacto.
  assert.match(source, /import \{[^}]*\bField\b[^}]*\} from '@\/src\/design\/primitives'/);
  assert.match(source, /error=\{fieldErrors\.serial_number\}/);
  assert.match(source, /onFieldChange\?\.\(field\)/);
  assert.doesNotMatch(source, /function Field\(/);
});

test('Observaciones del equipo respeta el límite backend de 4000 caracteres', () => {
  const fieldMatch = source.match(/<Field\s+error=\{fieldErrors\.observations\}[\s\S]*?\/>/);
  assert.ok(fieldMatch, 'no se encontró el Field de observations');
  assert.match(fieldMatch[0], /maxLength=\{4000\}/);
});
