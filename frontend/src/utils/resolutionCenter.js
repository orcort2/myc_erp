export const ACTIVE_RESOLUTION_STATES = new Set([
  'draft',
  'context_ready',
  'analyzed',
  'plan_ready',
  'simulated',
  'pending_authorization',
  'authorized',
  'revalidating',
  'ready_for_execution',
  'executing'
]);

export function shouldPollResolutions(items, visibilityState) {
  return visibilityState === 'visible'
    && items.some((item) => ACTIVE_RESOLUTION_STATES.has(item.lifecycle_status));
}

export function canRunResolutionStage(stage, capabilities = {}) {
  if (stage === 'prepare-context') return Boolean(capabilities.can_prepare);
  if (stage === 'analyze') return Boolean(capabilities.can_analyze);
  if (stage === 'build-plan') return Boolean(capabilities.can_plan);
  if (stage === 'simulate') return Boolean(capabilities.can_simulate);
  if (stage === 'authorize') return Boolean(capabilities.can_authorize);
  if (stage === 'execute') return Boolean(capabilities.can_execute);
  return false;
}
