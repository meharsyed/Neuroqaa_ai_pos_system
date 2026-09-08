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
  Supplier,
} from "../types/catalog";

export const catalogApi = {
  categories: {
    list: () =>
      apiClient.get<PaginatedResponse<Category>>("/categories/").then((r) => r.data.results),
  },

  suppliers: {
    list: (params?: { search?: string; include_inactive?: boolean; page?: number }) =>
      apiClient.get<PaginatedResponse<Supplier>>("/suppliers/", { params }).then((r) => r.data),

    get: (id: number) =>
      apiClient.get<Supplier>(`/suppliers/${id}/`).then((r) => r.data),

    create: (data: Partial<Omit<Supplier, "id" | "is_active" | "created_at" | "updated_at">>) =>
      apiClient.post<Supplier>("/suppliers/", data).then((r) => r.data),

    update: (id: number, data: Partial<Omit<Supplier, "id" | "created_at" | "updated_at">>) =>
      apiClient.patch<Supplier>(`/suppliers/${id}/`, data).then((r) => r.data),

    /**
     * Deactivates a supplier with purchase history under it (archived is: true
     * in the response), or deletes outright a supplier that's never been used.
     */
    remove: (id: number) =>
      apiClient
        .delete<{ archived: boolean; detail: string }>(`/suppliers/${id}/`)
        .then((r) => r.data),

    restore: (id: number) =>
      apiClient.post<Supplier>(`/suppliers/${id}/restore/`).then((r) => r.data),

    /**
     * A supplier's purchase history — no dedicated endpoint. The append-only
     * stock movements ledger already has everything (product, qty, cost,
     * date); this just filters it down to what this supplier was stocked in
     * against.
     */
    purchaseHistory: (supplierId: number, page = 1) =>
      apiClient
        .get<PaginatedResponse<StockMovement>>("/movements/", {
          params: { supplier: supplierId, movement_type: "stock_in", page },
        })
        .then((r) => r.data),
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

    /**
     * Remove a product. The server archives it when it has been sold or
     * stocked before — deleting the row would corrupt every bill it appears
     * on — and deletes it outright only when it has no history at all.
     */
    remove: (id: number) =>
      apiClient
        .delete<{ archived: boolean; detail: string }>(`/products/${id}/`)
        .then((r) => r.data),

    restore: (id: number) =>
      apiClient.post<Product>(`/products/${id}/restore/`).then((r) => r.data),

    /** Ask which of the two will happen, so the button can say the right word. */
    removalCheck: (id: number) =>
      apiClient
        .get<{ can_delete: boolean; reasons: string[]; is_active: boolean }>(
          `/products/${id}/removal-check/`
        )
        .then((r) => r.data),

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

    uploadImage: (productId: number, formData: FormData) =>
      apiClient
        .patch<Product>(
          `/products/${productId}/`,
          formData,
          { headers: { "Content-Type": "multipart/form-data" } }
        )
        .then((r) => r.data),
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