import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Package, AlertTriangle, TrendingUp } from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { catalogApi } from "@/lib/catalog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  const { data: lowStockProducts = [] } = useQuery({
    queryKey: ["low-stock"],
    queryFn: catalogApi.products.lowStock,
    staleTime: 60_000,
  });

  const { data: productsData } = useQuery({
    queryKey: ["products", { page: 1 }],
    queryFn: () => catalogApi.products.list({ page: 1 }),
    staleTime: 60_000,
  });

  const totalProducts = productsData?.count ?? 0;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">
          Welcome back{user?.first_name ? `, ${user.first_name}` : ""}
        </h1>
        <p className="text-sm text-muted-foreground capitalize">{user?.role} · Neuroqaa POS</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="border rounded-lg p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Package className="h-4 w-4" />
            <span>Total Products</span>
          </div>
          <p className="text-2xl font-bold tabular-nums">{totalProducts.toLocaleString()}</p>
          <Link to="/products" className="text-xs text-primary hover:underline">
            View all →
          </Link>
        </div>

        <div className={`border rounded-lg p-4 space-y-1 ${lowStockProducts.length > 0 ? "border-amber-300 bg-amber-50/50" : ""}`}>
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <AlertTriangle className={`h-4 w-4 ${lowStockProducts.length > 0 ? "text-amber-500" : ""}`} />
            <span>Low Stock</span>
          </div>
          <p className={`text-2xl font-bold tabular-nums ${lowStockProducts.length > 0 ? "text-amber-600" : ""}`}>
            {lowStockProducts.length}
          </p>
          {lowStockProducts.length > 0 ? (
            <Link to="/products" className="text-xs text-amber-600 hover:underline">
              View items →
            </Link>
          ) : (
            <p className="text-xs text-muted-foreground">All stock levels OK</p>
          )}
        </div>

        <div className="border rounded-lg p-4 space-y-1">
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <TrendingUp className="h-4 w-4" />
            <span>Sales Today</span>
          </div>
          <p className="text-2xl font-bold tabular-nums">—</p>
          <p className="text-xs text-muted-foreground">Coming in Phase 3</p>
        </div>
      </div>

      {/* Low stock alert table */}
      {lowStockProducts.length > 0 && (
        <div className="border rounded-lg">
          <div className="px-4 py-3 border-b flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <h2 className="font-semibold text-sm">Low Stock Alert</h2>
              <Badge variant="warning">{lowStockProducts.length}</Badge>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link to="/products">Manage Stock</Link>
            </Button>
          </div>
          <div className="divide-y">
            {lowStockProducts.slice(0, 8).map((p) => (
              <div key={p.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
                <div>
                  <span className="font-mono text-xs text-muted-foreground mr-2">{p.sku}</span>
                  <span className="font-medium">{p.name}</span>
                </div>
                <div className="flex items-center gap-3 text-right">
                  <span className="text-amber-600 font-semibold tabular-nums">
                    {p.stock_qty} {p.unit}
                  </span>
                  <span className="text-muted-foreground text-xs">
                    (min {p.low_stock_threshold})
                  </span>
                </div>
              </div>
            ))}
            {lowStockProducts.length > 8 && (
              <div className="px-4 py-2 text-xs text-muted-foreground text-center">
                +{lowStockProducts.length - 8} more —{" "}
                <Link to="/products" className="text-primary hover:underline">view all</Link>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}