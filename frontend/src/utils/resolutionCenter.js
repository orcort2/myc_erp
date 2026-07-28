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

export function resolutionParameterFields(definition) {
  const schema = definition?.parameter_schema ?? {};
  const required = new Set(schema.required ?? []);
  return Object.entries(schema.properties ?? {}).map(([name, field]) => ({
    ...field,
    name,
    required: required.has(name)
  }));
}

export function buildResolutionParameters(definition, values = {}) {
  return Object.fromEntries(
    resolutionParameterFields(definition)
      .filter(({ name }) => values[name] !== undefined && values[name] !== '')
      .map((field) => {
        const raw = values[field.name];
        if (field.type === 'integer') return [field.name, Number.parseInt(raw, 10)];
        if (field.type === 'number') return [field.name, Number(raw)];
        if (field.type === 'boolean') return [field.name, raw === true || raw === 'true'];
        return [field.name, typeof raw === 'string' ? raw.trim() : raw];
      })
  );
}
