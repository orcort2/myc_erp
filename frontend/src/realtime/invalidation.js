const listeners = new Set();

export function subscribeInvalidations(listener) {
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}

export function invalidateResources(resources = ['*']) {
  const names = Array.isArray(resources) ? resources : [resources];

  for (const listener of [...listeners]) {
    listener(names);
  }
}

export function matchesInvalidation(resources, requestedResources) {
  return (
    resources.includes('*')
    || requestedResources.includes('*')
    || requestedResources.some((resource) => resources.includes(resource))
  );
}
