import { apiClient } from "./axios";
import type { CreateSalePayload, Sale, ShareInfo } from "../types/sales";
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

  processReturn: (id: number, items: { product_id: number; qty: string }[], notes = "") =>
    apiClient
      .post<Sale>(`/sales/${id}/return/`, { items, notes })
      .then((r) => r.data),

  /** Signed link + pre-written WhatsApp message for one bill. */
  share: (id: number | string) =>
    apiClient.get<ShareInfo>(`/sales/${id}/share/`).then((r) => r.data),

  /** Raw PDF bytes, for the native share sheet on devices that can attach files. */
  receiptPdfBlob: (id: number | string, template: "thermal" | "invoice" = "invoice") =>
    apiClient
      .get<Blob>(`/sales/${id}/receipt/pdf/`, { params: { template }, responseType: "blob" })
      .then((r) => r.data),
};