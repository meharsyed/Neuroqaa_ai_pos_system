import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  FileBarChart, Download, Loader2, TrendingUp, TrendingDown,
  Receipt, Wallet, ShoppingBag, Percent,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { paiseToRupees } from "@/lib/catalog";
import { reportsApi, downloadAuditPdf } from "@/lib/reports";
import { useAuthStore } from "@/store/authStore";
import type { AuditReport } from "@/types/config";

// ── helpers ───────────────────────────────────────────────────────────────────

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}
function monthStartIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
}

function pct(value: number, total: number) {
  if (!total) return "0%";
  return `${((value / total) * 100).toFixed(1)}%`;
}

// ── Metric card ───────────────────────────────────────────────────────────────

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
  accent,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  accent?: "blue" | "green" | "red" | "amber" | "purple";
}) {
  const border = {
    blue:   "border-l-blue-500 bg-blue-50/40",
    green:  "border-l-emerald-500 bg-emerald-50/40",
    red:    "border-l-red-500 bg-red-50/40",
    amber:  "border-l-amber-500 bg-amber-50/40",
    purple: "border-l-purple-500 bg-purple-50/40",
  };
  const icon_color = {
    blue:   "text-blue-500",
    green:  "text-emerald-500",
    red:    "text-red-500",
    amber:  "text-amber-500",
    purple: "text-purple-500",
  };
  return (
    <div className={`border rounded-xl p-4 border-l-4 shadow-sm ${accent ? border[accent] : "border-l-border"}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</span>
        <Icon className={`h-4 w-4 ${accent ? icon_color[accent] : "text-muted-foreground"}`} />
      </div>
      <p className="text-2xl font-bold tabular-nums leading-none">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function AuditPage() {
  const user = useAuthStore((s) => s.user);
  const [startDate, setStartDate] = useState(monthStartIso());
  const [endDate, setEndDate]     = useState(todayIso());
  const [queryRange, setQueryRange] = useState<{ start: string; end: string } | null>(null);
  const [downloading, setDownloading] = useState(false);

  // Access guard
  if (user?.role !== "owner" && user?.role !== "manager") {
    return (
      <div className="min-h-full flex items-center justify-center p-8">
        <div className="text-center">
          <FileBarChart className="h-12 w-12 mx-auto mb-3 opacity-20" />
          <p className="font-semibold text-muted-foreground">Access restricted</p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            Only owners and managers can view audit reports.
          </p>
        </div>
      </div>
    );
  }

  const { data, isLoading, isError } = useQuery<AuditReport>({
    queryKey: ["audit", queryRange],
    queryFn: () => reportsApi.audit(queryRange!.start, queryRange!.end),
    enabled: queryRange !== null,
    staleTime: 60_000,
  });

  async function handleDownload() {
    if (!queryRange) return;
    setDownloading(true);
    try {
      await downloadAuditPdf(queryRange.start, queryRange.end);
    } finally {
      setDownloading(false);
    }
  }

  const marginPositive = (data?.gross_margin_pct ?? 0) >= 0;

  return (
    <div className="min-h-full flex flex-col">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <FileBarChart className="h-5 w-5 text-primary" />
            <div>
              <h1 className="text-xl font-bold">Audit / Closing Report</h1>
              <p className="text-sm text-muted-foreground">
                Profit &amp; Loss analysis with COGS breakdown — Owner/Manager only
              </p>
            </div>
          </div>
          {data && (
            <Button
              onClick={handleDownload}
              disabled={downloading}
              variant="outline"
              size="sm"
              className="gap-2"
            >
              {downloading ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Generating…</>
              ) : (
                <><Download className="h-4 w-4" /> Download PDF</>
              )}
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 p-6 space-y-6">

        {/* Date range selector */}
        <div className="flex flex-wrap items-end gap-3 rounded-xl border bg-muted/20 px-5 py-4">
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide block mb-1.5">
              From
            </label>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-40"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide block mb-1.5">
              To
            </label>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-40"
            />
          </div>
          <Button
            onClick={() => setQueryRange({ start: startDate, end: endDate })}
            disabled={!startDate || !endDate || startDate > endDate || isLoading}
            className="gap-2"
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileBarChart className="h-4 w-4" />}
            Generate Report
          </Button>

          {/* Quick presets */}
          <div className="flex gap-1.5 ml-2">
            {[
              { label: "Today",      start: todayIso(),       end: todayIso() },
              { label: "This month", start: monthStartIso(),  end: todayIso() },
              {
                label: "Last 7 days",
                start: (() => { const d = new Date(); d.setDate(d.getDate() - 6); return d.toISOString().slice(0, 10); })(),
                end: todayIso(),
              },
            ].map((p) => (
              <button
                key={p.label}
                onClick={() => { setStartDate(p.start); setEndDate(p.end); setQueryRange({ start: p.start, end: p.end }); }}
                className="text-xs px-2.5 py-1.5 rounded-lg border border-border text-muted-foreground hover:border-primary/40 hover:text-foreground transition-colors"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="flex items-center justify-center py-16 text-sm text-muted-foreground gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            Calculating audit report…
          </div>
        )}

        {/* Error state */}
        {isError && (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-6 text-center text-sm text-destructive">
            Failed to generate report. Please try again.
          </div>
        )}

        {/* Report data */}
        {data && !isLoading && (
          <>
            {/* Period label */}
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Report period: <span className="font-semibold text-foreground">{data.period_start}</span>
                {" → "}
                <span className="font-semibold text-foreground">{data.period_end}</span>
              </span>
              <span className="text-xs text-muted-foreground">
                Generated {new Date(data.generated_at).toLocaleString("en-PK")}
              </span>
            </div>

            {/* Summary metric cards */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <MetricCard
                icon={Receipt}
                label="Transactions"
                value={data.transaction_count.toLocaleString()}
                sub="Completed sales"
                accent="blue"
              />
              <MetricCard
                icon={Wallet}
                label="Revenue"
                value={paiseToRupees(data.total_revenue_paise)}
                sub={`Discounts: ${paiseToRupees(data.total_discount_paise)}`}
                accent="blue"
              />
              <MetricCard
                icon={ShoppingBag}
                label="COGS"
                value={paiseToRupees(data.total_cogs_paise)}
                sub={`${pct(data.total_cogs_paise, data.total_revenue_paise)} of revenue`}
                accent="amber"
              />
              <MetricCard
                icon={marginPositive ? TrendingUp : TrendingDown}
                label="Gross Profit"
                value={paiseToRupees(data.gross_profit_paise)}
                sub={`After COGS deduction`}
                accent={marginPositive ? "green" : "red"}
              />
              <MetricCard
                icon={Percent}
                label="Gross Margin"
                value={`${data.gross_margin_pct}%`}
                sub="Profit / Revenue"
                accent={data.gross_margin_pct >= 30 ? "green" : data.gross_margin_pct >= 10 ? "amber" : "red"}
              />
            </div>

            {/* Revenue breakdown + payment methods side by side */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

              {/* Revenue breakdown */}
              <div className="rounded-xl border overflow-hidden shadow-sm">
                <div className="px-4 py-3 border-b bg-muted/30">
                  <h3 className="font-semibold text-sm">Revenue &amp; Profit Breakdown</h3>
                </div>
                <div className="divide-y text-sm">
                  {[
                    { label: "Gross Sales (before discounts)", value: paiseToRupees(data.total_subtotal_paise), sub: false },
                    { label: "Discounts Given", value: `− ${paiseToRupees(data.total_discount_paise)}`, sub: true, cls: "text-amber-600" },
                    { label: "Tax Collected", value: `+ ${paiseToRupees(data.total_tax_paise)}`, sub: true, cls: "text-blue-600" },
                    { label: "Net Revenue", value: paiseToRupees(data.total_revenue_paise), bold: true },
                    { label: "Cost of Goods Sold", value: `− ${paiseToRupees(data.total_cogs_paise)}`, sub: true, cls: "text-muted-foreground" },
                    { label: "Gross Profit", value: paiseToRupees(data.gross_profit_paise), bold: true, cls: marginPositive ? "text-emerald-600" : "text-red-600" },
                    { label: "Gross Margin %", value: `${data.gross_margin_pct}%`, bold: true, cls: marginPositive ? "text-emerald-600" : "text-red-600" },
                  ].map(({ label, value, sub, bold, cls }) => (
                    <div key={label} className={`flex justify-between px-4 py-2.5 ${sub ? "bg-muted/10" : ""}`}>
                      <span className={`${bold ? "font-bold" : "text-muted-foreground"} ${cls ?? ""}`}>{label}</span>
                      <span className={`font-mono tabular-nums ${bold ? "font-bold" : ""} ${cls ?? ""}`}>{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Payment methods */}
              <div className="rounded-xl border overflow-hidden shadow-sm">
                <div className="px-4 py-3 border-b bg-muted/30">
                  <h3 className="font-semibold text-sm">Payment Methods</h3>
                </div>
                {Object.keys(data.payment_breakdown).length === 0 ? (
                  <p className="px-4 py-8 text-center text-sm text-muted-foreground">No sales in this period.</p>
                ) : (
                  <div className="divide-y text-sm">
                    {Object.entries(data.payment_breakdown).map(([method, v]) => (
                      <div key={method} className="flex items-center justify-between px-4 py-3">
                        <div>
                          <span className="font-medium uppercase text-xs bg-muted px-2 py-0.5 rounded font-mono">
                            {method}
                          </span>
                          <span className="text-xs text-muted-foreground ml-2">{v.count} transaction{v.count !== 1 ? "s" : ""}</span>
                        </div>
                        <div className="text-right">
                          <p className="font-mono font-semibold">{paiseToRupees(v.total_paise)}</p>
                          <p className="text-xs text-muted-foreground">
                            {pct(v.total_paise, data.total_revenue_paise)} of revenue
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Top products */}
            {data.top_products.length > 0 && (
              <div className="rounded-xl border overflow-hidden shadow-sm">
                <div className="px-4 py-3 border-b bg-muted/30 flex items-center justify-between">
                  <h3 className="font-semibold text-sm">Top Products by Revenue</h3>
                  <span className="text-xs text-muted-foreground">with per-product profit margin</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/40 border-b">
                      <tr>
                        {["Product", "Qty Sold", "Revenue", "COGS", "Gross Profit", "Margin"].map((h, i) => (
                          <th key={h} className={`px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground ${i > 0 ? "text-right" : "text-left"}`}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {data.top_products.map((p) => {
                        const pos = p.gross_profit_paise >= 0;
                        return (
                          <tr key={p.sku} className="hover:bg-muted/20 transition-colors">
                            <td className="px-4 py-2.5">
                              <p className="font-medium">{p.name}</p>
                              <p className="text-[10px] text-muted-foreground font-mono">{p.sku}</p>
                            </td>
                            <td className="px-4 py-2.5 text-right font-mono text-xs">{p.qty_sold}</td>
                            <td className="px-4 py-2.5 text-right font-mono">{paiseToRupees(p.revenue_paise)}</td>
                            <td className="px-4 py-2.5 text-right font-mono text-muted-foreground">{paiseToRupees(p.cogs_paise)}</td>
                            <td className={`px-4 py-2.5 text-right font-mono font-semibold ${pos ? "text-emerald-600" : "text-red-600"}`}>
                              {paiseToRupees(p.gross_profit_paise)}
                            </td>
                            <td className="px-4 py-2.5 text-right">
                              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${pos ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
                                {p.gross_margin_pct}%
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Daily breakdown */}
            {data.daily_breakdown.length > 0 && (
              <div className="rounded-xl border overflow-hidden shadow-sm">
                <div className="px-4 py-3 border-b bg-muted/30">
                  <h3 className="font-semibold text-sm">Daily Breakdown</h3>
                </div>
                <table className="w-full text-sm">
                  <thead className="bg-muted/40 border-b">
                    <tr>
                      {["Date", "Transactions", "Discounts", "Revenue", "% of Period"].map((h, i) => (
                        <th key={h} className={`px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground ${i > 0 ? "text-right" : "text-left"}`}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.daily_breakdown.map((row) => (
                      <tr key={row.date} className="hover:bg-muted/20 transition-colors">
                        <td className="px-4 py-2.5 font-mono text-xs font-medium">{row.date}</td>
                        <td className="px-4 py-2.5 text-right">{row.count}</td>
                        <td className="px-4 py-2.5 text-right font-mono text-xs text-amber-600">
                          {row.discount_paise > 0 ? `− ${paiseToRupees(row.discount_paise)}` : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono font-semibold">
                          {paiseToRupees(row.revenue_paise)}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-20 bg-muted rounded-full h-1.5 overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full"
                                style={{ width: `${Math.min(100, (row.revenue_paise / (data.total_revenue_paise || 1)) * 100)}%` }}
                              />
                            </div>
                            <span className="text-xs text-muted-foreground w-10 text-right">
                              {pct(row.revenue_paise, data.total_revenue_paise)}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* COGS note */}
            <p className="text-xs text-muted-foreground/60 text-center pb-2">
              COGS is calculated using current product cost prices (approximate).
              Profit margins improve as selling prices increase relative to purchase costs.
            </p>
          </>
        )}

        {/* Empty state — nothing generated yet */}
        {!queryRange && !data && !isLoading && (
          <div className="rounded-xl border p-16 text-center">
            <FileBarChart className="h-10 w-10 mx-auto mb-3 opacity-15" />
            <p className="text-sm font-medium text-muted-foreground">Select a date range and click Generate Report</p>
            <p className="text-xs text-muted-foreground/60 mt-1">
              Default range is set to the current calendar month
            </p>
          </div>
        )}

      </div>
    </div>
  );
}
