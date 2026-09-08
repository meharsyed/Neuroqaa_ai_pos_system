import { apiClient } from "./axios";
import type { PaginatedResponse } from "@/types/catalog";
import type { CreateUserPayload, UpdateUserPayload, User } from "@/types/auth";

/** Staff accounts. Owner only — every endpoint here answers 403 to anyone else. */
export const usersApi = {
  list: (params?: { search?: string; page?: number }) =>
    apiClient
      .get<PaginatedResponse<User>>("/auth/users/", { params })
      .then((r) => r.data),

  create: (data: CreateUserPayload) =>
    apiClient.post<User>("/auth/users/", data).then((r) => r.data),

  update: (id: number, data: UpdateUserPayload) =>
    apiClient.patch<User>(`/auth/users/${id}/`, data).then((r) => r.data),

  /** Issue a temporary password. The user is made to choose their own next sign-in. */
  setPassword: (id: number, password: string) =>
    apiClient
      .post<{ detail: string }>(`/auth/users/${id}/set-password/`, { password })
      .then((r) => r.data),

  changeOwnPassword: (current_password: string, new_password: string) =>
    apiClient
      .post<{ detail: string }>("/auth/change-password/", { current_password, new_password })
      .then((r) => r.data),
};

/**
 * Turn a DRF error into something a person can read.
 *
 * DRF returns field errors as {"email": ["Someone already uses that email."]},
 * not {"detail": "..."} — reading only `detail` swallows exactly the messages
 * worth showing.
 */
export function apiErrorMessage(err: unknown, fallback = "Something went wrong."): string {
  const data = (err as { response?: { data?: unknown } })?.response?.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (typeof d.detail === "string") return d.detail;
    const parts: string[] = [];
    for (const [field, value] of Object.entries(d)) {
      const text = Array.isArray(value) ? value.join(" ") : String(value);
      parts.push(field === "non_field_errors" ? text : `${field.replace(/_/g, " ")}: ${text}`);
    }
    if (parts.length) return parts.join("\n");
  }
  return fallback;
}
