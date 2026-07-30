export function hasDirectExceptionAuthority(user) {
  const roles = (user?.roles ?? []).map((role) => (role?.name ?? '').toLowerCase());
  return Boolean(
    user?.permissions?.includes('*') ||
      roles.some((role) => ['admin', 'administrador', 'administrator'].includes(role))
  );
}

export function exceptionActionLabel(user) {
  return hasDirectExceptionAuthority(user)
    ? 'Aplicar excepción'
    : 'Solicitar excepción';
}
