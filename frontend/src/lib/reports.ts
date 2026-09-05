import { apiClient } from "./axios";
import type { AuditReport, DailySummary, InventoryValuation } from "@/types/config";

export const reportsApi = {
  daily: (date: string) =>
    apiClient.get<DailySummary>("/reports/daily/", { params: { date } }).then((r) => r.data),

  inventory: () =>
    apiClient.get<InventoryValuation>("/reports/inventory/").then((r) => r.data),

  audit: (start: string, end: string, detailed = false) =>
    apiClient
      .get<AuditReport>("/reports/audit/", { params: { start, end, detailed } })
      .then((r) => r.data),
};

export function downloadAuditPdf(start: string, end: string, detailed = false) {
  return apiClient
    .get<Blob>("/reports/audit/", {
      params: { start, end, export: "pdf", detailed },
      responseType: "blob",
    })
    .then((r) => {
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-${start}-to-${end}${detailed ? "-detailed" : ""}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    });
}

export function downloadAuditCsv(start: string, end: string, detailed = false) {
  return apiClient
    .get<Blob>("/reports/audit/", {
      params: { start, end, export: "csv", detailed },
      responseType: "blob",
    })
    .then((r) => {
      const url = URL.createObjectURL(r.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-${start}-to-${end}${detailed ? "-detailed" : ""}.csv`;
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

export type ReceiptTemplate = "thermal" | "invoice";

export function openReceiptPdf(saleId: number, template: ReceiptTemplate = "thermal") {
  return apiClient
    .get<Blob>(`/sales/${saleId}/receipt/pdf/`, {
      params: { template },
      responseType: "blob",
    })
    .then((r) => {
      const blobUrl = URL.createObjectURL(r.data);
      const win = window.open(blobUrl, "_blank");
      if (!win) {
        alert("Popup blocked. Please allow popups for this site.");
      }
    })
    .catch((err) => {
      console.error("Receipt PDF error:", err);
      const detail = err.response?.data?.detail || err.message;
      alert(`Failed to load receipt: ${detail}`);
    });
}

export function printReceipt(saleId: number) {
  return apiClient
    .post<{ detail: string }>(`/sales/${saleId}/receipt/print/`)
    .then((r) => r.data);
}