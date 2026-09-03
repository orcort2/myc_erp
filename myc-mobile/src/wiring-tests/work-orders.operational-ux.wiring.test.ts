import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
  'utf8',
);

test('el flujo técnico usa el canon de botones acordado', () => {
  // Normalización visual (actividad B): estos wrappers ahora también
  // llevan un icon= semántico -- el atributo se agregó antes de label=.
  assert.match(source, /<SecondaryButton icon="arrow-left" label="Volver a equipos" onPress=\{\(\) => setStep\('capture'\)\}/);
  assert.match(source, /<PrimaryButton icon="arrow-right-circle" label="Continuar a cierre" onPress=\{\(\) => setStep\('review'\)\}/);
  assert.match(source, /<SecondaryButton icon="download" label="Descargar paquete disponible"/);
});

test('datos generales y equipo presentan fieldErrors estructurados junto al control', () => {
  assert.match(source, /setGeneralErrors\(Object\.fromEntries\(error\.fieldErrors/);
  assert.match(source, /setEquipmentErrors\(Object\.fromEntries\(error\.fieldErrors/g);
  assert.match(source, /<AlertBanner tone="danger">Revisa los campos marcados/);
  assert.match(source, /fieldErrors=\{equipmentErrors\}/);
  assert.match(source, /onFieldChange=\{clearEquipmentError\}/);
});
