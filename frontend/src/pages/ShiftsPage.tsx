import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Clock, PlayCircle, StopCircle, CheckCircle2, AlertTriangle,
  Wallet, Loader2, ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { paiseToRupees, rupeesToPaise } from "@/lib/catalog";
import { shiftsApi } from "@/lib/shifts";
import type { ShiftCloseResult, ShiftReconciliation } from "@/types/config";

function formatDt(iso: string) {
  return new Date(iso).toLocaleString("en-PK", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function VarianceLine({ paise }: { paise: number }) {
  if (paise === 0)
    return <span className="font-bold text-emerald-600">✓ Balanced — drawer matches perfectly</span>;
  if (paise > 0)
    return <span className="font-bold text-blue-600">+{paiseToRupees(paise)} over (surplus)</span>;
  return <span className="font-bold text-red-600">{paiseToRupees(paise)} short (deficit)</span>;
}

export default function ShiftsPage() {
  const qc = useQueryClient();

  // Open shift form
  const [openingRs, setOpeningRs] = useState("0");
  const [openingNotes, setOpeningNotes] = useState("");

  // Close shift flow state
  type CloseStep = "idle" | "loading" | "confirm";
  const [closeStep, setCloseStep] = useState<CloseStep>("idle");
  const [reconcData, setReconcData] = useState<ShiftReconciliation | null>(null);
  const [closingRs, setClosingRs] = useState("");
  const [closingNotes, setClosingNotes] = useState("");
  const [closeResult, setCloseResult] = useState<ShiftCloseResult | null>(null);

  // Queries
  const {
    data: currentShiftData,
    isLoading: currentLoading,
    isError: shiftNotFound,
  } = useQuery({
    queryKey: ["shift-current"],
    queryFn: shiftsApi.current,
    retry: false,
    staleTime: 30_000,
  });

  // isError means the API returned 404 (no open shift). React Query keeps stale
  // data on error, so we must check isError explicitly — not just the data value.
  const currentShift = shiftNotFound ? undefined : currentShiftData;

  const { data: shiftList = [], isLoading: listLoading } = useQuery({
    queryKey: ["shifts"],
    queryFn: shiftsApi.list,
    staleTime: 60_000,
  });

  // Mutations
  const { mutate: openShift, isPending: isOpening } = useMutation({
    mutationFn: () => shiftsApi.open(rupeesToPaise(openingRs), openingNotes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["shift-current"] });
      qc.invalidateQueries({ queryKey: ["shifts"] });
      setOpeningRs("0");
      setOpeningNotes("");
    },
  });

  const { mutate: closeShift, isPending: isClosing } = useMutation({
    mutationFn: () =>
      shiftsApi.close(currentShift!.id, rupeesToPaise(closingRs), closingNotes),
    onSuccess: (result) => {
      setCloseResult(result);
      setCloseStep("idle");
      setReconcData(null);
      setClosingRs("");
      setClosingNotes("");
      qc.invalidateQueries({ queryKey: ["shift-current"] });
      qc.invalidateQueries({ queryKey: ["shifts"] });
    },
  });

  // Fetch reconciliation then enter confirm step
  async function handlePrepareClose() {
    if (!currentShift) return;
    setCloseStep("loading");
    try {
      const data = await shiftsApi.reconciliation(currentShift.id);
      setReconcData(data);
      // Pre-fill with expected so cashier sees the target
      setClosingRs(String((data.expected_cash_paise / 100).toFixed(2)));
      setCloseStep("confirm");
    } catch {
      setCloseStep("idle");
    }
  }

  function cancelClose() {
    setCloseStep("idle");
    setReconcData(null);
    setClosingRs("");
  }

  // Live variance as cashier types
  const closingPaise = Math.round((parseFloat(closingRs) || 0) * 100);
  const liveVariance = reconcData ? closingPaise - reconcData.expected_cash_paise : null;

  return (
    <div className="min-h-full flex flex-col">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center gap-2.5">
          <Clock className="h-5 w-5 text-primary" />
          <div>
            <h1 className="text-xl font-bold">Shift Management</h1>
            <p className="text-sm text-muted-foreground">
              Open and close cash drawer shifts with full reconciliation
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 max-w-3xl mx-auto w-full space-y-6">

        {/* ── Post-close result banner ───────────────────────────────────── */}
        {closeResult && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 space-y-4 animate-fade-up">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
              <h3 className="font-semibold text-emerald-800">
                Shift #{closeResult.shift.id} Closed Successfully
              </h3>
            </div>
            <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
              {([
                ["Opening Float",       paiseToRupees(closeResult.summary.opening_float_paise)],
                ["Cash Sales Total",    paiseToRupees(closeResult.summary.cash_sales_total_paise)],
                ["Expected in Drawer",  paiseToRupees(closeResult.summary.expected_cash_paise)],
                ["Actual Cash Counted", paiseToRupees(closeResult.summary.actual_cash_paise)],
                ["Total Transactions",  String(closeResult.summary.total_sales)],
                ["Total Revenue",       paiseToRupees(closeResult.summary.total_revenue_paise)],
              ] as [string, string][]).map(([label, value]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-muted-foreground">{label}</span>
                  <span className="font-mono font-medium">{value}</span>
                </div>
              ))}
              <div className="col-span-2 flex justify-between pt-2 border-t border-emerald-200">
                <span className="text-muted-foreground">Variance</span>
                <VarianceLine paise={closeResult.summary.variance_paise} />
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => setCloseResult(null)}>
              Dismiss
            </Button>
          </div>
        )}

        {/* ── Active shift card / open shift form ───────────────────────── */}
        {currentLoading ? (
          <div className="rounded-xl border p-6 flex items-center gap-2 text-muted-foreground text-sm">
            <Loader2 className="h-4 w-4 animate-spin" /> Checking shift status…
          </div>
        ) : currentShift ? (
          /* ── OPEN SHIFT CARD ── */
          <div className="rounded-xl border overflow-hidden shadow-sm">
            <div className="px-5 py-4 bg-emerald-50 border-b border-emerald-200 flex items-center gap-3">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
              <h2 className="font-semibold text-emerald-800">Shift #{currentShift.id} — Open</h2>
              <span className="ml-auto text-xs text-emerald-600 font-mono">
                Since {new Date(currentShift.opened_at).toLocaleTimeString("en-PK", {
                  hour: "2-digit", minute: "2-digit",
                })}
              </span>
            </div>

            <div className="px-5 py-4 text-sm grid grid-cols-2 gap-2 text-muted-foreground border-b">
              <span>Opened</span>
              <span className="text-foreground font-medium">{formatDt(currentShift.opened_at)}</span>
              <span>Opening float</span>
              <span className="text-foreground font-medium font-mono">
                {paiseToRupees(currentShift.opening_float_paise)}
              </span>
            </div>

            {/* Close flow */}
            <div className="px-5 py-4 space-y-4">
              {closeStep === "idle" && (
                <>
                  <p className="text-sm text-muted-foreground">
                    Click below to calculate expected cash and begin the closing process.
                  </p>
                  <Button
                    onClick={handlePrepareClose}
                    variant="destructive"
                    size="sm"
                    className="gap-2"
                  >
                    <StopCircle className="h-4 w-4" />
                    Prepare to Close Shift
                  </Button>
                </>
              )}

              {closeStep === "loading" && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Calculating expected cash…
                </div>
              )}

              {closeStep === "confirm" && reconcData && (
                <div className="space-y-5 animate-fade-up">
                  {/* Expected cash summary */}
                  <div className="rounded-lg bg-muted/30 border p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Wallet className="h-4 w-4 text-primary" />
                      <h3 className="font-semibold text-sm">Shift Summary</h3>
                    </div>
                    <div className="grid grid-cols-2 gap-y-2 text-sm">
                      <span className="text-muted-foreground">Opening float</span>
                      <span className="text-right font-mono">
                        {paiseToRupees(reconcData.opening_float_paise)}
                      </span>

                      <span className="text-muted-foreground">Cash sales during shift</span>
                      <span className="text-right font-mono text-emerald-600">
                        + {paiseToRupees(reconcData.cash_sales_total_paise)}
                      </span>

                      <span className="text-muted-foreground pt-2 border-t font-semibold">
                        Expected in drawer
                      </span>
                      <span className="text-right font-mono font-bold text-primary pt-2 border-t">
                        {paiseToRupees(reconcData.expected_cash_paise)}
                      </span>

                      <span className="text-muted-foreground text-xs mt-1">
                        Total transactions
                      </span>
                      <span className="text-right text-xs mt-1">{reconcData.total_sales}</span>

                      <span className="text-muted-foreground text-xs">
                        Total revenue (all methods)
                      </span>
                      <span className="text-right font-mono text-xs">
                        {paiseToRupees(reconcData.total_revenue_paise)}
                      </span>
                    </div>
                  </div>

                  {/* Cashier count input */}
                  <div>
                    <p className="text-sm font-medium mb-3">
                      Count your drawer and enter the actual amount:
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide block mb-1.5">
                          Actual Cash in Drawer (Rs.)
                        </label>
                        <Input
                          type="number"
                          min={0}
                          step="50"
                          value={closingRs}
                          onChange={(e) => setClosingRs(e.target.value)}
                          onFocus={(e) => e.target.select()}
                          placeholder="Enter counted amount"
                          className="font-mono text-base"
                          autoFocus
                        />
                        {/* Live variance */}
                        {closingRs && liveVariance !== null && (
                          <p className="text-xs mt-1.5 flex items-center gap-1">
                            {liveVariance === 0 ? (
                              <>
                                <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                                <span className="text-emerald-600 font-medium">Drawer balanced</span>
                              </>
                            ) : liveVariance > 0 ? (
                              <>
                                <ArrowRight className="h-3 w-3 text-blue-500" />
                                <span className="text-blue-600 font-medium">
                                  Over by {paiseToRupees(liveVariance)}
                                </span>
                              </>
                            ) : (
                              <>
                                <AlertTriangle className="h-3 w-3 text-red-500" />
                                <span className="text-red-600 font-medium">
                                  Short by {paiseToRupees(Math.abs(liveVariance))}
                                </span>
                              </>
                            )}
                          </p>
                        )}
                      </div>
                      <div>
                        <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide block mb-1.5">
                          Closing Notes (optional)
                        </label>
                        <Input
                          value={closingNotes}
                          onChange={(e) => setClosingNotes(e.target.value)}
                          placeholder="Any remarks…"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={cancelClose}>
                      Cancel
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      className="gap-2"
                      onClick={() => closeShift()}
                      disabled={isClosing || !closingRs}
                    >
                      {isClosing ? (
                        <><Loader2 className="h-4 w-4 animate-spin" /> Closing…</>
                      ) : (
                        <><StopCircle className="h-4 w-4" /> Confirm Close Shift</>
                      )}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* ── NO SHIFT — OPEN FORM ── */
          <div className="rounded-xl border overflow-hidden shadow-sm">
            <div className="px-5 py-4 bg-muted/30 border-b flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/40 shrink-0" />
              <h2 className="font-semibold text-muted-foreground">No Open Shift</h2>
            </div>
            <div className="px-5 py-5 space-y-4">
              <p className="text-sm text-muted-foreground">
                Open a shift before starting sales to enable cash reconciliation at day end.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide block mb-1.5">
                    Opening Float (Rs.)
                  </label>
                  <Input
                    type="number"
                    min={0}
                    step="50"
                    value={openingRs}
                    onChange={(e) => setOpeningRs(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide block mb-1.5">
                    Notes (optional)
                  </label>
                  <Input
                    value={openingNotes}
                    onChange={(e) => setOpeningNotes(e.target.value)}
                    placeholder="e.g. Morning shift"
                  />
                </div>
              </div>
              <Button onClick={() => openShift()} disabled={isOpening} size="sm" className="gap-2">
                {isOpening ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Opening…</>
                ) : (
                  <><PlayCircle className="h-4 w-4" /> Open Shift</>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* ── Shift history table ────────────────────────────────────────── */}
        <div className="space-y-3">
          <h2 className="text-xs font-bold uppercase tracking-widest text-muted-foreground/60">
            Shift History
          </h2>
          {listLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : shiftList.length === 0 ? (
            <p className="text-sm text-muted-foreground">No shifts recorded yet.</p>
          ) : (
            <div className="rounded-xl border overflow-hidden shadow-sm">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 border-b">
                  <tr>
                    {["#", "Cashier", "Opened", "Closed", "Float", "Status"].map((h, i) => (
                      <th
                        key={h}
                        className={`px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground ${
                          i >= 4 ? "text-right" : "text-left"
                        }`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {shiftList.map((shift) => (
                    <tr key={shift.id} className="hover:bg-muted/20 transition-colors">
                      <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">
                        #{shift.id}
                      </td>
                      <td className="px-4 py-2.5 font-medium">{shift.cashier_name}</td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground">
                        {formatDt(shift.opened_at)}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground">
                        {shift.closed_at ? (
                          formatDt(shift.closed_at)
                        ) : (
                          <span className="text-emerald-600 font-medium">Open</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs">
                        {paiseToRupees(shift.opening_float_paise)}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {shift.is_open ? (
                          <Badge variant="success" className="text-[10px]">Open</Badge>
                        ) : (
                          <Badge variant="secondary" className="text-[10px]">Closed</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}