export function hasQuotationExceptionPermission(user, permission) {
  return Boolean(
    user?.permissions?.includes('*') ||
      user?.permissions?.includes('quotations.*') ||
      user?.permissions?.includes(permission)
  );
}

export function formatQuotationServiceOption(item) {
  return item?.internalKey ? `${item.internalKey} · ${item.name}` : item?.name || 'Servicio';
}

export function canShowQuotationServiceException(quotation, user) {
  return Boolean(
    quotation?.status === 'accepted' &&
      hasQuotationExceptionPermission(
        user,
        'quotations.exceptions.request_change_service'
      )
  );
}
