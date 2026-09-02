import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Package, AlertTriangle, TrendingUp, Receipt,
  ArrowRight, CheckCircle2, XCircle,
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
  trend,
  accent,
  to,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  trend?: { value: number; isPositive: boolean };
  accent?: "navy" | "orange" | "teal" | "gray" | "red";
  to?: string;
}) {
  const colorMap: Record<string, { border: string; bg: string; icon: string; gradient: string }> = {
    navy: {
      border: "border-teal-600",
      bg: "bg-gradient-to-br from-teal-50 to-cyan-25",
      icon: "text-teal-600",
      gradient: "from-teal-600 to-teal-500",
    },
    orange: {
      border: "border-orange-500",
      bg: "bg-gradient-to-br from-orange-50 to-red-25",
      icon: "text-orange-500",
      gradient: "from-orange-500 to-red-500",
    },
    teal: {
      border: "border-cyan-500",
      bg: "bg-gradient-to-br from-cyan-50 to-teal-25",
      icon: "text-cyan-500",
      gradient: "from-cyan-500 to-teal-500",
    },
    gray: {
      border: "border-slate-500",
      bg: "bg-gradient-to-br from-slate-50 to-gray-25",
      icon: "text-slate-500",
      gradient: "from-slate-600 to-slate-500",
    },
    red: {
      border: "border-red-600",
      bg: "bg-gradient-to-br from-red-50 to-rose-25",
      icon: "text-red-600",
      gradient: "from-red-600 to-red-500",
    },
  };

  const colors = accent && accent in colorMap ? colorMap[accent] : colorMap.navy;

  const card = (
    <div
      className={`stat-card-gradient border rounded-xl p-4 space-y-3 border-l-4 shadow-sm ${colors.border} ${colors.bg}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <Icon className={`h-5 w-5 ${colors.icon}`} />
      </div>
      <div className="space-y-1">
        <p className={`text-3xl font-black tabular-nums leading-none bg-gradient-to-r ${colors.gradient} bg-clip-text text-transparent`}>
          {value}
        </p>
        {trend && (
          <div className={`text-sm font-bold flex items-center gap-1 ${trend.isPositive ? "stat-trend-up text-sports-emerald" : "stat-trend-down text-sports-orange"}`}>
            {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}% {trend.isPositive ? "vs yesterday" : "vs yesterday"}
          </div>
        )}
      </div>
      {sub && <div className="text-xs text-muted-foreground pt-1">{sub}</div>}
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
      {/* Page header — Speed Tech Solutions Professional Compact */}
      <div className="px-6 py-3.5 border-b bg-white animate-fade-up border-slate-200">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Shop branding (compact) */}
          <div className="min-w-0 flex-shrink-0">
            <h1 className="text-lg font-bold text-slate-900 leading-tight">
              Speed Tech Solutions
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">Enterprise Security & Surveillance</p>
          </div>

          {/* Right: User info + date */}
          <div className="flex items-center gap-4 min-w-0">
            <div className="text-right">
              <p className="text-sm font-semibold text-slate-900 leading-tight">
                {greeting()}{user?.first_name ? ` ${user.first_name}` : ""}
              </p>
              <p className="text-xs text-slate-500 capitalize mt-0.5">{user?.role} Account</p>
            </div>
            <div className="h-10 w-px bg-slate-200 shrink-0" />
            <div className="text-right min-w-max">
              <p className="text-sm font-semibold text-slate-900">{dateLabel}</p>
              <p className="text-xs text-slate-500 mt-0.5">{new Date().toLocaleTimeString(language === "ur" ? "ur-PK" : "en-PK", { hour: "2-digit", minute: "2-digit" })}</p>
            </div>
          </div>
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
            trend={{ value: 8, isPositive: true }}
            accent="navy"
            to="/products"
          />
          <StatCard
            icon={AlertTriangle}
            label={t("dashboard.statLowStock")}
            value={lowStockProducts.length}
            sub={
              lowStockProducts.length > 0
                ? <Link to="/products" className="hover:underline text-orange-600">{t("dashboard.viewItems")}</Link>
                : t("dashboard.allLevelsOk")
            }
            accent="red"
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
            trend={{ value: 15, isPositive: true }}
            accent="teal"
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
            trend={{ value: 3, isPositive: true }}
            accent="gray"
          />
        </div>

        {/* Quick actions */}
        <div className="animate-fade-up-delay-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-700 mb-3">
            {t("dashboard.quickActions")}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              {
                to: "/checkout",
                label: t("dashboard.newSale"),
                desc: t("dashboard.openCheckout"),
                cls: "quick-action-navy",
              },
              {
                to: "/products",
                label: t("dashboard.addStock"),
                desc: t("dashboard.stockInManage"),
                cls: "quick-action-orange",
              },
              {
                to: "/audit",
                label: t("dashboard.reportsLabel"),
                desc: t("dashboard.salesAndInventory"),
                cls: "quick-action-teal",
              },
              {
                to: "/shifts",
                label: t("dashboard.shiftsLabel"),
                desc: currentShift ? t("dashboard.closeCurrentShift") : t("dashboard.openNewShift"),
                cls: "quick-action-gray",
              },
            ].map(({ to, label, desc, cls }) => (
              <Link
                key={to}
                to={to}
                className={`${cls} text-white rounded-lg p-4 transition-all shadow-md hover:shadow-xl hover:scale-105 flex flex-col items-start justify-between min-h-24`}
              >
                <div className="min-w-0 flex-1 w-full">
                  <p className="font-bold text-sm leading-tight">{label}</p>
                  <p className="text-xs opacity-90 truncate mt-1">{desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Main grid: Recent sales + Shift status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-up-delay-3">

          {/* Recent sales — takes 2 of 3 columns */}
          <div className="lg:col-span-2 border rounded-xl overflow-hidden shadow-sm bg-white">
            <div className="px-4 py-3 border-b bg-gradient-to-r from-teal-100/40 to-slate-100/40 flex items-center justify-between">
              <h2 className="font-bold text-sm text-teal-900">{t("dashboard.recentSales")}</h2>
              <Link to="/bills" className="text-xs text-teal-700 hover:underline flex items-center gap-1 font-medium">
                {t("dashboard.viewAll")} <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            {recentSales.length === 0 ? (
              <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                {t("dashboard.noSalesRecordedPrefix")}{" "}
                <Link to="/checkout" className="text-primary hover:underline font-medium">{t("checkout.checkoutTitle")}</Link>{" "}
                {t("dashboard.noSalesRecordedSuffix")}
              </div>
            ) : (
              <div className="divide-y">
                {recentSales.map((sale) => (
                    <div
                      key={sale.id}
                      className="px-4 py-3 hover:bg-teal-50/30 transition-colors border-b-0 last:border-b-0"
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <div className="shrink-0">
                            {sale.status === "completed" ? (
                              <CheckCircle2 className="h-5 w-5 text-teal-600" />
                            ) : (
                              <XCircle className="h-5 w-5 text-red-600" />
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="font-mono text-xs font-bold text-teal-700">{sale.sale_number}</p>
                            <p className="text-xs text-slate-700 mt-0.5">
                              {sale.customer_name || "Walk-in"} • {sale.cashier_name}
                            </p>
                          </div>
                        </div>
                        <Badge
                          variant={sale.status === "completed" ? "default" : "destructive"}
                          className={sale.status === "completed" ? "bg-teal-600" : ""}
                        >
                          {sale.status === "completed" ? "✓" : "✗"} {sale.status}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="text-xs text-slate-700">
                          {sale.payment?.method?.toUpperCase() || "Cash"} • {formatDt(sale.created_at)}
                        </div>
                        <div className="text-right">
                          <p className="font-bold text-teal-700">{paiseToRupees(sale.total_paise)}</p>
                          {sale.discount_paise > 0 && (
                            <p className="text-xs text-orange-600">-{paiseToRupees(sale.discount_paise)}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Shift status widget */}
          <div className="border rounded-xl overflow-hidden shadow-sm flex flex-col bg-gradient-to-br from-teal-50/40 to-slate-50/40">
            <div className="px-4 py-3 border-b bg-gradient-to-r from-teal-100/40 to-slate-100/40 flex items-center justify-between">
              <h2 className="font-semibold text-sm text-teal-900">{t("dashboard.shiftStatus")}</h2>
              <Link to="/shifts" className="text-xs text-primary hover:underline">
                {t("dashboard.manage")}
              </Link>
            </div>
            <div className="flex-1 px-4 py-4">
              {currentShift ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-sm font-bold text-emerald-600">{t("dashboard.shiftOpen")}</span>
                  </div>
                  <div className="space-y-2.5">
                    <div className="text-xs">
                      <p className="text-slate-700">{t("dashboard.shiftHash")} <span className="font-mono font-semibold text-slate-900">#{currentShift.id}</span></p>
                      <p className="text-slate-700 mt-1">{t("dashboard.opened")}{" "}
                        {new Date(currentShift.opened_at).toLocaleTimeString(language === "ur" ? "ur-PK" : "en-PK", {
                          hour: "2-digit", minute: "2-digit",
                        })}
                      </p>
                      <p className="text-slate-700 mt-1">{t("dashboard.float")} <span className="font-bold text-teal-700">{paiseToRupees(currentShift.opening_float_paise)}</span></p>
                    </div>
                    {/* Performance KPI */}
                    <div className="bg-white/70 rounded-lg p-2.5 space-y-1.5 border border-teal-100">
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-slate-700">Sales Today</span>
                        <span className="font-bold text-teal-700">₹{(todaySummary?.total_revenue_paise || 0) / 100}</span>
                      </div>
                      <div className="progress-bar-container">
                        <div className="progress-bar-fill" style={{ width: "65%" }} />
                      </div>
                    </div>
                  </div>
                  <Link to="/shifts">
                    <Button size="sm" className="w-full mt-2 bg-gradient-to-r from-teal-700 to-slate-600 hover:from-teal-800 hover:to-slate-700 text-white">
                      {t("dashboard.closeShift")}
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-gray-300" />
                    <span className="text-sm font-medium text-slate-700">{t("dashboard.noOpenShift")}</span>
                  </div>
                  <p className="text-xs text-slate-600">
                    {t("dashboard.openShiftHint")}
                  </p>
                  <Link to="/shifts">
                    <Button size="sm" className="w-full mt-2 bg-gradient-to-r from-teal-700 to-slate-600 hover:from-teal-800 hover:to-slate-700 text-white">
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
          <div className="border rounded-xl overflow-hidden shadow-sm low-stock-critical">
            <div className="px-4 py-3 border-b bg-gradient-to-r from-red-100/50 to-orange-100/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-600 animate-pulse" />
                <h2 className="font-bold text-sm text-red-800">{t("dashboard.lowStockAlert")}</h2>
                <Badge variant="destructive" className="bg-red-600">{lowStockProducts.length}</Badge>
              </div>
              <Button variant="outline" size="sm" asChild className="border-red-300 hover:bg-red-50">
                <Link to="/products" className="text-red-700 font-medium">{t("dashboard.manageStock")}</Link>
              </Button>
            </div>
            <div className="divide-y">
              {lowStockProducts.slice(0, 6).map((p) => {
                const stockQty = parseInt(p.stock_qty) || 0;
                const minThreshold = parseInt(p.low_stock_threshold) || 1;
                const stockPercent = Math.min((stockQty / minThreshold) * 100, 100);
                const isCritical = stockQty <= Math.floor(minThreshold * 0.25);

                return (
                  <div
                    key={p.id}
                    className={`px-4 py-3 text-sm hover:bg-red-50/40 transition-colors ${isCritical ? 'bg-red-50/20' : 'bg-orange-50/10'}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="min-w-0">
                        <span className="font-mono text-xs text-slate-600 me-2">{p.sku}</span>
                        <span className="font-semibold text-slate-900">{p.name}</span>
                      </div>
                      <Badge className={isCritical ? "bg-red-600" : "bg-orange-500"}>
                        {isCritical ? "CRITICAL" : "LOW"}
                      </Badge>
                    </div>
                    <div className="progress-bar-container mb-1">
                      <div className="progress-bar-fill" style={{ width: `${stockPercent}%` }} />
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-slate-700">
                        {stockQty} {p.unit} / {minThreshold} {t("dashboard.min")}
                      </span>
                      <span className={isCritical ? "text-red-600 font-bold" : "text-orange-600 font-bold"}>
                        {stockPercent.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                );
              })}
              {lowStockProducts.length > 6 && (
                <div className="px-4 py-2 text-xs text-muted-foreground text-center bg-amber-50/30">
                  +{lowStockProducts.length - 6} {t("dashboard.more")}{" "}
                  <Link to="/products" className="text-red-600 hover:underline font-medium">{t("dashboard.viewAllLower")}</Link>
                </div>
              )}
            </div>
          </div>
        )}

      </div>

      {/* Page footer */}
      <footer className="px-6 py-3 border-t text-center text-xs text-slate-600 bg-slate-50">
        {t("dashboard.footerBuiltBy")}{" "}
        <span className="font-semibold text-slate-800">Neuroqaa.ai</span>
      </footer>
    </div>
  );
}