import { apiClient } from "./axios";
import type { CreateSalePayload, Sale } from "../types/sales";
import type { PaginatedResponse } from "../types/catalog";

export const salesApi = {
  create: (data: CreateSalePayload) =>
    apiClient.post<Sale>("/sales/", data).then((r) => r.data),

  list: (params?: {
    status?: string;
    page?: number;
    search?: string;
    date_from?: string;
    date_to?: string;
    customer?: number;
  }) =>
    apiClient.get<PaginatedResponse<Sale>>("/sales/", { params }).then((r) => r.data),

  get: (id: number) =>
    apiClient.get<Sale>(`/sales/${id}/`).then((r) => r.data),

  void: (id: number) =>
    apiClient.post<Sale>(`/sales/${id}/void/`).then((r) => r.data),
};