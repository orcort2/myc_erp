import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const here = dirname(fileURLToPath(import.meta.url));

type LocalAuthMock = {
  hasHardware?: boolean;
  isEnrolled?: boolean;
  supportedTypes?: number[];
  authenticateResult?: boolean;
};

// Execute the real module; only expo-local-authentication and RN's Platform
// (native ports) are replaced, same convention as LabTechnicalCapture's tests.
function harness(platform: 'ios' | 'android', mock: LocalAuthMock = {}) {
  const authenticateCalls: unknown[] = [];
  const ports: Record<string, unknown> = {
    'react-native': { Platform: { OS: platform } },
    'expo-local-authentication': {
      AuthenticationType: { FINGERPRINT: 1, FACIAL_RECOGNITION: 2, IRIS: 3 },
      hasHardwareAsync: async () => mock.hasHardware ?? true,
      isEnrolledAsync: async () => mock.isEnrolled ?? true,
      supportedAuthenticationTypesAsync: async () => mock.supportedTypes ?? [2],
      authenticateAsync: async (options: unknown) => {
        authenticateCalls.push(options);
        return (mock.authenticateResult ?? true) ? { success: true } : { success: false, error: 'user_cancel' };
      },
    },
  };
  const require_ = (name: string) => {
    if (name in ports) return ports[name];
    throw new Error(`unexpected import: ${name}`);
  };
  const source = readFileSync(resolve(here, 'biometric-auth.ts'), 'utf8');
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
  } }).outputText;
  const exports: Record<string, unknown> = {};
  new Function('require', 'exports', javascript)(require_, exports);
  return { ...exports, authenticateCalls } as {
    getBiometricAvailability(): Promise<{ available: boolean; enrolled: boolean; type: string; label: string }>;
    authenticateBiometric(reason: string): Promise<boolean>;
    authenticateCalls: unknown[];
  };
}

test('iOS con reconocimiento facial se detecta como Face ID', async () => {
  const bio = harness('ios', { supportedTypes: [2] });
  const availability = await bio.getBiometricAvailability();
  assert.deepEqual(availability, { available: true, enrolled: true, type: 'face_id', label: 'Face ID' });
});

test('iOS con huella (sin facial) se detecta como Touch ID', async () => {
  const bio = harness('ios', { supportedTypes: [1] });
  const availability = await bio.getBiometricAvailability();
  assert.deepEqual(availability, { available: true, enrolled: true, type: 'touch_id', label: 'Touch ID' });
});

test('Android con huella/biometría se detecta como Huella', async () => {
  const bio = harness('android', { supportedTypes: [1] });
  const availability = await bio.getBiometricAvailability();
  assert.deepEqual(availability, { available: true, enrolled: true, type: 'fingerprint', label: 'Huella' });
});

test('Android con reconocimiento facial también se detecta como Huella (biometría fuerte genérica)', async () => {
  const bio = harness('android', { supportedTypes: [2] });
  const availability = await bio.getBiometricAvailability();
  assert.equal(availability.type, 'fingerprint');
});

test('sin hardware biométrico, availability es "none" y no consulta enrolamiento', async () => {
  const bio = harness('ios', { hasHardware: false });
  const availability = await bio.getBiometricAvailability();
  assert.deepEqual(availability, { available: false, enrolled: false, type: 'none', label: 'Biometría' });
});

test('authenticateBiometric exige biometría fuerte en Android y deshabilita el fallback a PIN/passcode', async () => {
  const bio = harness('android', { authenticateResult: true });
  const success = await bio.authenticateBiometric('Confirma tu identidad');
  assert.equal(success, true);
  assert.equal(bio.authenticateCalls.length, 1);
  const options = bio.authenticateCalls[0] as Record<string, unknown>;
  assert.equal(options.disableDeviceFallback, true);
  assert.equal(options.biometricsSecurityLevel, 'strong');
  assert.equal(options.promptMessage, 'Confirma tu identidad');
});

test('authenticateBiometric también deshabilita el fallback a passcode en iOS', async () => {
  const bio = harness('ios', {});
  await bio.authenticateBiometric('Confirma tu identidad');
  const options = bio.authenticateCalls[0] as Record<string, unknown>;
  assert.equal(options.disableDeviceFallback, true);
});

test('la cancelación del prompt biométrico resuelve false, no lanza', async () => {
  const bio = harness('ios', { authenticateResult: false });
  const success = await bio.authenticateBiometric('Confirma tu identidad');
  assert.equal(success, false);
});
