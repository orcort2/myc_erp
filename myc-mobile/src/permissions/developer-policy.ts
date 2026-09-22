import type { AuthUser } from '@/src/types/auth';

// DEV-0: mirrors backend app/core/developer_policy.py. Administrador ERP is
// NOT an infrastructure administrator: Developer requires an internal actor
// AND an exact Developer capability (the exact capability string, e.g.
// 'developer.access'). Neither '*' nor the literal wildcard 'developer.*' opens
// it -- deliberately NOT hasPermission(), whose wildcard semantics stay for
// the rest of the app. The backend re-checks this on every Developer call;
// this only decides what the UI offers.
export const DEVELOPER_ACCESS = 'developer.access';

export function hasDeveloperCapability(
  user: Pick<AuthUser, 'actor_type' | 'permissions'> | null | undefined,
  capability: string = DEVELOPER_ACCESS,
): boolean {
  return user?.actor_type === 'internal' && (user.permissions ?? []).includes(capability);
}
