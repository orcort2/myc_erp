export type Role = {
  id: number;
  name: string;
  description?: string | null;
};

export type AuthUser = {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  permissions: string[];
  roles?: Role[];
  actor_type: 'internal' | 'client';
  client_id: number | null;
  membership_id: number | null;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  user: AuthUser;
};
