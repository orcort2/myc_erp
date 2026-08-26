import assert from 'node:assert/strict';
import test from 'node:test';

import { createMobileAuthClient } from './mobile-auth-client';

function tokenPair(actorType: 'internal' | 'client') {
  return {
    access_token: 'access-token',
    refresh_token: 'refresh-token',
    token_type: 'bearer',
    user: {
      id: 7,
      email: 'mobile@example.com',
      full_name: 'Mobile User',
      is_active: true,
      permissions: ['mobile.access'],
      actor_type: actorType,
      client_id: actorType === 'client' ? 31 : null,
      membership_id: actorType === 'client' ? 47 : null,
    },
  };
}

test('login usa la autoridad Mobile y normaliza el correo', async () => {
  let request: { input: string; init?: RequestInit } | null = null;
  const auth = createMobileAuthClient('https://api.example.com', (async (input, init) => {
    request = { input: String(input), init };
    return Response.json(tokenPair('internal'));
  }) as typeof fetch);

  const result = await auth.login(' Staff@MYC.Example.com ', 'secret');

  assert.match(request!.input, /\/mobile\/v1\/auth\/login$/);
  assert.deepEqual(JSON.parse(String(request!.init?.body)), {
    email: 'staff@myc.example.com',
    password: 'secret',
  });
  assert.equal(result.user.actor_type, 'internal');
  assert.equal(result.user.client_id, null);
});

for (const profile of ['Viewer externo', 'Operativo Jr', 'Operativo Sr']) {
  test(`login ${profile} conserva el contexto client recibido`, async () => {
    const auth = createMobileAuthClient(
      'https://api.example.com',
      (async () => Response.json(tokenPair('client'))) as typeof fetch,
    );

    const result = await auth.login('external@example.com', 'secret');

    assert.equal(result.user.actor_type, 'client');
    assert.equal(result.user.client_id, 31);
    assert.equal(result.user.membership_id, 47);
  });
}

test('refresh usa el endpoint Mobile y conserva actor y scope', async () => {
  let requestedUrl = '';
  const auth = createMobileAuthClient('https://api.example.com', (async (input) => {
    requestedUrl = String(input);
    return Response.json(tokenPair('client'));
  }) as typeof fetch);

  const result = await auth.refresh('refresh-token');

  assert.match(requestedUrl, /\/mobile\/v1\/auth\/refresh$/);
  assert.equal(result.user.actor_type, 'client');
  assert.equal(result.user.client_id, 31);
  assert.equal(result.user.membership_id, 47);
});

test('el detalle backend de acceso denegado llega intacto a la UX', async () => {
  const auth = createMobileAuthClient(
    'https://api.example.com',
    (async () => Response.json(
      { detail: 'La cuenta no tiene acceso a MYC Mobile' },
      { status: 403 },
    )) as typeof fetch,
  );

  await assert.rejects(
    auth.login('blocked@example.com', 'secret'),
    /La cuenta no tiene acceso a MYC Mobile/,
  );
});
