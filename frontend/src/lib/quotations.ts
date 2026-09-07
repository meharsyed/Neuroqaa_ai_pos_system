import { apiClient } from "./axios";
import { openApiPdf } from "./pdf";
import type { PaginatedResponse } from "@/types/catalog";
import type {
  BusinessProfile,
  CreateQuotationPayload,
  Quotation,
  QuotationCart,
  QuotationStatus,
} from "@/types/quotations";

export const quotationsApi = {
  list: (params?: { search?: string; status?: string; page?: number }) =>
    apiClient
      .get<PaginatedResponse<Quotation>>("/quotations/", { params })
      .then((r) => r.data),

  get: (id: number) =>
    apiClient.get<Quotation>(`/quotations/${id}/`).then((r) => r.data),

  create: (data: CreateQuotationPayload) =>
    apiClient.post<Quotation>("/quotations/", data).then((r) => r.data),

  /** Replaces the contents and bumps the revision — same number throughout. */
  revise: (id: number, data: Partial<CreateQuotationPayload>) =>
    apiClient.post<Quotation>(`/quotations/${id}/revise/`, data).then((r) => r.data),

  setStatus: (id: number, status: QuotationStatus) =>
    apiClient.post<Quotation>(`/quotations/${id}/status/`, { status }).then((r) => r.data),

  toCart: (id: number) =>
    apiClient.get<QuotationCart>(`/quotations/${id}/to-cart/`).then((r) => r.data),

  markConverted: (id: number, sale_id: number) =>
    apiClient
      .post<Quotation>(`/quotations/${id}/mark-converted/`, { sale_id })
      .then((r) => r.data),

  /**
   * Open the printed quotation.
   *
   * Never link straight to /api/quotations/<id>/pdf/ — the token is attached
   * by the axios interceptor, so a plain navigation arrives unauthenticated.
   */
  openPdf: (id: number) =>
    openApiPdf(`/quotations/${id}/pdf/`, {
      failure: "Could not open the quotation",
    }),

  profiles: {
    list: () =>
      apiClient.get<BusinessProfile[]>("/business-profiles/").then((r) => r.data),
    create: (data: Partial<BusinessProfile>) =>
      apiClient.post<BusinessProfile>("/business-profiles/", data).then((r) => r.data),
    update: (id: number, data: Partial<BusinessProfile>) =>
      apiClient.patch<BusinessProfile>(`/business-profiles/${id}/`, data).then((r) => r.data),
  },
};
