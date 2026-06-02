import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Package, AlertTriangle, TrendingUp, Receipt,
  ShoppingCart, ArrowRight, BarChart3, Clock,
  CheckCircle2, XCircle,
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { catalogApi, paiseToRupees } from "@/lib/catalog";
import { salesApi } from "@/lib/sales";
import { reportsApi } from "@/lib/reports";
import { shiftsApi } from "@/lib/shifts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

function today() {
  return new Date().toISOString().slice(0, 10);
}

function formatDt(iso: string) {
  return new Date(iso).toLocaleString("en-PK", {
    month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
  accent,
  to,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  accent?: "blue" | "amber" | "green" | "purple";
  to?: string;
}) {
  const accentMap = {
    blue:   "border-l-blue-500   bg-blue-50/40",
    amber:  "border-l-amber-500  bg-amber-50/40",
    green:  "border-l-emerald-500 bg-emerald-50/40",
    purple: "border-l-purple-500 bg-purple-50/40",
  };
  const iconMap = {
    blue:   "text-blue-500",
    amber:  "text-amber-500",
    green:  "text-emerald-500",
    purple: "text-purple-500",
  };

  const card = (
    <div
      className={`border rounded-xl p-4 space-y-2 border-l-4 shadow-sm transition-shadow hover:shadow-md ${
        accent ? accentMap[accent] : "border-l-border"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        <Icon className={`h-4 w-4 ${accent ? iconMap[accent] : "text-muted-foreground"}`} />
      </div>
      <p className="text-2xl font-bold tabular-nums leading-none">{value}</p>
      {sub && <div className="text-xs text-muted-foreground">{sub}</div>}
    </div>
  );

  return to ? <Link to={to}>{card}</Link> : card;
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const todayStr = today();

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

  const { data: todaySummary } = useQuery({
    queryKey: ["report-daily", todayStr],
    queryFn: () => reportsApi.daily(todayStr),
    staleTime: 60_000,
  });

  const { data: recentSalesData } = useQuery({
    queryKey: ["sales", { page: 1 }],
    queryFn: () => salesApi.list({ page: 1 }),
    staleTime: 30_000,
  });

  const { data: currentShift } = useQuery({
    queryKey: ["shift-current"],
    queryFn: shiftsApi.current,
    retry: false,
    staleTime: 30_000,
  });

  const totalProducts = productsData?.count ?? 0;
  const recentSales = recentSalesData?.results?.slice(0, 6) ?? [];

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
  };

  const dateLabel = new Date().toLocaleDateString("en-PK", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  return (
    <div className="min-h-full flex flex-col">
      {/* Page header */}
      <div className="px-6 pt-6 pb-4 border-b bg-gradient-to-r from-primary/5 via-primary/[0.03] to-transparent animate-fade-up">
        <h1 className="text-2xl font-bold tracking-tight">
          {greeting()}{user?.first_name ? `, ${user.first_name}` : ""}
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          <span className="capitalize font-medium">{user?.role}</span>
          <span className="mx-1.5 text-border">·</span>
          {dateLabel}
        </p>
      </div>

      <div className="flex-1 p-6 space-y-6">

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-up-delay-1">
          <StatCard
            icon={Package}
            label="Total Products"
            value={totalProducts.toLocaleString()}
            sub={<Link to="/products" className="hover:underline text-primary">View catalogue →</Link>}
            accent="blue"
            to="/products"
          />
          <StatCard
            icon={AlertTriangle}
            label="Low Stock"
            value={lowStockProducts.length}
            sub={
              lowStockProducts.length > 0
                ? <Link to="/products" className="hover:underline text-amber-600">View items →</Link>
                : "All levels OK"
            }
            accent="amber"
          />
          <StatCard
            icon={TrendingUp}
            label="Revenue Today"
            value={
              todaySummary
                ? paiseToRupees(todaySummary.total_revenue_paise)
                : <span className="text-muted-foreground text-lg">—</span>
            }
            sub={
              todaySummary && todaySummary.total_discount_paise > 0
                ? `${paiseToRupees(todaySummary.total_discount_paise)} discounts given`
                : "No discounts today"
            }
            accent="green"
          />
          <StatCard
            icon={Receipt}
            label="Transactions Today"
            value={todaySummary?.transaction_count ?? "—"}
            sub={
              todaySummary && Object.keys(todaySummary.payment_breakdown).length > 0
                ? Object.entries(todaySummary.payment_breakdown)
                    .map(([m, v]) => `${m}: ${v.count}`)
                    .join(" · ")
                : "No sales yet"
            }
            accent="purple"
          />
        </div>

        {/* Quick actions */}
        <div className="animate-fade-up-delay-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
            Quick Actions
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              {
                to: "/checkout",
                label: "New Sale",
                desc: "Open checkout",
                icon: ShoppingCart,
                cls: "bg-primary text-primary-foreground hover:bg-primary/90",
              },
              {
                to: "/products",
                label: "Add Stock",
                desc: "Stock in / manage",
                icon: Package,
                cls: "bg-emerald-600 text-white hover:bg-emerald-700",
              },
              {
                to: "/reports",
                label: "Reports",
                desc: "Sales & inventory",
                icon: BarChart3,
                cls: "bg-purple-600 text-white hover:bg-purple-700",
              },
              {
                to: "/shifts",
                label: "Shifts",
                desc: currentShift ? "Close current shift" : "Open a new shift",
                icon: Clock,
                cls: "bg-amber-500 text-white hover:bg-amber-600",
              },
            ].map(({ to, label, desc, icon: Icon, cls }) => (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-3 rounded-xl p-4 transition-all shadow-sm hover:shadow-md ${cls}`}
              >
                <Icon className="h-5 w-5 shrink-0 opacity-90" />
                <div className="min-w-0">
                  <p className="font-semibold text-sm leading-tight">{label}</p>
                  <p className="text-xs opacity-75 truncate">{desc}</p>
                </div>
                <ArrowRight className="h-4 w-4 ml-auto shrink-0 opacity-60" />
              </Link>
            ))}
          </div>
        </div>

        {/* Main grid: Recent sales + Shift status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-up-delay-3">

          {/* Recent sales — takes 2 of 3 columns */}
          <div className="lg:col-span-2 border rounded-xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b bg-muted/30 flex items-center justify-between">
              <h2 className="font-semibold text-sm">Recent Sales</h2>
              <Link to="/reports" className="text-xs text-primary hover:underline flex items-center gap-1">
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            {recentSales.length === 0 ? (
              <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                No sales recorded yet. Start from the{" "}
                <Link to="/checkout" className="text-primary hover:underline">Checkout</Link> page.
              </div>
            ) : (
              <div className="divide-y">
                {recentSales.map((sale) => (
                  <div key={sale.id} className="flex items-center px-4 py-2.5 gap-3 text-sm">
                    <div className="shrink-0">
                      {sale.status === "completed" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-400" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-xs font-medium truncate">{sale.sale_number}</p>
                      <p className="text-xs text-muted-foreground">{sale.cashier_name}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="font-semibold tabular-nums">{paiseToRupees(sale.total_paise)}</p>
                      <p className="text-xs text-muted-foreground">{formatDt(sale.created_at)}</p>
                    </div>
                    <Badge
                      variant={sale.status === "completed" ? "success" : "destructive"}
                      className="shrink-0 hidden sm:inline-flex"
                    >
                      {sale.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Shift status widget */}
          <div className="border rounded-xl overflow-hidden shadow-sm flex flex-col">
            <div className="px-4 py-3 border-b bg-muted/30 flex items-center justify-between">
              <h2 className="font-semibold text-sm">Shift Status</h2>
              <Link to="/shifts" className="text-xs text-primary hover:underline">
                Manage
              </Link>
            </div>
            <div className="flex-1 px-4 py-4">
              {currentShift ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-sm font-medium text-emerald-700">Shift Open</span>
                  </div>
                  <div className="space-y-1.5 text-xs text-muted-foreground">
                    <p>Shift <span className="font-mono font-medium">#{currentShift.id}</span></p>
                    <p>
                      Opened:{" "}
                      {new Date(currentShift.opened_at).toLocaleTimeString("en-PK", {
                        hour: "2-digit", minute: "2-digit",
                      })}
                    </p>
                    <p>Float: <span className="font-medium">{paiseToRupees(currentShift.opening_float_paise)}</span></p>
                  </div>
                  <Link to="/shifts">
                    <Button size="sm" variant="outline" className="w-full mt-2">
                      Close Shift
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-gray-300" />
                    <span className="text-sm font-medium text-muted-foreground">No Open Shift</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Open a shift before starting sales to enable cash reconciliation.
                  </p>
                  <Link to="/shifts">
                    <Button size="sm" className="w-full mt-2">
                      Open Shift
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Low stock alert */}
        {lowStockProducts.length > 0 && (
          <div className="border rounded-xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b bg-amber-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                <h2 className="font-semibold text-sm text-amber-800">Low Stock Alert</h2>
                <Badge variant="warning">{lowStockProducts.length}</Badge>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link to="/products">Manage Stock</Link>
              </Button>
            </div>
            <div className="divide-y">
              {lowStockProducts.slice(0, 6).map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between px-4 py-2.5 text-sm hover:bg-amber-50/30 transition-colors"
                >
                  <div>
                    <span className="font-mono text-xs text-muted-foreground mr-2">{p.sku}</span>
                    <span className="font-medium">{p.name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-right">
                    <span className="text-amber-600 font-bold tabular-nums">
                      {p.stock_qty} {p.unit}
                    </span>
                    <span className="text-muted-foreground text-xs hidden sm:inline">
                      min {p.low_stock_threshold}
                    </span>
                  </div>
                </div>
              ))}
              {lowStockProducts.length > 6 && (
                <div className="px-4 py-2 text-xs text-muted-foreground text-center">
                  +{lowStockProducts.length - 6} more —{" "}
                  <Link to="/products" className="text-primary hover:underline">view all</Link>
                </div>
              )}
            </div>
          </div>
        )}

      </div>

      {/* Page footer */}
      <footer className="px-6 py-3 border-t text-center text-xs text-muted-foreground/60 bg-muted/20">
        Neuroqaa POS · Built by{" "}
        <span className="font-semibold text-muted-foreground">Neuroqaa.ai</span>
      </footer>
    </div>
  );
}