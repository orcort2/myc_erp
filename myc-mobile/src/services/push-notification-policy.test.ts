import assert from 'node:assert/strict';
import test from 'node:test';

import { FOREGROUND_REVALIDATE_INTERVAL_MS, shouldSkipForegroundRevalidation } from './push-notification-policy';

test('a foreground revalidation with an unchanged token skips within the throttle window', () => {
  assert.equal(shouldSkipForegroundRevalidation('foreground', false, 60_000), true);
});

test('a foreground revalidation past the throttle window retries even with an unchanged token', () => {
  assert.equal(
    shouldSkipForegroundRevalidation('foreground', false, FOREGROUND_REVALIDATE_INTERVAL_MS + 1),
    false,
  );
});

test('a changed Expo push token always forces a fresh attempt, regardless of elapsed time', () => {
  assert.equal(shouldSkipForegroundRevalidation('foreground', true, 0), false);
});

test('the login/session-restore trigger never skips, even right after a success', () => {
  assert.equal(shouldSkipForegroundRevalidation('login', false, 0), false);
});
