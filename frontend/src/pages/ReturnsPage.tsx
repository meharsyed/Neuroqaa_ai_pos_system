import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  RotateCcw, Search, CheckCircle2, Loader2, Package,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { FormTextField } from "@/components/forms";
import { Money } from "@/components/ui/money";
import { salesApi } from "@/lib/sales";
import { useToast } from "@/lib/use-toast";
import type { Sale, SaleItemRecord } from "@/types/sales";
import { useTranslation } from "@/lib/useTranslation";

function formatDt(iso: string) {
  return new Date(iso).toLocaleString("en-PK", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

// ── Return quantities state ───────────────────────────────────────────────────

type ReturnQtys = Record<number, string>; // product_id → qty string

type ReturnStage = "search" | "select" | "confirm";

export default function ReturnsPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [searchInput, setSearchInput]   = useState("");
  const [saleQuery, setSaleQuery]       = useState("");
  const [returnQtys, setReturnQtys]     = useState<ReturnQtys>({});
  const [notes, setNotes]               = useState("");
  const [completedReturn, setCompleted] = useState<Sale | null>(null);

  // Search the sale by number
  const { data: searchData, isLoading: isSearching } = useQuery({
    queryKey: ["sale-search", saleQuery],
    queryFn: () => salesApi.list({ search: saleQuery }),
    enabled: saleQuery.trim().length > 0,
    staleTime: 0,
  });

  const sale = searchData?.results?.find(
    (s) => s.sale_number.toLowerCase() === saleQuery.toLowerCase() && s.sale_type === "sale"
  ) ?? null;

  function handleSearch() {
    if (!searchInput.trim()) return;
    setSaleQuery(searchInput.trim());
    setReturnQtys({});
    setNotes("");
    setCompleted(null);
  }

  function setQty(productId: number, value: string) {
    setReturnQtys((prev) => ({ ...prev, [productId]: value }));
  }

  function maxQty(item: SaleItemRecord): number {
    return parseFloat(item.qty);
  }

  const returnItems = Object.entries(returnQtys)
    .filter(([, q]) => parseFloat(q) > 0)
    .map(([pid, q]) => ({ product_id: parseInt(pid), qty: q }));

  const returnTotal = returnItems.reduce((sum, ri) => {
    const item = sale?.items.find((i) => i.product === ri.product_id);
    if (!item) return sum;
    return sum + Math.round(parseFloat(ri.qty) * item.unit_price_paise);
  }, 0);

  // Derived, not stored: the indicator now follows the actual state of the
  // form instead of a step variable that was never advanced.
  const currentStage: ReturnStage =
    !sale ? "search" : returnTotal > 0 ? "confirm" : "select";

  const { mutate: submitReturn, isPending: isSubmitting, error: submitError } = useMutation({
    mutationFn: () => salesApi.processReturn(sale!.id, returnItems, notes),
    onSuccess: (result) => {
      toast({ title: "Return processed", description: `Return amount: Rs ${(returnTotal / 100).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` });
      setCompleted(result);
      setReturnQtys({});
    },
  });

  // ── Success screen ────────────────────────────────────────────────────────

  if (completedReturn) {
    return (
      <div className="min-h-full flex flex-col items-center justify-center p-8 bg-gradient-to-b from-background to-info-bg/20">
        <div className="text-center space-y-5 max-w-sm w-full animate-fade-in-scale">
          <div className="w-20 h-20 rounded-full bg-info-bg flex items-center justify-center mx-auto shadow-lg">
            <CheckCircle2 className="h-10 w-10 text-info" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-info">Return Processed</h2>
            <p className="text-sm text-muted-foreground font-mono mt-1">{completedReturn.sale_number}</p>
          </div>
          <div className="bg-white rounded-xl border shadow-sm p-4 space-y-2 text-sm text-left">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Return amount</span>
              <span className="font-bold text-xl tabular-nums text-info">
                <Money paise={Math.abs(completedReturn.total_paise)} />
              </span>
            </div>
            <div className="flex justify-between text-xs text-muted-foreground border-t pt-2">
              <span>Original bill</span>
              <span className="font-mono">{sale?.sale_number}</span>
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Items returned</span>
              <span>{completedReturn.items.length}</span>
            </div>
            <p className="text-xs text-info bg-info-bg border border-info/40 rounded px-2 py-1.5 mt-2">
              Stock has been restored automatically for all returned items.
            </p>
          </div>
          <Button
            onClick={() => { setCompleted(null); setSaleQuery(""); setSearchInput(""); }}
            className="w-full"
          >
            Process Another Return
          </Button>
        </div>
      </div>
    );
  }

  // ── Main layout ───────────────────────────────────────────────────────────

  return (
    <PageContainer>
      <PageHeader
        title={t("returns.title")}
        subtitle={t("returns.subtitle")}
      />

      {/* Stepper UI */}
      <div className="max-w-3xl mx-auto w-full mb-6">
        <div className="flex items-center justify-between">
          {[
            { id: "search", label: "Find Bill" },
            { id: "select", label: "Select Items" },
            { id: "confirm", label: "Confirm Return" },
          ].map((stepDef, idx, arr) => {
            const stepId = stepDef.id as ReturnStage;
            const order = ["search", "select", "confirm"];
            const stepOrder = order.indexOf(stepId);
            const currentOrder = order.indexOf(currentStage);
            const isActive = stepOrder === currentOrder;
            const isCompleted = stepOrder < currentOrder;

            return (
              <div key={stepId} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : isCompleted
                        ? "bg-success text-white"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {isCompleted ? "✓" : idx + 1}
                  </div>
                  <p className="text-xs mt-1 font-medium text-center text-foreground">{stepDef.label}</p>
                </div>
                {idx < arr.length - 1 && (
                  <div className={`h-0.5 flex-1 ${isCompleted ? "bg-success" : "bg-muted"}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="max-w-3xl mx-auto w-full space-y-6">

        {/* Bill search */}
        <div className="rounded-xl border overflow-hidden shadow-sm">
          <div className="px-5 py-4 bg-muted/20 border-b">
            <h2 className="text-sm font-semibold">Step 1 — Find the original bill</h2>
          </div>
          <div className="px-5 py-4">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                <Input
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  placeholder="Enter bill number (e.g. SALE-20260601-00005)"
                  className="pl-9 font-mono text-sm"
                />
              </div>
              <Button onClick={handleSearch} disabled={isSearching || !searchInput.trim()} className="gap-2">
                {isSearching ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                Search
              </Button>
            </div>

            {saleQuery && !isSearching && !sale && (
              <p className="text-sm text-destructive mt-2 flex items-center gap-1">
                Bill "{saleQuery}" not found or is already a return.
              </p>
            )}
          </div>
        </div>

        {/* Bill search loading state */}
        {saleQuery && isSearching && (
          <div className="rounded-xl border overflow-hidden shadow-sm">
            <div className="px-5 py-4 bg-muted/20 border-b">
              <h2 className="text-sm font-semibold">Step 2 — Select items to return</h2>
            </div>
            <div className="px-5 py-4 space-y-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          </div>
        )}

        {/* Sale details + return form */}
        {sale && !isSearching && (
          <>
            {/* Original sale info */}
            <div className="rounded-xl border overflow-hidden shadow-sm">
              <div className="px-5 py-4 bg-muted/20 border-b flex items-center justify-between">
                <h2 className="text-sm font-semibold">Step 2 — Select items to return</h2>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-muted-foreground">{sale.sale_number}</span>
                  <Badge variant="success" className="text-[10px]">Original Sale</Badge>
                </div>
              </div>

              {/* Sale meta */}
              <div className="px-5 py-3 border-b bg-muted/10 grid grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-muted-foreground">Date</span>
                  <p className="font-medium">{formatDt(sale.created_at)}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Cashier</span>
                  <p className="font-medium">{sale.cashier_name}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Original Total</span>
                  <p className="font-bold font-mono"><Money paise={sale.total_paise} /></p>
                </div>
              </div>

              {/* Items with return qty inputs */}
              <div className="divide-y">
                {sale.items.map((item) => {
                  const qty = returnQtys[item.product] ?? "";
                  const parsedQty = parseFloat(qty) || 0;
                  const max = maxQty(item);
                  const lineReturn = Math.round(parsedQty * item.unit_price_paise);

                  return (
                    <div key={item.id} className="px-5 py-3 flex items-center gap-4">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{item.product_name}</p>
                        <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                          {item.product_sku} · Sold: {item.qty} {item.product_unit} @ <Money paise={item.unit_price_paise} />
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <div>
                          <label className="text-[10px] text-muted-foreground block mb-0.5 text-right">
                            Return qty (max {max})
                          </label>
                          <Input
                            type="number"
                            min={0}
                            max={max}
                            step="1"
                            value={qty}
                            placeholder="0"
                            onChange={(e) => setQty(item.product, e.target.value)}
                            className={`w-24 text-right font-mono text-sm h-8 ${
                              parsedQty > max ? "border-destructive" : ""
                            }`}
                          />
                          {parsedQty > max && (
                            <p className="text-[10px] text-destructive text-right">Max {max}</p>
                          )}
                        </div>
                        <div className="text-right w-24">
                          <p className="text-xs text-muted-foreground">Return value</p>
                          <p className={`font-mono text-sm font-semibold ${parsedQty > 0 ? "text-foreground" : "text-muted-foreground/30"}`}>
                            {parsedQty > 0 ? <Money paise={lineReturn} /> : "—"}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Total return amount */}
              {returnTotal > 0 && (
                <div className="px-5 py-3 border-t bg-accent-soft flex justify-between items-center">
                  <span className="font-semibold text-sm">Total Return Amount</span>
                  <span className="font-bold text-xl tabular-nums text-primary">
                    <Money paise={returnTotal} />
                  </span>
                </div>
              )}
            </div>

            {/* Notes + submit */}
            <div className="rounded-xl border overflow-hidden shadow-sm">
              <div className="px-5 py-4 bg-muted/20 border-b">
                <h2 className="text-sm font-semibold">Step 3 — Confirm return</h2>
              </div>
              <div className="px-5 py-4 space-y-4">
                <FormTextField
                  label="Reason / Notes"
                  name="notes"
                  value={notes}
                  onChange={setNotes}
                  placeholder={t("returns.reasonPlaceholder")}
                  hint="Optional - for your records"
                />

                {submitError && (
                  <p className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                    {(submitError as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                      ?? "Return failed. Please check item quantities."}
                  </p>
                )}

                <Button
                  onClick={() => submitReturn()}
                  disabled={isSubmitting || returnItems.length === 0}
                  className="w-full gap-2"
                  size="lg"
                >
                  {isSubmitting ? (
                    <><Loader2 className="h-4 w-4 animate-spin" /> Processing Return…</>
                  ) : (
                    <><RotateCcw className="h-4 w-4" /> Process Return — <Money paise={returnTotal} /></>
                  )}
                </Button>

                <p className="text-xs text-muted-foreground text-center">
                  Stock will be automatically restored for all returned items.
                </p>
              </div>
            </div>
          </>
        )}

        {/* Empty state */}
        {!saleQuery && (
          <EmptyState
            icon={Package}
            title="Enter a bill number to begin"
            description="The customer should have their original receipt with the bill number"
          />
        )}

      </div>
    </PageContainer>
  );
}