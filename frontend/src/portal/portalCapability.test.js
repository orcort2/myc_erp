import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const layoutPath = new URL('./ClientPortalLayout.jsx', import.meta.url);

test('Portal usa la capacidad institucional portal.read', async () => {
  const layout = await readFile(layoutPath, 'utf8');

  assert.match(layout, /permission: 'portal\.read'/);
  assert.doesNotMatch(layout, /portal\.view/);
});
