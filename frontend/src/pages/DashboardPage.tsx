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
import { useTranslation } from "@/lib/useTranslation";

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
  const { t, language } = useTranslation();

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
    if (h < 12) return t("dashboard.greetingMorning");
    if (h < 17) return t("dashboard.greetingAfternoon");
    return t("dashboard.greetingEvening");
  };

  const dateLabel = new Date().toLocaleDateString(language === "ur" ? "ur-PK" : "en-PK", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  return (
    <div className="min-h-full flex flex-col">
      {/* Page header */}
      <div className="px-6 pt-6 pb-4 border-b bg-gradient-to-r from-primary/5 via-primary/[0.03] to-transparent animate-fade-up grid grid-cols-3 items-end gap-4">
        {/* Left: greeting + role — smaller, sits lower (subscript-like) */}
        <div className="text-start min-w-0 translate-y-2">
          <p className="text-xs font-semibold text-muted-foreground leading-tight truncate">
            {greeting()}{user?.first_name ? `, ${user.first_name}` : ""}
          </p>
          <p className="text-[11px] text-muted-foreground/70 capitalize mt-0.5">{user?.role}</p>
        </div>

        {/* Center: shop name, large and prominent */}
        <div className="text-center">
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-blue-800">
            Bolan Sports Quetta
          </h1>
        </div>

        {/* Right: date — smaller, sits lower (subscript-like) */}
        <div className="text-end translate-y-2">
          <p className="text-xs text-muted-foreground">{dateLabel}</p>
        </div>
      </div>

      <div className="flex-1 p-6 space-y-6">

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-up-delay-1">
          <StatCard
            icon={Package}
            label={t("dashboard.statTotalProducts")}
            value={totalProducts.toLocaleString()}
            sub={<Link to="/products" className="hover:underline text-primary">{t("dashboard.viewCatalogue")}</Link>}
            accent="blue"
            to="/products"
          />
          <StatCard
            icon={AlertTriangle}
            label={t("dashboard.statLowStock")}
            value={lowStockProducts.length}
            sub={
              lowStockProducts.length > 0
                ? <Link to="/products" className="hover:underline text-amber-600">{t("dashboard.viewItems")}</Link>
                : t("dashboard.allLevelsOk")
            }
            accent="amber"
          />
          <StatCard
            icon={TrendingUp}
            label={t("dashboard.statRevenueToday")}
            value={
              todaySummary
                ? paiseToRupees(todaySummary.total_revenue_paise)
                : <span className="text-muted-foreground text-lg">—</span>
            }
            sub={
              todaySummary && todaySummary.total_discount_paise > 0
                ? t("dashboard.discountsGiven", { amount: paiseToRupees(todaySummary.total_discount_paise) })
                : t("dashboard.noDiscountsToday")
            }
            accent="green"
          />
          <StatCard
            icon={Receipt}
            label={t("dashboard.statTransactionsToday")}
            value={todaySummary?.transaction_count ?? "—"}
            sub={
              todaySummary && Object.keys(todaySummary.payment_breakdown).length > 0
                ? Object.entries(todaySummary.payment_breakdown)
                    .map(([m, v]) => `${m}: ${v.count}`)
                    .join(" · ")
                : t("dashboard.noSalesYet")
            }
            accent="purple"
          />
        </div>

        {/* Quick actions */}
        <div className="animate-fade-up-delay-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
            {t("dashboard.quickActions")}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              {
                to: "/checkout",
                label: t("dashboard.newSale"),
                desc: t("dashboard.openCheckout"),
                icon: ShoppingCart,
                cls: "bg-primary text-primary-foreground hover:bg-primary/90",
              },
              {
                to: "/products",
                label: t("dashboard.addStock"),
                desc: t("dashboard.stockInManage"),
                icon: Package,
                cls: "bg-emerald-600 text-white hover:bg-emerald-700",
              },
              {
                to: "/audit",
                label: t("dashboard.reportsLabel"),
                desc: t("dashboard.salesAndInventory"),
                icon: BarChart3,
                cls: "bg-purple-600 text-white hover:bg-purple-700",
              },
              {
                to: "/shifts",
                label: t("dashboard.shiftsLabel"),
                desc: currentShift ? t("dashboard.closeCurrentShift") : t("dashboard.openNewShift"),
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
                <ArrowRight className="h-4 w-4 ms-auto shrink-0 opacity-60" />
              </Link>
            ))}
          </div>
        </div>

        {/* Main grid: Recent sales + Shift status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-up-delay-3">

          {/* Recent sales — takes 2 of 3 columns */}
          <div className="lg:col-span-2 border rounded-xl overflow-hidden shadow-sm">
            <div className="px-4 py-3 border-b bg-muted/30 flex items-center justify-between">
              <h2 className="font-semibold text-sm">{t("dashboard.recentSales")}</h2>
              <Link to="/bills" className="text-xs text-primary hover:underline flex items-center gap-1">
                {t("dashboard.viewAll")} <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            {recentSales.length === 0 ? (
              <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                {t("dashboard.noSalesRecordedPrefix")}{" "}
                <Link to="/checkout" className="text-primary hover:underline">{t("checkout.checkoutTitle")}</Link>{" "}
                {t("dashboard.noSalesRecordedSuffix")}
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
              <h2 className="font-semibold text-sm">{t("dashboard.shiftStatus")}</h2>
              <Link to="/shifts" className="text-xs text-primary hover:underline">
                {t("dashboard.manage")}
              </Link>
            </div>
            <div className="flex-1 px-4 py-4">
              {currentShift ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-sm font-medium text-emerald-700">{t("dashboard.shiftOpen")}</span>
                  </div>
                  <div className="space-y-1.5 text-xs text-muted-foreground">
                    <p>{t("dashboard.shiftHash")} <span className="font-mono font-medium">#{currentShift.id}</span></p>
                    <p>
                      {t("dashboard.opened")}{" "}
                      {new Date(currentShift.opened_at).toLocaleTimeString(language === "ur" ? "ur-PK" : "en-PK", {
                        hour: "2-digit", minute: "2-digit",
                      })}
                    </p>
                    <p>{t("dashboard.float")} <span className="font-medium">{paiseToRupees(currentShift.opening_float_paise)}</span></p>
                  </div>
                  <Link to="/shifts">
                    <Button size="sm" variant="outline" className="w-full mt-2">
                      {t("dashboard.closeShift")}
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-gray-300" />
                    <span className="text-sm font-medium text-muted-foreground">{t("dashboard.noOpenShift")}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t("dashboard.openShiftHint")}
                  </p>
                  <Link to="/shifts">
                    <Button size="sm" className="w-full mt-2">
                      {t("dashboard.openShift")}
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
                <h2 className="font-semibold text-sm text-amber-800">{t("dashboard.lowStockAlert")}</h2>
                <Badge variant="warning">{lowStockProducts.length}</Badge>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link to="/products">{t("dashboard.manageStock")}</Link>
              </Button>
            </div>
            <div className="divide-y">
              {lowStockProducts.slice(0, 6).map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between px-4 py-2.5 text-sm hover:bg-amber-50/30 transition-colors"
                >
                  <div>
                    <span className="font-mono text-xs text-muted-foreground me-2">{p.sku}</span>
                    <span className="font-medium">{p.name}</span>
                  </div>
                  <div className="flex items-center gap-3 text-right">
                    <span className="text-amber-600 font-bold tabular-nums">
                      {p.stock_qty} {p.unit}
                    </span>
                    <span className="text-muted-foreground text-xs hidden sm:inline">
                      {t("dashboard.min")} {p.low_stock_threshold}
                    </span>
                  </div>
                </div>
              ))}
              {lowStockProducts.length > 6 && (
                <div className="px-4 py-2 text-xs text-muted-foreground text-center">
                  +{lowStockProducts.length - 6} {t("dashboard.more")}{" "}
                  <Link to="/products" className="text-primary hover:underline">{t("dashboard.viewAllLower")}</Link>
                </div>
              )}
            </div>
          </div>
        )}

      </div>

      {/* Page footer */}
      <footer className="px-6 py-3 border-t text-center text-xs text-muted-foreground/60 bg-muted/20">
        {t("dashboard.footerBuiltBy")}{" "}
        <span className="font-semibold text-muted-foreground">Neuroqaa.ai</span>
      </footer>
    </div>
  );
}