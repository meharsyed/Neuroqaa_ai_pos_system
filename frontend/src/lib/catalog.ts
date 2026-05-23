import { apiClient } from "./axios";
import type {
  Category,
  Inventory,
  PaginatedResponse,
  Product,
  ProductFilters,
  ProductFormValues,
  StockInFormValues,
  StockMovement,
} from "../types/catalog";

export const catalogApi = {
  categories: {
    list: () =>
      apiClient.get<PaginatedResponse<Category>>("/categories/").then((r) => r.data.results),
  },

  products: {
    list: (filters?: ProductFilters) =>
      apiClient
        .get<PaginatedResponse<Product>>("/products/", { params: filters })
        .then((r) => r.data),

    get: (id: number) =>
      apiClient.get<Product>(`/products/${id}/`).then((r) => r.data),

    create: (data: Partial<ProductFormValues>) =>
      apiClient.post<Product>("/products/", data).then((r) => r.data),

    update: (id: number, data: Partial<ProductFormValues>) =>
      apiClient.patch<Product>(`/products/${id}/`, data).then((r) => r.data),

    lowStock: () =>
      apiClient.get<Product[]>("/products/low-stock/").then((r) => r.data),

    byBarcode: (barcode: string) =>
      apiClient.get<Product>(`/products/barcode/${encodeURIComponent(barcode)}/`).then((r) => r.data),

    importCsv: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return apiClient
        .post<{ imported: number; updated: number; skipped: number }>(
          "/products/import/",
          fd,
          { headers: { "Content-Type": "multipart/form-data" } }
        )
        .then((r) => r.data);
    },
  },

  inventory: {
    list: () =>
      apiClient.get<PaginatedResponse<Inventory>>("/inventory/").then((r) => r.data),

    stockIn: (data: StockInFormValues) =>
      apiClient.post<StockMovement>("/inventory/stock-in/", data).then((r) => r.data),
  },
};

// Utility: convert Rs string/number to integer paise
export function rupeesToPaise(rupees: string | number): number {
  const n = parseFloat(String(rupees).replace(/,/g, ""));
  return isNaN(n) ? 0 : Math.round(n * 100);
}

// Utility: convert paise integer to Rs string
export function paiseToRupees(paise: number): string {
  return `Rs. ${(paise / 100).toLocaleString("en-PK", { minimumFractionDigits: 2 })}`;
}