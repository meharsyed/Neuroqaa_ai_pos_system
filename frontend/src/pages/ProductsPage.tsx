import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { useState, useEffect, type ReactNode } from "react";

/** Format stock quantity: whole-number units show as integers; continuous units keep meaningful decimals. */
function fmtQty(qty: string, unit: string): string {
  const n = parseFloat(qty);
  if (isNaN(n)) return qty;
  const discrete = ["pcs", "box", "dozen", "bundle"];
  if (discrete.includes(unit.toLowerCase())) return Math.round(n).toLocaleString();
  // Strip trailing zeros up to 3 decimal places
  return parseFloat(n.toFixed(3)).toString();
}
import { useQuery } from "@tanstack/react-query";
import { Search, Plus, Upload, PackageX, RefreshCw, Download, Package, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ProductImage } from "@/components/ProductImage";
import { ProductModal } from "@/components/catalog/ProductModal";
import { StockInModal } from "@/components/catalog/StockInModal";
import { catalogApi } from "@/lib/catalog";
import { Money } from "@/components/ui/money";
import { reportsApi, downloadCsv } from "@/lib/reports";
import type { Product, ProductFilters } from "@/types/catalog";

type ProductsTab = "catalogue" | "inventory";

function SummaryCard({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border p-4 space-y-1">
      <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
      <p className="text-xl font-bold tabular-nums">{value}</p>
    </div>
  );
}


export default function ProductsPage() {
  const [tab, setTab] = useState<ProductsTab>("catalogue");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<number | "">("");
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [productModalOpen, setProductModalOpen] = useState(false);
  const [stockInModalOpen, setStockInModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [importStatus, setImportStatus] = useState<string | null>(null);

  // Debounce search input (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

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

  const { data: invData, isLoading: invLoading } = useQuery({
    queryKey: ["report-inventory"],
    queryFn: reportsApi.inventory,
    enabled: tab === "inventory",
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
    <PageContainer>
      <PageHeader
        title="Products"
        subtitle={`${totalCount.toLocaleString()} items${lowStockProducts.length > 0 ? ` · ${lowStockProducts.length} low stock` : ""}`}
        actions={
          <div className="flex items-center gap-2">
            {tab === "catalogue" ? (
              <>
                <label className="cursor-pointer">
                  <input type="file" accept=".csv" className="hidden" onChange={handleImportCsv} />
                  <Button variant="outline" size="sm" asChild>
                    <span><Upload className="h-4 w-4 mr-1" /> Import CSV</span>
                  </Button>
                </label>
                <Button size="sm" onClick={openAddModal}>
                  <Plus className="h-4 w-4 mr-1" /> New Product
                </Button>
              </>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => downloadCsv("/reports/inventory/?export=csv", "inventory-valuation.csv")}
              >
                <Download className="h-4 w-4 mr-1" /> Export CSV
              </Button>
            )}
          </div>
        }
      />

      <div className="space-y-4">

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {(
          [
            { key: "catalogue" as const, label: "Catalogue", icon: Package },
            { key: "inventory" as const, label: "Inventory Value", icon: Wallet },
          ]
        ).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {tab === "inventory" ? (
        <div className="space-y-6">
          {invLoading && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="rounded-lg border p-4">
                    <Skeleton className="h-3 w-24 mb-2" />
                    <Skeleton className="h-6 w-32" />
                  </div>
                ))}
              </div>
              <div className="rounded-lg border overflow-hidden">
                <div className="bg-muted/50 p-3">
                  <div className="grid grid-cols-5 gap-4">
                    {[...Array(5)].map((_, i) => (
                      <Skeleton key={i} className="h-4 w-16" />
                    ))}
                  </div>
                </div>
                <div className="space-y-2">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="px-4 py-3 border-b grid grid-cols-5 gap-4">
                      <Skeleton className="h-4 w-12" />
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-4 w-8 ml-auto" />
                      <Skeleton className="h-4 w-16 ml-auto" />
                      <Skeleton className="h-4 w-16 ml-auto" />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          {invData && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <SummaryCard label="Cost Value" value={<Money paise={invData.total_cost_value_paise} />} />
                <SummaryCard label="Sell Value" value={<Money paise={invData.total_sell_value_paise} />} />
                <SummaryCard label="Potential Profit" value={<Money paise={invData.potential_profit_paise} />} />
              </div>
              <div className="rounded-lg border overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium">SKU</th>
                      <th className="px-4 py-2 text-left font-medium">Product</th>
                      <th className="px-4 py-2 text-right font-medium">Stock</th>
                      <th className="px-4 py-2 text-right font-medium">Cost Value</th>
                      <th className="px-4 py-2 text-right font-medium">Sell Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {invData.products.map((p) => (
                      <tr key={p.sku}>
                        <td className="px-4 py-2 font-mono text-xs">{p.sku}</td>
                        <td className="px-4 py-2">{p.name}</td>
                        <td className="px-4 py-2 text-right tabular-nums">{p.stock_qty}</td>
                        <td className="px-4 py-2 text-right tabular-nums font-mono">
                          <Money paise={p.cost_value_paise} />
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums font-mono">
                          <Money paise={p.sell_value_paise} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      ) : (
      <>
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
              <>
                {[...Array(6)].map((_, i) => (
                  <tr key={i}>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-12" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-16 ml-auto" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-12 ml-auto" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-16 mx-auto" /></td>
                    <td className="px-4 py-3"><Skeleton className="h-4 w-20 ml-auto" /></td>
                  </tr>
                ))}
              </>
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
                <td colSpan={8} className="px-4 py-8">
                  <EmptyState
                    icon={PackageX}
                    title="No products found"
                    description={search ? "Try adjusting your search or filters." : "Add your first product to get started."}
                    action={!search ? (
                      <Button size="sm" onClick={openAddModal}>
                        Add your first product
                      </Button>
                    ) : undefined}
                  />
                </td>
              </tr>
            )}
            {products.map((product) => (
              <tr key={product.id} className="hover:bg-muted/30 transition-colors">
                <td className="px-4 py-3 font-mono text-xs">{product.sku}</td>
                <td className="px-4 py-3 font-medium">
                  <div className="flex items-center gap-3">
                    <ProductImage
                      imageUrl={product.image_url}
                      productName={product.name}
                      size="md"
                    />
                    <span className="max-w-[150px] truncate" title={product.name}>
                      {product.name}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{product.category_name ?? "—"}</td>
                <td className="px-4 py-3 text-muted-foreground">{product.unit}</td>
                <td className="px-4 py-3 text-right tabular-nums">{product.sell_price}</td>
                <td className="px-4 py-3 text-right tabular-nums">
                  <span className={parseFloat(product.stock_qty) === 0 ? "text-red-600 font-semibold" : product.is_low_stock ? "text-amber-600 font-semibold" : ""}>
                    {fmtQty(product.stock_qty, product.unit)}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  {parseFloat(product.stock_qty) === 0 ? (
                    <Badge variant="danger">Out of Stock</Badge>
                  ) : product.is_low_stock ? (
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
      </>
      )}
      </div>

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
    </PageContainer>
  );
}