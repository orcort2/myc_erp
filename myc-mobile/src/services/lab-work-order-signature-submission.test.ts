import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import type { SignaturePayload } from '../components/signatures/signature-flow-state';
import type { LabWorkOrder } from '../types/lab-work-order';
import { postLabGroupSignatures } from './lab-work-order-signature-submission';

const payload: SignaturePayload = {
  client: {
    signer_name: 'Cliente',
    signature_data_url: 'data:image/png;base64,client',
  },
  technician: {
    signer_name: 'Técnico',
    signature_data_url: 'data:image/png;base64,technician',
  },
};

test('a normal draft with signature_required false reaches the real signatures request path', async () => {
  const workOrder = {
    id: 6419,
    root_work_order_id: 6419,
    status: 'draft',
    signature_required: false,
    signature_preserved: false,
    signature_session_id: null,
  } as LabWorkOrder;
  const calls: { init?: RequestInit; path: string }[] = [];
  const response = {
    ...workOrder,
    status: 'ready_for_signatures',
    signature_session_id: 77,
  } as LabWorkOrder;

  const result = await postLabGroupSignatures({
    payload,
    request: async <T>(path: string, init?: RequestInit) => {
      calls.push({ init, path });
      return response as T;
    },
    signedAt: '2026-08-24T12:00:00.000Z',
    workOrder,
  });

  assert.equal(calls.length, 1);
  assert.equal(calls[0].path, '/mobile/v1/technician/lab-work-orders/6419/signatures');
  assert.equal(calls[0].init?.method, 'POST');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
    client: {
      ...payload.client,
      signed_at: '2026-08-24T12:00:00.000Z',
      version: 1,
    },
    technician: {
      ...payload.technician,
      signed_at: '2026-08-24T12:00:00.000Z',
      version: 1,
    },
  });
  assert.equal(result.status, 'ready_for_signatures');
  assert.equal(result.signature_session_id, 77);
});

test('the exact backend error propagates without clearing or replacing it locally', async () => {
  const backendError = new Error('409: El grupo ya conserva una firma válida');

  await assert.rejects(
    postLabGroupSignatures({
      payload,
      request: async () => { throw backendError; },
      signedAt: '2026-08-24T12:00:00.000Z',
      workOrder: { id: 6419 } as LabWorkOrder,
    }),
    (error) => error === backendError,
  );
});

test('applySignatures delegates to the POST without a signature_required guard', () => {
  const screenSource = readFileSync(
    resolve(dirname(fileURLToPath(import.meta.url)), '../../app/(technician)/work-orders.tsx'),
    'utf8',
  );
  const handlerStart = screenSource.indexOf('async function applySignatures');
  const handlerEnd = screenSource.indexOf('async function completeGroup', handlerStart);
  const handlerSource = screenSource.slice(handlerStart, handlerEnd);

  assert.ok(handlerStart >= 0 && handlerEnd > handlerStart);
  assert.match(handlerSource, /workOrder\.root_work_order_id !== capturedContextId/);
  assert.match(handlerSource, /postLabGroupSignatures\(\{ payload, request, signedAt, workOrder \}\)/);
  assert.doesNotMatch(handlerSource, /signature_required/);
});
