import assert from 'node:assert/strict';
import test from 'node:test';

import { MYC_50X30 } from '../../../label-profile';
import { renderLabel } from '../../../label-renderer';
import type { LabLabelPayload } from '../../../label-types';
import { NelkoPm220Adapter, NelkoProtocolPendingError } from './nelko-pm220-adapter';

const PAYLOAD: LabLabelPayload = {
  calibrationDate: '2026-09-01',
  equipmentCode: 'ID-1',
  workOrderFolio: '12345',
  certificateFolio: 'MYCA-0001',
};

test('NELKO PM220 nunca reporta conectado', () => {
  assert.equal(new NelkoPm220Adapter().isConnected(), false);
});

test('connect() rechaza con NelkoProtocolPendingError -- nunca intenta hablar un protocolo inventado', async () => {
  const adapter = new NelkoPm220Adapter();
  await assert.rejects(adapter.connect({ id: 'device-1', name: 'PM220-0042' }), NelkoProtocolPendingError);
});

test('print() rechaza con NelkoProtocolPendingError -- nunca envía un byte al dispositivo', async () => {
  const adapter = new NelkoPm220Adapter();
  const raster = renderLabel(PAYLOAD, MYC_50X30, 203);
  await assert.rejects(adapter.print(raster), NelkoProtocolPendingError);
});

test('disconnect() es un no-op seguro incluso sin haber conectado nunca', async () => {
  const adapter = new NelkoPm220Adapter();
  await assert.doesNotReject(adapter.disconnect());
});

test('capabilities declara la ficha técnica pública (203dpi/384px) pero eso NO implica soporte de protocolo', () => {
  const adapter = new NelkoPm220Adapter();
  assert.equal(adapter.capabilities.dpi, 203);
  assert.equal(adapter.id, 'nelko-pm220');
});
