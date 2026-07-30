export function hasQuotationExceptionPermission(user, permission) {
  return Boolean(
    user?.permissions?.includes('*') ||
      user?.permissions?.includes('quotations.*') ||
      user?.permissions?.includes(permission)
  );
}

export function canSelfAuthorizeQuotationUnlock(user) {
  return (
    hasQuotationExceptionPermission(
      user,
      'quotations.exceptions.self_authorize_unlock'
    ) &&
    hasQuotationExceptionPermission(
      user,
      'quotations.exceptions.authorize_unlock'
    )
  );
}

export function formatQuotationServiceOption(item) {
  return item?.internalKey ? `${item.internalKey} · ${item.name}` : item?.name || 'Servicio';
}

export function serviceTypeLabel(value) {
  return {
    accredited: 'Acreditado',
    traceable: 'Trazable',
    linked: 'Vinculado'
  }[value] || 'Sin clasificación';
}

export function normalizeLinkedCertificatePrefix(value) {
  return String(value || '').trim().toUpperCase();
}

export function validateLinkedServiceFields({
  serviceType,
  linkedCompanyId,
  linkedCompanyName,
  linkedCertificatePrefix
}) {
  if (serviceType !== 'linked') return null;
  if (!linkedCompanyId) return 'Selecciona la empresa o laboratorio vinculado.';
  if (linkedCompanyId === 'other' && !String(linkedCompanyName || '').trim()) {
    return 'Captura el nombre de la empresa vinculada.';
  }
  if (!/^[A-Z0-9]{2,12}$/.test(normalizeLinkedCertificatePrefix(linkedCertificatePrefix))) {
    return 'Las iniciales deben tener de 2 a 12 caracteres alfanuméricos, sin espacios.';
  }
  return null;
}

export function canShowQuotationServiceException(quotation, user) {
  return Boolean(
    quotation?.status === 'accepted' &&
      hasQuotationExceptionPermission(
        user,
        'quotations.exceptions.request_unlock'
      )
  );
}
