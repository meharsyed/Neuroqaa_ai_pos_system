import { apiClient } from "./axios";
import type { PaginatedResponse } from "@/types/catalog";
import type { Shift, ShiftCloseResult, ShiftReconciliation } from "@/types/config";

export const shiftsApi = {
  list: () =>
    apiClient
      .get<PaginatedResponse<Shift>>("/shifts/")
      .then((r) => r.data.results),

  current: () =>
    apiClient.get<Shift>("/shifts/current/").then((r) => r.data),

  open: (opening_float_paise: number, notes: string = "") =>
    apiClient
      .post<Shift>("/shifts/", { opening_float_paise, notes })
      .then((r) => r.data),

  close: (id: number, closing_cash_paise: number, closing_notes: string = "") =>
    apiClient
      .post<ShiftCloseResult>(`/shifts/${id}/close/`, { closing_cash_paise, closing_notes })
      .then((r) => r.data),

  reconciliation: (id: number) =>
    apiClient
      .get<ShiftReconciliation>(`/shifts/${id}/reconciliation/`)
      .then((r) => r.data),
};