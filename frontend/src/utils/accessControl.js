export function hasPermission(user, permission) {
  if (!permission) return Boolean(user);
  const permissions = Array.isArray(user?.permissions) ? user.permissions : [];
  if (permissions.includes('*') || permissions.includes(permission)) return true;
  const [scope] = permission.split('.', 1);
  return permissions.includes(`${scope}.*`);
}

export function hasAnyPermission(user, requiredPermissions = []) {
  if (!user) return false;
  if (!requiredPermissions?.length) return true;
  return requiredPermissions.some((permission) => hasPermission(user, permission));
}

export function filterAccessibleEntries(entries, user) {
  return entries.filter((entry) => hasAnyPermission(user, entry.permissions));
}

export function canAccessModule(module, user) {
  return Boolean(module && hasAnyPermission(user, module.permissions));
}

export function isClientPortalUser(user) {
  const roleNames = Array.isArray(user?.roles)
    ? user.roles.map((role) => `${role?.name ?? ''}`.trim().toLowerCase())
    : [];
  return (
    roleNames.length > 0
    && roleNames.every((roleName) => roleName === 'cliente')
    && hasPermission(user, 'portal.read')
  );
}
