import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Receipt, Search, X, Eye, ChevronLeft, ChevronRight,
  FileText, Printer, Ban, CheckCircle2, XCircle, User, Filter,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { paiseToRupees } from "@/lib/catalog";
import { salesApi } from "@/lib/sales";
import { openReceiptPdf, printReceipt } from "@/lib/reports";
import { useAuthStore } from "@/store/authStore";
import type { Sale } from "@/types/sales";

function formatDt(iso: string) {
  return new Date(iso).toLocaleString("en-PK", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// ── Detail modal ──────────────────────────────────────────────────────────────

function SaleDetailModal({
  sale,
  onClose,
  canVoid,
}: {
  sale: Sale;
  onClose: () => void;
  canVoid: boolean;
}) {
  const qc = useQueryClient();

  const { mutate: voidSale, isPending: isVoiding } = useMutation({
    mutationFn: () => salesApi.void(sale.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["bills"] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 p-4">
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-lg max-h-[92vh] overflow-y-auto animate-fade-in-scale">

        {/* Header */}
        <div className="sticky top-0 bg-background px-5 py-4 border-b flex items-center justify-between z-10">
          <div>
            <p className="font-bold font-mono">{sale.sale_number}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{formatDt(sale.created_at)}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={sale.status === "completed" ? "success" : "destructive"}>
              {sale.status}
            </Badge>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground p-1 rounded hover:bg-muted transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="p-5 space-y-5">
          {/* Meta */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
            <span className="text-muted-foreground">Cashier</span>
            <span className="font-medium">{sale.cashier_name}</span>
            {(sale.customer_name || sale.customer_phone) && (
              <>
                <span className="text-muted-foreground">Customer</span>
                <span className="font-medium">
                  {sale.customer_name || "—"}
                  {sale.customer_phone && (
                    <span className="text-muted-foreground ml-2 text-xs font-mono">
                      {sale.customer_phone}
                    </span>
                  )}
                </span>
              </>
            )}
          </div>

          {/* Items */}
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60 mb-2">
              Items
            </p>
            <div className="rounded-lg border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/40">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground">Product</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-muted-foreground">Qty</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-muted-foreground">Rate</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-muted-foreground">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {sale.items.map((item) => (
                    <tr key={item.id}>
                      <td className="px-3 py-2">
                        <p className="font-medium">{item.product_name}</p>
                        <p className="text-[10px] text-muted-foreground font-mono">{item.product_sku}</p>
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-xs">{item.qty}</td>
                      <td className="px-3 py-2 text-right text-xs">{paiseToRupees(item.unit_price_paise)}</td>
                      <td className="px-3 py-2 text-right font-mono font-semibold">
                        {paiseToRupees(item.subtotal_paise)}
                        {item.discount_paise > 0 && (
                          <p className="text-[10px] text-amber-600 font-normal">
                            −{paiseToRupees(item.discount_paise)} disc
                          </p>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Totals */}
          <div className="rounded-lg bg-muted/30 p-4 space-y-1.5 text-sm">
            <div className="flex justify-between text-muted-foreground">
              <span>Subtotal</span>
              <span className="font-mono">{paiseToRupees(sale.subtotal_paise)}</span>
            </div>
            {sale.discount_paise > 0 && (
              <div className="flex justify-between text-amber-600">
                <span>Discount</span>
                <span className="font-mono">− {paiseToRupees(sale.discount_paise)}</span>
              </div>
            )}
            <div className="flex justify-between font-bold text-base border-t pt-2">
              <span>Total</span>
              <span className="font-mono">{paiseToRupees(sale.total_paise)}</span>
            </div>
            {sale.payment && (
              <div className="border-t pt-2 space-y-1.5">
                <div className="flex justify-between text-muted-foreground">
                  <span>Paid ({sale.payment.method.toUpperCase()})</span>
                  <span className="font-mono">{paiseToRupees(sale.payment.amount_tendered_paise)}</span>
                </div>
                {sale.payment.change_paise > 0 && (
                  <div className="flex justify-between text-emerald-600 font-medium">
                    <span>Change</span>
                    <span className="font-mono">{paiseToRupees(sale.payment.change_paise)}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-1">
            {sale.status === "completed" && (
              <>
                <Button variant="outline" size="sm" onClick={() => openReceiptPdf(sale.id)}>
                  <FileText className="h-3.5 w-3.5 mr-1.5" /> PDF Receipt
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    printReceipt(sale.id).catch(() =>
                      alert("Printer not available. Check Settings → thermal_printer_ip.")
                    )
                  }
                >
                  <Printer className="h-3.5 w-3.5 mr-1.5" /> Print
                </Button>
              </>
            )}
            {canVoid && sale.status === "completed" && (
              <Button
                variant="destructive"
                size="sm"
                disabled={isVoiding}
                onClick={() => {
                  if (confirm(`Void sale ${sale.sale_number}? Stock will be restored and this cannot be undone.`))
                    voidSale();
                }}
              >
                <Ban className="h-3.5 w-3.5 mr-1.5" />
                {isVoiding ? "Voiding…" : "Void Sale"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function BillsPage() {
  const user = useAuthStore((s) => s.user);
  const canVoid = user?.role === "owner" || user?.role === "manager";

  const [search, setSearch]           = useState("");
  const [dateFrom, setDateFrom]       = useState("");
  const [dateTo, setDateTo]           = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | "completed" | "voided">("");
  const [page, setPage]               = useState(1);
  const [selected, setSelected]       = useState<Sale | null>(null);

  const params = {
    page,
    ...(search      && { search }),
    ...(dateFrom    && { date_from: dateFrom }),
    ...(dateTo      && { date_to: dateTo }),
    ...(statusFilter && { status: statusFilter }),
  };

  const { data, isLoading } = useQuery({
    queryKey: ["bills", params],
    queryFn: () => salesApi.list(params),
    staleTime: 30_000,
  });

  const sales      = data?.results ?? [];
  const totalCount = data?.count ?? 0;
  const totalPages = Math.ceil(totalCount / 10) || 1;
  const hasFilters = search || dateFrom || dateTo || statusFilter;

  function clearFilters() {
    setSearch(""); setDateFrom(""); setDateTo(""); setStatusFilter(""); setPage(1);
  }

  return (
    <div className="min-h-full flex flex-col">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center gap-2.5">
          <Receipt className="h-5 w-5 text-primary" />
          <div>
            <h1 className="text-xl font-bold">Bills &amp; Sales History</h1>
            <p className="text-sm text-muted-foreground">
              Search, filter, and review all past transactions
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 space-y-4">

        {/* Filter bar */}
        <div className="flex flex-wrap gap-2 items-end">
          {/* Search */}
          <div className="relative flex-1 min-w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            <Input
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              placeholder="Bill number, customer name or phone…"
              className="pl-9"
            />
          </div>

          {/* Date from */}
          <div className="flex items-center gap-1.5 shrink-0">
            <label className="text-xs text-muted-foreground whitespace-nowrap">From</label>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
              className="w-36 text-sm"
            />
          </div>

          {/* Date to */}
          <div className="flex items-center gap-1.5 shrink-0">
            <label className="text-xs text-muted-foreground whitespace-nowrap">To</label>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
              className="w-36 text-sm"
            />
          </div>

          {/* Status toggle */}
          <div className="flex gap-1 shrink-0">
            {(["", "completed", "voided"] as const).map((s) => (
              <button
                key={s}
                onClick={() => { setStatusFilter(s); setPage(1); }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  statusFilter === s
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background text-muted-foreground border-border hover:border-primary/40"
                }`}
              >
                {s === "" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>

          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="gap-1.5 text-muted-foreground shrink-0">
              <X className="h-3.5 w-3.5" /> Clear
            </Button>
          )}
        </div>

        {/* Result count */}
        {data && (
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Filter className="h-3.5 w-3.5" />
              {totalCount.toLocaleString()} bill{totalCount !== 1 ? "s" : ""} found
            </span>
            {totalPages > 1 && <span>Page {page} of {totalPages}</span>}
          </div>
        )}

        {/* Table */}
        {isLoading ? (
          <div className="rounded-xl border p-12 text-center text-sm text-muted-foreground">
            Loading bills…
          </div>
        ) : sales.length === 0 ? (
          <div className="rounded-xl border p-12 text-center">
            <Receipt className="h-8 w-8 mx-auto mb-3 opacity-15" />
            <p className="text-sm font-medium text-muted-foreground">No bills found</p>
            {hasFilters && (
              <button onClick={clearFilters} className="text-xs text-primary hover:underline mt-1">
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div className="rounded-xl border overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 border-b">
                <tr>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Bill #</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Date &amp; Time</th>
                  <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">Customer</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Items</th>
                  <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">Total</th>
                  <th className="px-4 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground">Pay</th>
                  <th className="px-4 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground">Status</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {sales.map((sale) => (
                  <tr
                    key={sale.id}
                    className={`transition-colors hover:bg-muted/25 ${
                      sale.status === "voided" ? "opacity-55" : ""
                    }`}
                  >
                    <td className="px-4 py-3">
                      <p className="font-mono text-xs font-semibold">{sale.sale_number}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">{sale.cashier_name}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                      {formatDt(sale.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      {sale.customer_name || sale.customer_phone ? (
                        <div className="flex items-center gap-1.5 text-xs">
                          <User className="h-3 w-3 text-muted-foreground shrink-0" />
                          <span className="truncate max-w-[110px]">
                            {sale.customer_name || sale.customer_phone}
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground/30 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                      {sale.items.length}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold">
                      {paiseToRupees(sale.total_paise)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded uppercase font-mono">
                        {sale.payment?.method ?? "—"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {sale.status === "completed" ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-400 mx-auto" />
                      )}
                    </td>
                    <td className="pr-3 text-center">
                      <button
                        onClick={() => setSelected(sale)}
                        className="text-muted-foreground hover:text-primary p-1 rounded hover:bg-primary/10 transition-colors"
                        title="View details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="px-4 py-3 border-t bg-muted/20 flex items-center justify-between">
                <Button
                  variant="outline" size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="gap-1"
                >
                  <ChevronLeft className="h-4 w-4" /> Prev
                </Button>
                <span className="text-xs text-muted-foreground">{page} / {totalPages}</span>
                <Button
                  variant="outline" size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="gap-1"
                >
                  Next <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {selected && (
        <SaleDetailModal
          sale={selected}
          onClose={() => setSelected(null)}
          canVoid={canVoid}
        />
      )}
    </div>
  );
}