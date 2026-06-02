import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { paiseToRupees } from "@/lib/catalog";
import { reportsApi, downloadCsv } from "@/lib/reports";

type Tab = "daily" | "range" | "inventory";

function today() {
  return new Date().toISOString().slice(0, 10);
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-4 space-y-1">
      <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
      <p className="text-xl font-bold tabular-nums">{value}</p>
    </div>
  );
}

export default function ReportsPage() {
  const [tab, setTab] = useState<Tab>("daily");
  const [date, setDate] = useState(today());
  const [rangeStart, setRangeStart] = useState(today());
  const [rangeEnd, setRangeEnd] = useState(today());

  const dailyQ = useQuery({
    queryKey: ["report-daily", date],
    queryFn: () => reportsApi.daily(date),
    enabled: tab === "daily",
  });

  const rangeQ = useQuery({
    queryKey: ["report-range", rangeStart, rangeEnd],
    queryFn: () => reportsApi.dateRange(rangeStart, rangeEnd),
    enabled: tab === "range",
  });

  const invQ = useQuery({
    queryKey: ["report-inventory"],
    queryFn: reportsApi.inventory,
    enabled: tab === "inventory",
    staleTime: 60_000,
  });

  const tabs: { key: Tab; label: string }[] = [
    { key: "daily", label: "Daily" },
    { key: "range", label: "Date Range" },
    { key: "inventory", label: "Inventory Value" },
  ];

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3">
        <BarChart3 className="h-5 w-5" />
        <h1 className="text-xl font-semibold">Reports</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Daily */}
      {tab === "daily" && (
        <div className="space-y-6">
          <div className="flex items-end gap-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">
                Date
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="border rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                downloadCsv(
                  `/reports/daily/?date=${date}&export=csv`,
                  `daily-${date}.csv`
                )
              }
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />
              Export CSV
            </Button>
          </div>

          {dailyQ.isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}
          {dailyQ.data && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <SummaryCard
                  label="Transactions"
                  value={String(dailyQ.data.transaction_count)}
                />
                <SummaryCard
                  label="Total Revenue"
                  value={paiseToRupees(dailyQ.data.total_revenue_paise)}
                />
                <SummaryCard
                  label="Discounts Given"
                  value={paiseToRupees(dailyQ.data.total_discount_paise)}
                />
                <SummaryCard
                  label="Net Revenue"
                  value={paiseToRupees(
                    dailyQ.data.total_revenue_paise - dailyQ.data.total_discount_paise
                  )}
                />
              </div>

              {Object.keys(dailyQ.data.payment_breakdown).length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold">Payment Methods</h3>
                  <div className="rounded-lg border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-2 text-left font-medium">Method</th>
                          <th className="px-4 py-2 text-right font-medium">Transactions</th>
                          <th className="px-4 py-2 text-right font-medium">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {Object.entries(dailyQ.data.payment_breakdown).map(([method, v]) => (
                          <tr key={method}>
                            <td className="px-4 py-2 capitalize">{method}</td>
                            <td className="px-4 py-2 text-right tabular-nums">{v.count}</td>
                            <td className="px-4 py-2 text-right tabular-nums font-mono">
                              {paiseToRupees(v.total_paise)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {dailyQ.data.top_products.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold">Top Products</h3>
                  <div className="rounded-lg border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-2 text-left font-medium">SKU</th>
                          <th className="px-4 py-2 text-left font-medium">Product</th>
                          <th className="px-4 py-2 text-right font-medium">Qty Sold</th>
                          <th className="px-4 py-2 text-right font-medium">Revenue</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {dailyQ.data.top_products.map((p, i) => (
                          <tr key={i}>
                            <td className="px-4 py-2 font-mono text-xs">{p.product__sku}</td>
                            <td className="px-4 py-2">{p.product__name}</td>
                            <td className="px-4 py-2 text-right tabular-nums">{p.qty_sold}</td>
                            <td className="px-4 py-2 text-right tabular-nums font-mono">
                              {paiseToRupees(p.revenue_paise)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {dailyQ.data.transaction_count === 0 && (
                <p className="text-muted-foreground text-sm text-center py-8">
                  No completed sales on {date}.
                </p>
              )}
            </>
          )}
        </div>
      )}

      {/* Date Range */}
      {tab === "range" && (
        <div className="space-y-6">
          <div className="flex items-end gap-3 flex-wrap">
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">
                From
              </label>
              <input
                type="date"
                value={rangeStart}
                onChange={(e) => setRangeStart(e.target.value)}
                className="border rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide block mb-1">
                To
              </label>
              <input
                type="date"
                value={rangeEnd}
                onChange={(e) => setRangeEnd(e.target.value)}
                className="border rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          </div>

          {rangeQ.isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}
          {rangeQ.data && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <SummaryCard
                  label="Transactions"
                  value={String(rangeQ.data.transaction_count)}
                />
                <SummaryCard
                  label="Total Revenue"
                  value={paiseToRupees(rangeQ.data.total_revenue_paise)}
                />
                <SummaryCard
                  label="Discounts"
                  value={paiseToRupees(rangeQ.data.total_discount_paise)}
                />
              </div>

              {rangeQ.data.daily_breakdown.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold">Daily Breakdown</h3>
                  <div className="rounded-lg border overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-2 text-left font-medium">Date</th>
                          <th className="px-4 py-2 text-right font-medium">Transactions</th>
                          <th className="px-4 py-2 text-right font-medium">Revenue</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {rangeQ.data.daily_breakdown.map((row) => (
                          <tr key={row.date}>
                            <td className="px-4 py-2 font-mono text-xs">{row.date}</td>
                            <td className="px-4 py-2 text-right tabular-nums">{row.count}</td>
                            <td className="px-4 py-2 text-right tabular-nums font-mono">
                              {paiseToRupees(row.revenue_paise)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Inventory Valuation */}
      {tab === "inventory" && (
        <div className="space-y-6">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadCsv("/reports/inventory/?export=csv", "inventory-valuation.csv")}
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />
              Export CSV
            </Button>
          </div>

          {invQ.isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}
          {invQ.data && (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <SummaryCard
                  label="Cost Value"
                  value={paiseToRupees(invQ.data.total_cost_value_paise)}
                />
                <SummaryCard
                  label="Sell Value"
                  value={paiseToRupees(invQ.data.total_sell_value_paise)}
                />
                <SummaryCard
                  label="Potential Profit"
                  value={paiseToRupees(invQ.data.potential_profit_paise)}
                />
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
                    {invQ.data.products.map((p) => (
                      <tr key={p.sku}>
                        <td className="px-4 py-2 font-mono text-xs">{p.sku}</td>
                        <td className="px-4 py-2">{p.name}</td>
                        <td className="px-4 py-2 text-right tabular-nums">{p.stock_qty}</td>
                        <td className="px-4 py-2 text-right tabular-nums font-mono">
                          {paiseToRupees(p.cost_value_paise)}
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums font-mono">
                          {paiseToRupees(p.sell_value_paise)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}