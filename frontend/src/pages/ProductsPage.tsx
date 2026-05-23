import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Plus, Upload, PackageX, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ProductModal } from "@/components/catalog/ProductModal";
import { StockInModal } from "@/components/catalog/StockInModal";
import { catalogApi } from "@/lib/catalog";
import type { Product, ProductFilters } from "@/types/catalog";

function useDebounce<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);
  const timeoutRef = useState<ReturnType<typeof setTimeout> | null>(null);
  useState(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  });
  return debounced;
}

export default function ProductsPage() {
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<number | "">("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [productModalOpen, setProductModalOpen] = useState(false);
  const [stockInModalOpen, setStockInModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [importStatus, setImportStatus] = useState<string | null>(null);

  const debouncedSearch = search; // Simple: we'll re-query on each keystroke since TanStack Query deduplicates

  const filters: ProductFilters = {
    ...(debouncedSearch && { search: debouncedSearch }),
    ...(categoryFilter && { category: categoryFilter }),
    ...(lowStockOnly && { low_stock: true }),
    page,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["products", filters],
    queryFn: () => catalogApi.products.list(filters),
    staleTime: 30_000,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: catalogApi.categories.list,
  });

  const { data: lowStockProducts = [] } = useQuery({
    queryKey: ["low-stock"],
    queryFn: catalogApi.products.lowStock,
    staleTime: 60_000,
  });

  const products = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const totalPages = Math.ceil(totalCount / 50);

  function openAddModal() {
    setSelectedProduct(null);
    setProductModalOpen(true);
  }

  function openEditModal(product: Product) {
    setSelectedProduct(product);
    setProductModalOpen(true);
  }

  function openStockIn(product: Product) {
    setSelectedProduct(product);
    setStockInModalOpen(true);
  }

  async function handleImportCsv(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportStatus("Importing…");
    try {
      const result = await catalogApi.products.importCsv(file);
      setImportStatus(`Done — ${result.imported} imported, ${result.updated} updated`);
      refetch();
    } catch {
      setImportStatus("Import failed. Check CSV format.");
    }
    e.target.value = "";
    setTimeout(() => setImportStatus(null), 5000);
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Products</h1>
          <p className="text-sm text-muted-foreground">
            {totalCount.toLocaleString()} products
            {lowStockProducts.length > 0 && (
              <span className="ml-2">
                <Badge variant="warning">{lowStockProducts.length} low stock</Badge>
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* CSV import */}
          <label className="cursor-pointer">
            <input type="file" accept=".csv" className="hidden" onChange={handleImportCsv} />
            <Button variant="outline" size="sm" asChild>
              <span><Upload className="h-4 w-4 mr-1" /> Import CSV</span>
            </Button>
          </label>
          <Button size="sm" onClick={openAddModal}>
            <Plus className="h-4 w-4 mr-1" /> New Product
          </Button>
        </div>
      </div>

      {/* Import status */}
      {importStatus && (
        <div className="rounded-md bg-muted px-4 py-2 text-sm">{importStatus}</div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-8"
            placeholder="Search by name, SKU, barcode…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <Select
          className="w-48"
          options={categories.map((c) => ({ value: c.id, label: c.name }))}
          placeholder="All categories"
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value ? Number(e.target.value) : ""); setPage(1); }}
        />
        <Button
          variant={lowStockOnly ? "destructive" : "outline"}
          size="sm"
          onClick={() => { setLowStockOnly((v) => !v); setPage(1); }}
        >
          {lowStockOnly ? "⚠ Low Stock Only" : "All Stock"}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-md border overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left font-medium">SKU</th>
              <th className="px-4 py-3 text-left font-medium">Name</th>
              <th className="px-4 py-3 text-left font-medium">Category</th>
              <th className="px-4 py-3 text-left font-medium">Unit</th>
              <th className="px-4 py-3 text-right font-medium">Sell Price</th>
              <th className="px-4 py-3 text-right font-medium">Stock</th>
              <th className="px-4 py-3 text-center font-medium">Status</th>
              <th className="px-4 py-3 text-right font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                  Loading…
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-destructive">
                  Failed to load products.
                </td>
              </tr>
            )}
            {!isLoading && products.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-12 text-center">
                  <PackageX className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                  <p className="text-muted-foreground">No products found.</p>
                  {!search && (
                    <Button size="sm" className="mt-3" onClick={openAddModal}>
                      Add your first product
                    </Button>
                  )}
                </td>
              </tr>
            )}
            {products.map((product) => (
              <tr key={product.id} className="hover:bg-muted/30 transition-colors">
                <td className="px-4 py-3 font-mono text-xs">{product.sku}</td>
                <td className="px-4 py-3 font-medium max-w-[200px] truncate" title={product.name}>
                  {product.name}
                </td>
                <td className="px-4 py-3 text-muted-foreground">{product.category_name ?? "—"}</td>
                <td className="px-4 py-3 text-muted-foreground">{product.unit}</td>
                <td className="px-4 py-3 text-right tabular-nums">{product.sell_price}</td>
                <td className="px-4 py-3 text-right tabular-nums">
                  <span className={product.is_low_stock ? "text-amber-600 font-semibold" : ""}>
                    {product.stock_qty}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  {product.is_low_stock ? (
                    <Badge variant="warning">Low Stock</Badge>
                  ) : (
                    <Badge variant="success">OK</Badge>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openStockIn(product)}
                      title="Stock In"
                    >
                      +Stock
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditModal(product)}
                    >
                      Edit
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Page {page} of {totalPages} ({totalCount} total)
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline" size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline" size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Modals */}
      <ProductModal
        open={productModalOpen}
        onOpenChange={setProductModalOpen}
        product={selectedProduct}
      />
      <StockInModal
        open={stockInModalOpen}
        onOpenChange={setStockInModalOpen}
        product={selectedProduct}
      />
    </div>
  );
}