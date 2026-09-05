import { apiClient } from "./axios";
import { toast } from "./use-toast";
import type {
  Customer,
  KhataDetail,
  KhataReport,
  PaymentReceived,
} from "@/types/customers";
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

  update: (
    id: number,
    data: {
      name?: string;
      notes?: string;
      gender?: string;
      /** null clears the per-customer limit and falls back to the shop default. */
      credit_limit_paise?: number | null;
    },
  ) =>
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

  /** Record a payment received against a customer's khata. Owner/manager only. */
  recordPayment: (data: { customer_id: number; amount_paise: number; notes?: string }) =>
    apiClient
      .post<{ payment: PaymentReceived; customer: Customer }>("/customers/record-payment/", data)
      .then((r) => r.data),

  /** Aged receivables across every customer carrying a balance. */
  khataReport: () =>
    apiClient.get<KhataReport>("/customers/khata-report/").then((r) => r.data),

  /** Full history behind one customer's balance. */
  khataDetail: (id: number) =>
    apiClient.get<KhataDetail>(`/customers/${id}/khata/`).then((r) => r.data),
};

/**
 * Open the printable khata statement. The endpoint needs a Bearer token, so it
 * has to be fetched rather than linked to directly.
 */
export function openKhataStatement(customerId: number) {
  return apiClient
    .get<Blob>(`/customers/${customerId}/khata/statement/`, { responseType: "blob" })
    .then((r) => {
      const url = URL.createObjectURL(r.data);
      const win = window.open(url, "_blank");
      if (!win) {
        toast({
          title: "Popup blocked",
          description: "Allow popups for this site to view the statement.",
          variant: "error",
        });
      }
    })
    .catch((err) => {
      toast({
        title: "Could not open the statement",
        description: err?.response?.data?.detail ?? err.message,
        variant: "error",
      });
    });
}

/**
 * Build a WhatsApp reminder link. Pakistani numbers are stored locally
 * (03331122333); wa.me needs them in international form (923331122333).
 */
export function whatsappReminderUrl(
  phone: string | null,
  customerName: string,
  outstandingPaise: number,
  shopName = "Speed Tech Solutions",
): string | null {
  if (!phone) return null;
  const digits = phone.replace(/\D/g, "");
  if (digits.length < 10) return null;

  let intl = digits;
  if (digits.startsWith("0")) intl = "92" + digits.slice(1);
  else if (!digits.startsWith("92")) intl = "92" + digits;

  const amount = (outstandingPaise / 100).toLocaleString("en-PK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const text =
    `Assalam o Alaikum ${customerName || ""}`.trim() +
    `,\n\nThis is a friendly reminder from ${shopName}. ` +
    `Your outstanding balance is Rs ${amount}.\n\n` +
    `Please contact us if you have any questions. Thank you.`;

  return `https://wa.me/${intl}?text=${encodeURIComponent(text)}`;
}
