import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  PlayCircle, StopCircle, CheckCircle2, AlertTriangle,
  Wallet, Loader2, ArrowRight, Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { FormNumberField, FormTextField } from "@/components/forms";
import { Money } from "@/components/ui/money";
import { rupeesToPaise } from "@/lib/catalog";
import { shiftsApi } from "@/lib/shifts";
import { useToast } from "@/lib/use-toast";
import type { ShiftCloseResult, ShiftReconciliation } from "@/types/config";
import { useTranslation } from "@/lib/useTranslation";

function formatDt(iso: string) {
  return new Date(iso).toLocaleString("en-PK", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function VarianceLine({ paise }: { paise: number }) {
  if (paise === 0)
    return <span className="font-bold text-teal-600">✓ Balanced — drawer matches perfectly</span>;
  if (paise > 0)
    return <span className="font-bold text-info">+<Money paise={paise} /> over (surplus)</span>;
  return <span className="font-bold text-destructive"><Money paise={paise} /> short (deficit)</span>;
}

export default function ShiftsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { toast } = useToast();

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
      toast({ title: "Shift opened", description: `Opening float: Rs ${parseFloat(openingRs).toFixed(2)}` });
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
      toast({ title: "Shift closed", description: result.summary.variance_paise === 0 ? "Drawer balanced perfectly" : `Variance: Rs ${Math.abs(result.summary.variance_paise / 100).toFixed(2)}` });
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
    <PageContainer>
      <PageHeader
        title={t("shifts.title")}
        subtitle={t("shifts.subtitle")}
      />

      <div className="max-w-3xl mx-auto w-full space-y-6">

        {/* ── Post-close result banner ───────────────────────────────────── */}
        {closeResult && (
          <div className="rounded-xl border border-teal-200 bg-teal-50 p-5 space-y-4 animate-fade-up">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-teal-600 shrink-0" />
              <h3 className="font-semibold text-teal-800">
                Shift #{closeResult.shift.id} Closed Successfully
              </h3>
            </div>
            <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
              {([
                ["Opening Float",       <Money paise={closeResult.summary.opening_float_paise} />],
                ["Cash Sales Total",    <Money paise={closeResult.summary.cash_sales_total_paise} />],
                ["Expected in Drawer",  <Money paise={closeResult.summary.expected_cash_paise} />],
                ["Actual Cash Counted", <Money paise={closeResult.summary.actual_cash_paise} />],
                ["Total Transactions",  String(closeResult.summary.total_sales)],
                ["Total Revenue",       <Money paise={closeResult.summary.total_revenue_paise} />],
              ] as [string, React.ReactNode][]).map(([label, value]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-muted-foreground">{label}</span>
                  <span className="font-mono font-medium">{value}</span>
                </div>
              ))}
              <div className="col-span-2 flex justify-between pt-2 border-t border-teal-200">
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
            <div className="px-5 py-4 bg-teal-50 border-b border-teal-200 flex items-center gap-3">
              <span className="h-2.5 w-2.5 rounded-full bg-teal-500 animate-pulse shrink-0" />
              <h2 className="font-semibold text-teal-800">Shift #{currentShift.id} — Open</h2>
              <span className="ml-auto text-xs text-teal-600 font-mono">
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
                <Money paise={currentShift.opening_float_paise} />
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
                        <Money paise={reconcData.opening_float_paise} />
                      </span>

                      <span className="text-muted-foreground">Cash sales during shift</span>
                      <span className="text-right font-mono text-teal-600">
                        + <Money paise={reconcData.cash_sales_total_paise} />
                      </span>

                      <span className="text-muted-foreground pt-2 border-t font-semibold">
                        Expected in drawer
                      </span>
                      <span className="text-right font-mono font-bold text-primary pt-2 border-t">
                        <Money paise={reconcData.expected_cash_paise} />
                      </span>

                      <span className="text-muted-foreground text-xs mt-1">
                        Total transactions
                      </span>
                      <span className="text-right text-xs mt-1">{reconcData.total_sales}</span>

                      <span className="text-muted-foreground text-xs">
                        Total revenue (all methods)
                      </span>
                      <span className="text-right font-mono text-xs">
                        <Money paise={reconcData.total_revenue_paise} />
                      </span>
                    </div>
                  </div>

                  {/* Cashier count input */}
                  <div>
                    <p className="text-sm font-medium mb-3">
                      Count your drawer and enter the actual amount:
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-4">
                        <FormNumberField
                          label="Actual Cash in Drawer (Rs.)"
                          name="closingRs"
                          value={closingRs}
                          onChange={setClosingRs}
                          min={0}
                          step={50}
                          placeholder="Enter counted amount"
                          hint="Count all cash in the drawer"
                        />
                        {/* Live variance */}
                        {closingRs && liveVariance !== null && (
                          <p className="text-xs flex items-center gap-1">
                            {liveVariance === 0 ? (
                              <>
                                <CheckCircle2 className="h-3 w-3 text-teal-500" />
                                <span className="text-teal-600 font-medium">Drawer balanced</span>
                              </>
                            ) : liveVariance > 0 ? (
                              <>
                                <ArrowRight className="h-3 w-3 text-info" />
                                <span className="text-info font-medium">
                                  Over by <Money paise={liveVariance} />
                                </span>
                              </>
                            ) : (
                              <>
                                <AlertTriangle className="h-3 w-3 text-destructive" />
                                <span className="text-destructive font-medium">
                                  Short by <Money paise={Math.abs(liveVariance)} />
                                </span>
                              </>
                            )}
                          </p>
                        )}
                      </div>
                      <FormTextField
                        label="Closing Notes"
                        name="closingNotes"
                        value={closingNotes}
                        onChange={setClosingNotes}
                        placeholder="Any remarks…"
                        hint="Optional"
                      />
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
                  <FormNumberField
                    label="Opening Float (Rs.)"
                    name="openingRs"
                    value={openingRs}
                    onChange={setOpeningRs}
                    min={0}
                    step={50}
                    hint="Starting cash in drawer"
                    required
                  />
                </div>
                <div>
                  <FormTextField
                    label="Notes"
                    name="openingNotes"
                    value={openingNotes}
                    onChange={setOpeningNotes}
                    placeholder="e.g. Morning shift"
                    hint="Optional"
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
            <div className="rounded-xl border overflow-hidden shadow-sm">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 border-b">
                  <tr>
                    {["#", t("shifts.colCashier"), t("shifts.colOpened"), t("shifts.colClosed"), t("shifts.colFloat"), t("common.status")].map((h, i) => (
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
                  {[...Array(4)].map((_, i) => (
                    <tr key={i}>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-8" /></td>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-24" /></td>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-32" /></td>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-32" /></td>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-16 ml-auto" /></td>
                      <td className="px-4 py-2.5"><Skeleton className="h-4 w-12 ml-auto" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : shiftList.length === 0 ? (
            <EmptyState
              icon={Clock}
              title="No shifts recorded yet"
              description="Open a new shift to start processing transactions."
            />
          ) : (
            <div className="rounded-xl border overflow-hidden shadow-sm">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 border-b">
                  <tr>
                    {["#", t("shifts.colCashier"), t("shifts.colOpened"), t("shifts.colClosed"), t("shifts.colFloat"), t("common.status")].map((h, i) => (
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
                          <span className="text-teal-600 font-medium">Open</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-xs">
                        <Money paise={shift.opening_float_paise} />
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {shift.is_open ? (
                          <Badge variant="success" className="text-[10px]">Open</Badge>
                        ) : (
                          <Badge variant="neutral" className="text-[10px]">Closed</Badge>
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
    </PageContainer>
  );
}