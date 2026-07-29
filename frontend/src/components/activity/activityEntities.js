export const ACTIVITY_ENTITY_DESTINATIONS = Object.freeze({
  client: '/dashboard#clientes',
  contact: '/dashboard#clientes',
  quotation: '/dashboard#cotizaciones',
  service_order: '/dashboard#servicios',
  work_order: '/dashboard#servicios',
  equipment: '/dashboard#servicios',
  field_sheet: '/dashboard#servicios',
  certificate: '/dashboard#certificados',
  invoice: '/dashboard#facturacion',
  payment: '/dashboard#facturacion',
  credit_note: '/dashboard#facturacion',
  document: '/dashboard#documentos',
  document_interpretation: '/dashboard#documentos',
  technical_profile: '/dashboard#documentos',
  reference_standard: '/dashboard#patrones',
  reference_standard_certificate: '/dashboard#patrones',
  calibration_procedure: '/dashboard#procedimientos',
  uncertainty_model: '/dashboard#incertidumbre',
  resolution: '/dashboard#resoluciones',
});

export function canEditActivityMessage(message, currentUser, capabilities = {}) {
  return Boolean(
    capabilities.can_edit_own
    && message?.author?.id === currentUser?.id
    && !message?.withdrawn_at
    && !message?.is_system
    && !message?.is_formal,
  );
}

export function canResolveActivityAttention(
  attention,
  currentUser,
  capabilities = {},
) {
  return Boolean(
    capabilities.can_resolve_attention
    && (
      !attention?.assigned_user_id
      || attention.assigned_user_id === currentUser?.id
      || capabilities.can_moderate
    ),
  );
}
