import { Link } from "react-router-dom";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Package, AlertTriangle, TrendingUp, Receipt,
  ArrowRight, CheckCircle2, XCircle, Plus,
} from "lucide-react";
import { catalogApi, paiseToRupees } from "@/lib/catalog";
import { salesApi } from "@/lib/sales";
import { reportsApi } from "@/lib/reports";
import { shiftsApi } from "@/lib/shifts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Money } from "@/components/ui/money";
import { DateTime } from "@/components/ui/date-display";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useTranslation } from "@/lib/useTranslation";
import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { StockInModal } from "@/components/catalog/StockInModal";
import type { Product } from "@/types/catalog";

function today() {
  return new Date().toISOString().slice(0, 10);
}

function getLast7Days() {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 6);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
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
      bg: "bg-gradient-to-br from-teal-50 to-teal-100",
      icon: "text-teal-600",
      gradient: "from-teal-600 to-teal-500",
    },
    orange: {
      border: "border-warning",
      bg: "bg-gradient-to-br from-warning-bg to-orange-50",
      icon: "text-warning",
      gradient: "from-warning to-orange-500",
    },
    teal: {
      border: "border-teal-500",
      bg: "bg-gradient-to-br from-teal-50 to-teal-100",
      icon: "text-teal-500",
      gradient: "from-teal-500 to-teal-400",
    },
    gray: {
      border: "border-n-400",
      bg: "bg-gradient-to-br from-n-50 to-n-100",
      icon: "text-n-500",
      gradient: "from-n-600 to-n-500",
    },
    red: {
      border: "border-destructive",
      bg: "bg-gradient-to-br from-destructive-bg to-danger-bg",
      icon: "text-destructive",
      gradient: "from-destructive to-danger",
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
          <div className={`text-sm font-bold flex items-center gap-1 ${trend.isPositive ? "text-success" : "text-warning"}`}>
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
  const todayStr = today();
  const { t } = useTranslation();
  const [stockInProduct, setStockInProduct] = useState<Product | null>(null);

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

  const dateRange = getLast7Days();
  const { data: sevenDayReport } = useQuery({
    queryKey: ["report-audit", dateRange.start, dateRange.end],
    queryFn: () => reportsApi.audit(dateRange.start, dateRange.end),
    staleTime: 60_000,
  });

  const { data: recentSalesData, isLoading: recentSalesLoading } = useQuery({
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

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        subtitle={`${totalProducts} products · ${lowStockProducts.length} low stock`}
      />

      <div className="space-y-6">

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-up-delay-1">
          <StatCard
            icon={Package}
            label={t("dashboard.statTotalProducts")}
            value={totalProducts.toLocaleString()}
            sub={<Link to="/products" className="hover:underline text-primary">{t("dashboard.viewCatalogue")}</Link>}
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
            accent="gray"
          />
        </div>

        {/* Quick actions */}
        <div className="animate-fade-up-delay-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
            {t("dashboard.quickActions")}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              {
                to: "/checkout",
                label: t("dashboard.newSale"),
                desc: t("dashboard.openCheckout"),
                bg: "bg-teal-600",
              },
              {
                to: "/products",
                label: t("dashboard.addStock"),
                desc: t("dashboard.stockInManage"),
                bg: "bg-warning",
              },
              {
                to: "/audit",
                label: t("dashboard.reportsLabel"),
                desc: t("dashboard.salesAndInventory"),
                bg: "bg-teal-500",
              },
              {
                to: "/shifts",
                label: t("dashboard.shiftsLabel"),
                desc: currentShift ? t("dashboard.closeCurrentShift") : t("dashboard.openNewShift"),
                bg: "bg-n-600",
              },
            ].map(({ to, label, desc, bg }) => (
              <Link
                key={to}
                to={to}
                className={`${bg} text-white rounded-lg p-4 transition-all shadow-md hover:shadow-xl hover:scale-105 flex flex-col items-start justify-between min-h-24`}
              >
                <div className="min-w-0 flex-1 w-full">
                  <p className="font-bold text-sm leading-tight">{label}</p>
                  <p className="text-xs opacity-90 truncate mt-1">{desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* 7-day revenue chart */}
        {sevenDayReport && (
          <div className="border rounded-xl overflow-hidden shadow-sm bg-white p-4 animate-fade-up-delay-2">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-bold text-sm text-foreground">7-Day Revenue Trend</h2>
                <p className="text-xs text-muted-foreground mt-1">{dateRange.start} to {dateRange.end}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-teal-700">
                  <Money paise={sevenDayReport.total_revenue_paise} />
                </div>
                <p className="text-xs text-muted-foreground">{sevenDayReport.transaction_count} transactions</p>
              </div>
            </div>

            {/* Sparkline bars */}
            <div className="flex items-end justify-between gap-1.5 h-16 bg-muted/20 p-3 rounded-lg">
              {sevenDayReport.daily_breakdown && sevenDayReport.daily_breakdown.length > 0 ? (
                sevenDayReport.daily_breakdown.map((day) => {
                  const maxRevenue = Math.max(...sevenDayReport.daily_breakdown.map((d) => d.revenue_paise), 1);
                  const height = (day.revenue_paise / maxRevenue) * 100;
                  return (
                    <div
                      key={day.date}
                      className="flex-1 bg-teal-400/60 hover:bg-teal-500 rounded-sm transition-colors cursor-pointer"
                      style={{ height: `${Math.max(height, 5)}%` }}
                      title={`${day.date}: Rs ${(day.revenue_paise / 100).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                    />
                  );
                })
              ) : (
                Array(7).fill(0).map((_, i) => (
                  <div key={i} className="flex-1 bg-muted rounded-sm" />
                ))
              )}
            </div>
          </div>
        )}

        {/* Main grid: Recent sales + Shift status */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-up-delay-3">

          {/* Recent sales — takes 2 of 3 columns */}
          <div className="lg:col-span-2 border rounded-xl overflow-hidden shadow-sm bg-white">
            <div className="px-4 py-3 border-b bg-gradient-to-r from-teal-100/40 to-n-100/40 flex items-center justify-between">
              <h2 className="font-bold text-sm text-teal-900">{t("dashboard.recentSales")}</h2>
              <Link to="/bills" className="text-xs text-teal-700 hover:underline flex items-center gap-1 font-medium">
                {t("dashboard.viewAll")} <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            {recentSalesLoading ? (
              <div className="divide-y">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="px-4 py-3 space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-3 w-48" />
                  </div>
                ))}
              </div>
            ) : recentSales.length === 0 ? (
              <EmptyState
                icon={Receipt}
                title={t("dashboard.noSalesRecorded")}
                description={t("dashboard.noSalesRecordedPrefix")}
                action={<Link to="/checkout" className="text-primary hover:underline font-medium">{t("checkout.checkoutTitle")}</Link>}
              />
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
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {sale.customer_name || "Walk-in"} • {sale.cashier_name}
                            </p>
                          </div>
                        </div>
                        <Badge
                          variant={sale.status === "completed" ? "success" : "danger"}
                        >
                          {sale.status === "completed" ? "✓" : "✗"} {sale.status}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="text-xs text-muted-foreground">
                          {sale.payment?.method?.toUpperCase() || "Cash"} • <DateTime value={new Date(sale.created_at)} format="short" />
                        </div>
                        <div className="text-right">
                          <Money paise={sale.total_paise} className="font-bold text-teal-700 text-sm" />
                          {sale.discount_paise > 0 && (
                            <div className="text-xs text-orange-600">-<Money paise={sale.discount_paise} /></div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Shift status widget */}
          <div className="border rounded-xl overflow-hidden shadow-sm flex flex-col bg-gradient-to-br from-teal-50/40 to-n-50/40">
            <div className="px-4 py-3 border-b bg-gradient-to-r from-teal-100/40 to-n-100/40 flex items-center justify-between">
              <h2 className="font-semibold text-sm text-teal-900">{t("dashboard.shiftStatus")}</h2>
              <Link to="/shifts" className="text-xs text-primary hover:underline">
                {t("dashboard.manage")}
              </Link>
            </div>
            <div className="flex-1 px-4 py-4">
              {currentShift ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-teal-500 animate-pulse" />
                    <span className="text-sm font-bold text-teal-600">{t("dashboard.shiftOpen")}</span>
                  </div>
                  <div className="space-y-2.5">
                    <div className="text-xs">
                      <p className="text-muted-foreground">{t("dashboard.shiftHash")} <span className="font-mono font-semibold text-foreground">#{currentShift.id}</span></p>
                      <p className="text-muted-foreground mt-1">
                        {t("dashboard.opened")} <DateTime value={new Date(currentShift.opened_at)} format="short" />
                      </p>
                      <p className="text-muted-foreground mt-1">{t("dashboard.float")} <span className="font-bold text-teal-700">{paiseToRupees(currentShift.opening_float_paise)}</span></p>
                    </div>
                    {/* Performance KPI */}
                    <div className="bg-white/70 rounded-lg p-2.5 space-y-1.5 border border-teal-100">
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-muted-foreground">Sales Today</span>
                        <span className="font-bold text-teal-700">₹{(todaySummary?.total_revenue_paise || 0) / 100}</span>
                      </div>
                      <div className="progress-bar-container">
                        <div className="progress-bar-fill" style={{ width: "65%" }} />
                      </div>
                    </div>
                  </div>
                  <Link to="/shifts">
                    <Button size="sm" className="w-full mt-2 bg-gradient-to-r from-teal-600 to-green-600 hover:from-teal-700 hover:to-green-700 text-white">
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
                    <Button size="sm" className="w-full mt-2 bg-gradient-to-r from-teal-600 to-green-600 hover:from-teal-700 hover:to-green-700 text-white">
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
                <Badge variant="danger">{lowStockProducts.length}</Badge>
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
                      <div className="min-w-0 flex-1">
                        <span className="font-mono text-xs text-muted-foreground me-2">{p.sku}</span>
                        <span className="font-semibold text-foreground">{p.name}</span>
                      </div>
                      <div className="flex items-center gap-2 ms-2 shrink-0">
                        <Badge variant={isCritical ? "danger" : "warning"}>
                          {isCritical ? "CRITICAL" : "LOW"}
                        </Badge>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setStockInProduct(p)}
                          className="h-7 gap-1 text-xs"
                        >
                          <Plus className="h-3 w-3" />
                          Stock
                        </Button>
                      </div>
                    </div>
                    <div className="progress-bar-container mb-1">
                      <div className="progress-bar-fill" style={{ width: `${stockPercent}%` }} />
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">
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

      <StockInModal
        open={!!stockInProduct}
        onOpenChange={(open) => !open && setStockInProduct(null)}
        product={stockInProduct}
      />
    </PageContainer>
  );
}