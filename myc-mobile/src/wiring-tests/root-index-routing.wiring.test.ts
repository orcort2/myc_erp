import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

/**
 * Cierre UX post-BIOMETRIC-2: la pantalla pública ya no forma parte del
 * flujo de entrada. La raíz de la app debe ir directo a login, que decide
 * por sí sola (vía biometricProfile) si muestra Face ID/Touch ID/Huella o
 * el formulario de correo/contraseña.
 */
const source = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), '../../app/index.tsx'),
  'utf8',
);

test('la raíz de la app redirige a /(auth)/login', () => {
  assert.match(source, /<Redirect href="\/\(auth\)\/login" \/>/);
});

test('la raíz de la app ya no redirige a /(public)', () => {
  assert.doesNotMatch(source, /\/\(public\)/);
});
