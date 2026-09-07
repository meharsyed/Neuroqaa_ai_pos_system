import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { useRef, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  FileBarChart, Download, Loader2, TrendingUp, TrendingDown,
  Receipt, Wallet, ShoppingBag, Percent, ChevronDown, FileText,
  FileSpreadsheet, ListChecks, LayoutList,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Money } from "@/components/ui/money";
import { DatePicker } from "@/components/ui/date-picker";
import { DateTime } from "@/components/ui/date-display";
import { reportsApi, downloadAuditPdf, downloadAuditCsv } from "@/lib/reports";
import { useAuthStore } from "@/store/authStore";
import { can } from "@/lib/permissions";
import { NotAllowed } from "@/components/RequireRole";
import type { AuditReport } from "@/types/config";

// ── Small dropdown menu (button + popover with options) ─────────────────────

function DropdownMenu({
  label,
  icon: Icon,
  options,
  disabled,
}: {
  label: string;
  icon: React.ElementType;
  options: { label: string; desc: string; icon: React.ElementType; onClick: () => void }[];
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <Button
        onClick={() => setOpen((v) => !v)}
        disabled={disabled}
        variant="outline"
        size="sm"
        className="gap-2"
      >
        <Icon className="h-4 w-4" />
        {label}
        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </Button>
      {open && (
        <div className="absolute end-0 mt-1.5 w-64 rounded-xl border bg-popover shadow-lg z-20 overflow-hidden animate-fade-in-scale">
          {options.map((opt) => (
            <button
              key={opt.label}
              onClick={() => { opt.onClick(); setOpen(false); }}
              className="w-full flex items-start gap-2.5 px-3.5 py-3 text-start hover:bg-muted/60 transition-colors border-b last:border-b-0"
            >
              <opt.icon className="h-4 w-4 mt-0.5 shrink-0 text-primary" />
              <div>
                <p className="text-sm font-medium">{opt.label}</p>
                <p className="text-xs text-muted-foreground">{opt.desc}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

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
  // Named by meaning rather than by colour, so a card cannot end up green in
  // light mode and unreadable in dark. The old map also referenced
  // `danger-500` and `danger-50`, which this project's Tailwind config does
  // not define at all — those cards had no accent at all and nobody noticed.
  accent?: "info" | "success" | "destructive" | "warning";
}) {
  const border = {
    info:        "border-l-info bg-info-bg/40",
    success:     "border-l-success bg-success-bg/40",
    destructive: "border-l-destructive bg-destructive-bg/40",
    warning:     "border-l-warning bg-warning-bg/40",
  };
  const icon_color = {
    info:        "text-info",
    success:     "text-success",
    destructive: "text-destructive",
    warning:     "text-warning",
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
  const [detailed, setDetailed] = useState(false);
  const [downloadingCsv, setDownloadingCsv] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // The access check is a value, not an early return. Returning before the
  // useQuery below meant this component ran a different number of hooks
  // depending on who was signed in — React's cardinal rule — and would have
  // crashed with "rendered more hooks than during the previous render" the
  // moment a role changed while the page was mounted. The guarded view is
  // returned from the JSX instead, after every hook has run.
  const allowed = can.viewReports(user);

  const { data, isLoading, isError } = useQuery<AuditReport>({
    queryKey: ["audit", queryRange, detailed],
    queryFn: () => reportsApi.audit(queryRange!.start, queryRange!.end, detailed),
    enabled: allowed && queryRange !== null,
    staleTime: 60_000,
  });

  function generateReport(isDetailed: boolean) {
    setDetailed(isDetailed);
    setQueryRange({ start: startDate, end: endDate });
  }

  async function handleDownloadPdf() {
    if (!queryRange) return;
    setDownloadingPdf(true);
    try {
      await downloadAuditPdf(queryRange.start, queryRange.end, detailed);
    } finally {
      setDownloadingPdf(false);
    }
  }

  async function handleDownloadCsv() {
    if (!queryRange) return;
    setDownloadingCsv(true);
    try {
      await downloadAuditCsv(queryRange.start, queryRange.end, detailed);
    } finally {
      setDownloadingCsv(false);
    }
  }

  const marginPositive = (data?.gross_margin_pct ?? 0) >= 0;

  if (!allowed) {
    return (
      <PageContainer>
        <NotAllowed what="Audit reports" />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Audit Reports"
        subtitle="Profit & Loss analysis with COGS breakdown — Owner/Manager only"
        actions={
          data && (
            <DropdownMenu
              label={downloadingCsv || downloadingPdf ? "Preparing…" : "Download"}
              icon={downloadingCsv || downloadingPdf ? Loader2 : Download}
              disabled={downloadingCsv || downloadingPdf}
              options={[
                {
                  label: "CSV",
                  desc: "Spreadsheet-friendly — open in Excel or Google Sheets",
                  icon: FileSpreadsheet,
                  onClick: handleDownloadCsv,
                },
                {
                  label: "PDF",
                  desc: "Formatted report — ready to print or share",
                  icon: FileText,
                  onClick: handleDownloadPdf,
                },
              ]}
            />
          )
        }
      />

      <div className="space-y-6">

        {/* Date range selector */}
        <div className="flex flex-wrap items-end gap-3 rounded-xl border bg-muted/20 px-5 py-4">
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide block mb-1.5">
              From
            </label>
            <DatePicker
              value={startDate}
              onChange={setStartDate}
              className="w-40"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide block mb-1.5">
              To
            </label>
            <DatePicker
              value={endDate}
              onChange={setEndDate}
              className="w-40"
            />
          </div>
          <DropdownMenu
            label={isLoading ? "Generating…" : "Generate Report"}
            icon={isLoading ? Loader2 : FileBarChart}
            disabled={!startDate || !endDate || startDate > endDate || isLoading}
            options={[
              {
                label: "Short Report",
                desc: "Summary totals, payment methods, top products, daily breakdown",
                icon: LayoutList,
                onClick: () => generateReport(false),
              },
              {
                label: "Detailed Report",
                desc: "Everything in Short, plus every individual bill for each day, itemized",
                icon: ListChecks,
                onClick: () => generateReport(true),
              },
            ]}
          />

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
                Generated <DateTime value={data.generated_at} />
              </span>
            </div>

            {/* Summary metric cards */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <MetricCard
                icon={Receipt}
                label="Transactions"
                value={data.transaction_count.toLocaleString()}
                sub="Completed sales"
                accent="info"
              />
              <MetricCard
                icon={Wallet}
                label="Revenue"
                value={<Money paise={data.total_revenue_paise} />}
                sub={<>Discounts: <Money paise={data.total_discount_paise} /></>}
                accent="info"
              />
              <MetricCard
                icon={ShoppingBag}
                label="COGS"
                value={<Money paise={data.total_cogs_paise} />}
                sub={`${pct(data.total_cogs_paise, data.total_revenue_paise)} of revenue`}
                accent="warning"
              />
              <MetricCard
                icon={marginPositive ? TrendingUp : TrendingDown}
                label="Gross Profit"
                value={<Money paise={data.gross_profit_paise} />}
                sub={`After COGS deduction`}
                accent={marginPositive ? "success" : "destructive"}
              />
              <MetricCard
                icon={Percent}
                label="Gross Margin"
                value={`${data.gross_margin_pct}%`}
                sub="Profit / Revenue"
                accent={
                  data.gross_margin_pct >= 30
                    ? "success"
                    : data.gross_margin_pct >= 10
                      ? "warning"
                      : "destructive"
                }
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
                    { label: "Gross Sales (before discounts)", value: <Money paise={data.total_subtotal_paise} />, sub: false },
                    { label: "Discounts Given", value: <>− <Money paise={data.total_discount_paise} /></>, sub: true, cls: "text-warning" },
                    { label: "Tax Collected", value: <>+ <Money paise={data.total_tax_paise} /></>, sub: true, cls: "text-info" },
                    { label: "Net Revenue", value: <Money paise={data.total_revenue_paise} />, bold: true },
                    { label: "Cost of Goods Sold", value: <>− <Money paise={data.total_cogs_paise} /></>, sub: true, cls: "text-muted-foreground" },
                    { label: "Gross Profit", value: <Money paise={data.gross_profit_paise} />, bold: true, cls: marginPositive ? "text-teal-600" : "text-destructive" },
                    { label: "Gross Margin %", value: `${data.gross_margin_pct}%`, bold: true, cls: marginPositive ? "text-teal-600" : "text-destructive" },
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
                          {/* Bills, not transactions: a split bill appears under
                              each tender it used, so these counts can overlap.
                              The money is what adds up to revenue. */}
                          <span className="text-xs text-muted-foreground ml-2">{v.count} bill{v.count !== 1 ? "s" : ""}</span>
                        </div>
                        <div className="text-right">
                          <p className="font-mono font-semibold"><Money paise={v.total_paise} /></p>
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
                            <td className="px-4 py-2.5 text-right font-mono"><Money paise={p.revenue_paise} /></td>
                            <td className="px-4 py-2.5 text-right font-mono text-muted-foreground"><Money paise={p.cogs_paise} /></td>
                            <td className={`px-4 py-2.5 text-right font-mono font-semibold ${pos ? "text-teal-600" : "text-destructive"}`}>
                              <Money paise={p.gross_profit_paise} />
                            </td>
                            <td className="px-4 py-2.5 text-right">
                              <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${pos ? "bg-teal-100 text-teal-700" : "bg-destructive-bg text-destructive"}`}>
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
                        <td className="px-4 py-2.5 text-right font-mono text-xs text-warning">
                          {row.discount_paise > 0 ? <>− <Money paise={row.discount_paise} /></> : "—"}
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono font-semibold">
                          <Money paise={row.revenue_paise} />
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

            {/* Detailed transactions — only present when Detailed Report was generated */}
            {detailed && data.daily_breakdown.some((row) => row.bills && row.bills.length > 0) && (
              <div className="space-y-4">
                <h3 className="font-semibold text-sm px-1">Detailed Transactions</h3>
                {data.daily_breakdown
                  .filter((row) => row.bills && row.bills.length > 0)
                  .map((row) => (
                    <div key={row.date} className="rounded-xl border overflow-hidden shadow-sm">
                      <div className="px-4 py-2.5 bg-primary text-primary-foreground flex items-center justify-between">
                        <span className="font-semibold text-sm">{row.date}</span>
                        <span className="text-xs opacity-80">
                          {row.bills!.length} bill{row.bills!.length !== 1 ? "s" : ""}
                        </span>
                      </div>
                      <div className="divide-y">
                        {row.bills!.map((bill) => (
                          <div key={bill.sale_number} className="p-4 space-y-2">
                            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                              <span className="font-mono font-semibold text-foreground">{bill.sale_number}</span>
                              <span>{bill.time.slice(11, 16)}</span>
                              <span>{bill.cashier}</span>
                              {bill.customer && <span className="text-primary">{bill.customer}</span>}
                            </div>
                            <div className="rounded-lg border overflow-hidden">
                              <table className="w-full text-xs">
                                <thead className="bg-muted/40">
                                  <tr>
                                    <th className="px-3 py-1.5 text-start font-medium text-muted-foreground">Item</th>
                                    <th className="px-3 py-1.5 text-end font-medium text-muted-foreground">Qty</th>
                                    <th className="px-3 py-1.5 text-end font-medium text-muted-foreground">Rate</th>
                                    <th className="px-3 py-1.5 text-end font-medium text-muted-foreground">Amount</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y">
                                  {bill.items.map((item, i) => (
                                    <tr key={i}>
                                      <td className="px-3 py-1.5">
                                        {item.name}{" "}
                                        <span className="text-muted-foreground font-mono text-[10px]">({item.sku})</span>
                                      </td>
                                      <td className="px-3 py-1.5 text-end font-mono">{item.qty}</td>
                                      <td className="px-3 py-1.5 text-end font-mono"><Money paise={item.unit_price_paise} /></td>
                                      <td className="px-3 py-1.5 text-end font-mono font-medium"><Money paise={item.subtotal_paise} /></td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                            <div className="flex items-center justify-end gap-3 text-xs">
                              {bill.discount_paise > 0 && (
                                <span className="text-warning">− <Money paise={bill.discount_paise} /> discount</span>
                              )}
                              {bill.payment_method && (
                                <span className="text-muted-foreground uppercase">{bill.payment_method}</span>
                              )}
                              <span className="font-bold text-sm">Total: <Money paise={bill.total_paise} /></span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
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
    </PageContainer>
  );
}
