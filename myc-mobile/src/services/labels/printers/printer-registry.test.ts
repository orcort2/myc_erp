import assert from 'node:assert/strict';
import test from 'node:test';

import { classifyDevice, familyFor, listKnownPrinterFamilies } from './printer-registry';
import type { DiscoveredDevice } from './types';

function device(overrides: Partial<DiscoveredDevice>): DiscoveredDevice {
  return { id: 'device-1', name: null, ...overrides };
}

test('NIIMBOT B1 se reconoce y reporta supported', () => {
  const result = classifyDevice(device({ name: 'B1-A1B2C3' }));
  assert.equal(result.kind, 'recognized');
  if (result.kind === 'recognized') {
    assert.equal(result.family.adapterId, 'niimbot-b1');
    assert.equal(result.family.supportStatus, 'supported');
  }
});

test('variantes de nombre NIIMBOT ("NIIMBOT B1", "niimbot_b1") también se reconocen', () => {
  for (const name of ['NIIMBOT B1', 'niimbot_b1-1234', 'NIIMBOT-B1']) {
    const result = classifyDevice(device({ name }));
    assert.equal(result.kind, 'recognized', `esperaba reconocer "${name}"`);
  }
});

test('NELKO PM220 se reconoce pero reporta protocol_pending, nunca supported', () => {
  const result = classifyDevice(device({ name: 'PM220-0042' }));
  assert.equal(result.kind, 'recognized');
  if (result.kind === 'recognized') {
    assert.equal(result.family.adapterId, 'nelko-pm220');
    assert.equal(result.family.supportStatus, 'protocol_pending');
  }
});

test('un dispositivo BLE sin nombre coincidente es unknown -- nunca se ofrece como impresora', () => {
  for (const name of [null, '', 'AirPods Pro', 'Apple Watch', 'B12000-fridge-sensor']) {
    const result = classifyDevice(device({ name }));
    assert.equal(result.kind, 'unknown', `"${name}" no debería clasificar como impresora conocida`);
  }
});

test('la clasificación nunca es por descarte: B21/D11 (otros modelos NIIMBOT) no se confunden con B1', () => {
  const result = classifyDevice(device({ name: 'B21-XYZ' }));
  assert.equal(result.kind, 'unknown', 'B21 no es B1: no debe clasificar como niimbot-b1 por prefijo parcial');
});

test('familyFor resuelve el descriptor completo por adapterId', () => {
  assert.equal(familyFor('niimbot-b1')?.displayName, 'NIIMBOT B1');
  assert.equal(familyFor('nelko-pm220')?.supportStatus, 'protocol_pending');
  assert.equal(familyFor('unknown-brand'), undefined);
});

test('el catálogo declara al menos NIIMBOT B1 (supported) y NELKO PM220 (protocol_pending)', () => {
  const families = listKnownPrinterFamilies();
  assert.ok(families.some((family) => family.adapterId === 'niimbot-b1' && family.supportStatus === 'supported'));
  assert.ok(families.some((family) => family.adapterId === 'nelko-pm220' && family.supportStatus === 'protocol_pending'));
});
