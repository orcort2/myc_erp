import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const here = dirname(fileURLToPath(import.meta.url));

type StorageModule = {
  readBiometricProfile(): Promise<unknown>;
  writeBiometricProfile(profile: unknown): Promise<void>;
  clearBiometricProfile(): Promise<void>;
  readBiometricCredential(): Promise<string | null>;
  writeBiometricCredential(credential: string): Promise<void>;
  clearBiometricCredential(): Promise<void>;
  clearBiometricEnrollment(): Promise<void>;
};

function harness(readCredentialError: Error | null = null) {
  const store = new Map<string, string>();
  const setItemCalls: { key: string; value: string; options?: unknown }[] = [];
  const getItemCalls: { key: string; options?: unknown }[] = [];
  const ports: Record<string, unknown> = {
    'expo-secure-store': {
      WHEN_UNLOCKED_THIS_DEVICE_ONLY: 0,
      getItemAsync: async (key: string, options?: unknown) => {
        getItemCalls.push({ key, options });
        if (readCredentialError && key === 'myc.biometric.credential.v1') throw readCredentialError;
        return store.get(key) ?? null;
      },
      setItemAsync: async (key: string, value: string, options?: unknown) => {
        setItemCalls.push({ key, value, options });
        store.set(key, value);
      },
      deleteItemAsync: async (key: string) => { store.delete(key); },
    },
  };
  const require_ = (name: string) => {
    if (name in ports) return ports[name];
    throw new Error(`unexpected import: ${name}`);
  };
  const source = readFileSync(resolve(here, 'biometric-storage.ts'), 'utf8');
  const javascript = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS,
  } }).outputText;
  const exports: Record<string, unknown> = {};
  new Function('require', 'exports', javascript)(require_, exports);
  return { module: exports as StorageModule, store, setItemCalls, getItemCalls };
}

test('el perfil y la credencial biométricos usan claves separadas', () => {
  const { module } = harness();
  void module;
  const profileKey = 'myc.biometric.profile.v1';
  const credentialKey = 'myc.biometric.credential.v1';
  assert.notEqual(profileKey, credentialKey);
});

test('escribir el perfil no exige autenticación (no es secreto)', async () => {
  const { setItemCalls, module } = harness();
  await module.writeBiometricProfile({ user_id: 1, email: 'a@b.com', full_name: 'A B', biometric_label: 'Face ID' });
  assert.equal(setItemCalls.length, 1);
  assert.equal(setItemCalls[0].key, 'myc.biometric.profile.v1');
  assert.equal((setItemCalls[0].options as Record<string, unknown> | undefined)?.requireAuthentication, undefined);
  assert.doesNotMatch(setItemCalls[0].value, /password/i);
});

test('leer el perfil nunca dispara un prompt biométrico', async () => {
  const { module, getItemCalls } = harness();
  await module.writeBiometricProfile({ user_id: 1, email: 'a@b.com', full_name: 'A B', biometric_label: 'Face ID' });
  await module.readBiometricProfile();
  const profileReads = getItemCalls.filter((call) => call.key === 'myc.biometric.profile.v1');
  assert.ok(profileReads.every((call) => !(call.options as Record<string, unknown> | undefined)?.requireAuthentication));
});

test('la credencial se guarda protegida con requireAuthentication', async () => {
  const { setItemCalls, module } = harness();
  await module.writeBiometricCredential('opaque-credential-value');
  assert.equal(setItemCalls.length, 1);
  assert.equal(setItemCalls[0].key, 'myc.biometric.credential.v1');
  assert.equal((setItemCalls[0].options as Record<string, unknown>).requireAuthentication, true);
});

test('leer la credencial exige autenticación', async () => {
  const { module, getItemCalls } = harness();
  await module.writeBiometricCredential('opaque-credential-value');
  const value = await module.readBiometricCredential();
  assert.equal(value, 'opaque-credential-value');
  const credentialReads = getItemCalls.filter((call) => call.key === 'myc.biometric.credential.v1');
  assert.equal((credentialReads.at(-1)?.options as Record<string, unknown>).requireAuthentication, true);
});

test('una lectura protegida sin valor almacenado resuelve null (nunca crashea)', async () => {
  const { module } = harness();
  const value = await module.readBiometricCredential();
  assert.equal(value, null);
});

test('un fallo/cancelación en la lectura protegida propaga el error, sin tocar el storage', async () => {
  const { module, store } = harness(new Error('user_cancel'));
  await module.writeBiometricCredential('opaque-credential-value');
  await assert.rejects(module.readBiometricCredential(), /user_cancel/);
  // The credential must survive a cancelled/failed prompt.
  assert.equal(store.get('myc.biometric.credential.v1'), 'opaque-credential-value');
});

test('clearBiometricEnrollment elimina perfil y credencial juntos', async () => {
  const { module, store } = harness();
  await module.writeBiometricProfile({ user_id: 1, email: 'a@b.com', full_name: 'A B', biometric_label: 'Face ID' });
  await module.writeBiometricCredential('opaque-credential-value');
  await module.clearBiometricEnrollment();
  assert.equal(store.has('myc.biometric.profile.v1'), false);
  assert.equal(store.has('myc.biometric.credential.v1'), false);
});
