export function hasPermission(permissions: string[], permission: string): boolean {
  if (permissions.includes('*') || permissions.includes(permission)) return true;
  const [namespace] = permission.split('.', 1);
  return permissions.includes(`${namespace}.*`);
}
