export type UserRole = "owner" | "manager" | "cashier" | "stock_clerk";

export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: UserRole;
  phone: string;
  is_active: boolean;
  /** Set when an owner issues or resets a password — the user picks their own. */
  must_change_password?: boolean;
  last_login?: string | null;
  created_at: string;
}

export interface CreateUserPayload {
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  phone?: string;
  password: string;
}

export interface UpdateUserPayload {
  first_name?: string;
  last_name?: string;
  role?: UserRole;
  phone?: string;
  is_active?: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface LoginResponse extends AuthTokens {
  user: User;
}
