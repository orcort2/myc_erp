import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const primitivesPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../design/primitives.tsx',
);
const partialDeliveryPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../components/lab/LabPartialDeliveryRequest.tsx',
);

const primitivesSource = readFileSync(primitivesPath, 'utf8');
const partialDeliverySource = readFileSync(partialDeliveryPath, 'utf8');

test('OperationalActionStack existe y su spacing viene del design system, no de números sueltos', () => {
  assert.match(
    primitivesSource,
    /export function OperationalActionStack\(\{ children \}: \{ children: ReactNode \}\)/,
  );

  const styleStart = primitivesSource.indexOf('operationalActionStack: {');
  assert.notEqual(styleStart, -1, 'debe existir un bloque de estilo operationalActionStack');
  const styleBlock = primitivesSource.slice(styleStart, primitivesSource.indexOf('}', styleStart));
  assert.match(styleBlock, /gap: spacing\./, 'el espaciado vertical debe venir de spacing.*, no de un número mágico');
  assert.doesNotMatch(styleBlock, /gap: \d/, 'no debe haber un valor de gap hardcodeado');
});

test('OperationalActionStack es una composición vertical distinta de ActionRow (contratos separados)', () => {
  const actionRowStyleStart = primitivesSource.indexOf('actionRow: {');
  const actionRowStyleBlock = primitivesSource.slice(actionRowStyleStart, primitivesSource.indexOf('}', actionRowStyleStart));
  assert.match(actionRowStyleBlock, /flexDirection: 'row'/, 'ActionRow debe seguir siendo horizontal');

  const stackStyleStart = primitivesSource.indexOf('operationalActionStack: {');
  const stackStyleBlock = primitivesSource.slice(stackStyleStart, primitivesSource.indexOf('}', stackStyleStart));
  assert.doesNotMatch(stackStyleBlock, /flexDirection: 'row'/, 'OperationalActionStack debe ser vertical (columna), no una fila');
});

test('PrimaryButton/SecondaryButton/AdministrativeButton/DangerButton siguen delegando en OperationalActionButton', () => {
  // La anatomía del botón (círculo + icono + label/description) no debe
  // duplicarse por wrapper -- cada uno sólo fija el tono semántico.
  for (const [wrapper, tone] of [
    ['PrimaryButton', 'primary'],
    ['SecondaryButton', 'secondary'],
    ['DangerButton', 'danger'],
    ['AdministrativeButton', 'administrative'],
  ] as const) {
    const pattern = new RegExp(
      `export function ${wrapper}\\(props: ButtonProps\\) \\{\\s*return <OperationalActionButton \\{\\.\\.\\.props\\} tone="${tone}" />;\\s*\\}`,
    );
    assert.match(primitivesSource, pattern, `${wrapper} debe delegar en OperationalActionButton con tone="${tone}"`);
  }
});

test('LabPartialDeliveryRequest agrupa su pareja Administrative/Secondary dentro de OperationalActionStack', () => {
  assert.match(
    partialDeliverySource,
    /import \{[^}]*OperationalActionStack[^}]*\} from '@\/src\/design\/primitives'/,
  );
  const stackStart = partialDeliverySource.indexOf('<OperationalActionStack>');
  assert.notEqual(stackStart, -1);
  const stackBody = partialDeliverySource.slice(stackStart, partialDeliverySource.indexOf('</OperationalActionStack>'));
  assert.match(stackBody, /<AdministrativeButton/);
  assert.match(stackBody, /<SecondaryButton/);
});
