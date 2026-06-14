import { apiClient } from "./axios";
import type { AuditReport, DailySummary, DateRangeSummary, InventoryValuation } from "@/types/config";

export const reportsApi = {
  daily: (date: string) =>
    apiClient.get<DailySummary>("/reports/daily/", { params: { date } }).then((r) => r.data),

  dateRange: (start: string, end: string) =>
    apiClient
      .get<DateRangeSummary>("/reports/date-range/", { params: { start, end } })
      .then((r) => r.data),

  inventory: () =>
    apiClient.get<InventoryValuation>("/reports/inventory/").then((r) => r.data),

  audit: (start: string, end: string) =>
    apiClient
      .get<AuditReport>("/reports/audit/", { params: { start, end } })
      .then((r) => r.data),
};

export function downloadAuditPdf(start: string, end: string) {
  return apiClient
    .get<Blob>("/reports/audit/", {
      params: { start, end, export: "pdf" },
      responseType: "blob",
    })
    .then((r) => {
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-${start}-to-${end}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    });
}

export function downloadCsv(url: string, filename: string) {
  return apiClient
    .get<Blob>(url, { responseType: "blob" })
    .then((r) => {
      const blobUrl = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(blobUrl);
    });
}

export function openReceiptPdf(saleId: number) {
  return apiClient
    .get<Blob>(`/sales/${saleId}/receipt/pdf/`, { responseType: "blob" })
    .then((r) => {
      const blobUrl = URL.createObjectURL(r.data);
      window.open(blobUrl, "_blank");
    });
}

export function printReceipt(saleId: number) {
  return apiClient
    .post<{ detail: string }>(`/sales/${saleId}/receipt/print/`)
    .then((r) => r.data);
}