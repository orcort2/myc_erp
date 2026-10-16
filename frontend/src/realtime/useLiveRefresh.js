import { useEffect, useRef } from 'react';

import {
  matchesInvalidation,
  subscribeInvalidations,
} from './invalidation.js';

export function useLiveRefresh(
  refresh,
  {
    resources = ['*'],
    enabled = true,
    intervalMs = 30000,
  } = {},
) {
  const refreshRef = useRef(refresh);
  const resourcesRef = useRef(resources);
  const runningRef = useRef(false);
  const pendingRef = useRef(false);

  useEffect(() => {
    refreshRef.current = refresh;
    resourcesRef.current = resources;
  });

  useEffect(() => {
    if (!enabled) return undefined;

    let active = true;

    async function runRefresh() {
      if (!active) return;

      if (runningRef.current) {
        pendingRef.current = true;
        return;
      }

      runningRef.current = true;

      try {
        do {
          pendingRef.current = false;
          await refreshRef.current();
        } while (active && pendingRef.current);
      } catch (error) {
        console.error('MYC live refresh failed:', error);
      } finally {
        runningRef.current = false;
      }
    }

    function refreshIfVisible() {
      if (document.visibilityState === 'visible') {
        void runRefresh();
      }
    }

    const unsubscribe = subscribeInvalidations((changedResources) => {
      if (
        matchesInvalidation(
          changedResources,
          resourcesRef.current,
        )
      ) {
        void runRefresh();
      }
    });

    window.addEventListener('focus', refreshIfVisible);
    document.addEventListener('visibilitychange', refreshIfVisible);

    const timer = intervalMs > 0
      ? window.setInterval(refreshIfVisible, intervalMs)
      : null;

    return () => {
      active = false;
      unsubscribe();

      window.removeEventListener('focus', refreshIfVisible);
      document.removeEventListener('visibilitychange', refreshIfVisible);

      if (timer !== null) {
        window.clearInterval(timer);
      }
    };
  }, [enabled, intervalMs]);
}
