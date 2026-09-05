import { apiClient } from "./axios";
import type { Customer, PaymentReceived, KhataReport } from "@/types/customers";
import type { PaginatedResponse } from "@/types/catalog";
import type { Sale } from "@/types/sales";

export const customersApi = {
  list: (params?: { search?: string; page?: number }) =>
    apiClient
      .get<PaginatedResponse<Customer>>("/customers/", { params })
      .then((r) => r.data),

  get: (id: number) =>
    apiClient.get<Customer>(`/customers/${id}/`).then((r) => r.data),

  create: (data: { name?: string; phone?: string; gender?: string; notes?: string }) =>
    apiClient.post<Customer>("/customers/", data).then((r) => r.data),

  update: (id: number, data: { name?: string; notes?: string; gender?: string }) =>
    apiClient.patch<Customer>(`/customers/${id}/`, data).then((r) => r.data),

  /** Returns the customer object if found, null if not found. */
  lookup: (phone: string) =>
    apiClient
      .get<Customer | null>(`/customers/lookup/?phone=${encodeURIComponent(phone)}`)
      .then((r) => r.data),

  salesHistory: (id: number, page = 1) =>
    apiClient
      .get<PaginatedResponse<Sale>>(`/customers/${id}/sales/?page=${page}`)
      .then((r) => r.data),

  /** Record a payment received against customer credit balance */
  recordPayment: (data: { customer_id: number; amount_paise: number; notes?: string }) =>
    apiClient
      .post<{ payment: PaymentReceived; customer: Customer }>("/customers/record-payment/", data)
      .then((r) => r.data),

  /** Get aged payables report (customers with outstanding credit) */
  khataReport: () =>
    apiClient
      .get<KhataReport>("/customers/khata-report/")
      .then((r) => r.data),
};