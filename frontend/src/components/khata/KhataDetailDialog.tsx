import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle, ArrowDownLeft, ArrowUpRight, Check, FileText, Loader2,
  MessageCircle, Pencil, Receipt, RotateCcw, ShieldCheck, Wallet, X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Money } from "@/components/ui/money";
import { DateTime } from "@/components/ui/date-display";
import { Input } from "@/components/ui/input";
import { customersApi, openKhataStatement, whatsappReminderUrl } from "@/lib/customers";
import { toast } from "@/lib/use-toast";
import { cn } from "@/lib/utils";
import type { Customer, LedgerKind } from "@/types/customers";

type Tab = "ledger" | "purchases" | "payments";

const KIND_STYLE: Record<LedgerKind, { icon: typeof Wallet; tone: string; label: string }> = {
  sale:       { icon: Receipt,        tone: "text-foreground",   label: "Credit sale" },
  payment:    { icon: ArrowDownLeft,  tone: "text-success",      label: "Payment" },
  return:     { icon: RotateCcw,      tone: "text-info",         label: "Return" },
  void:       { icon: AlertTriangle,  tone: "text-destructive",  label: "Voided" },
  adjustment: { icon: ArrowUpRight,   tone: "text-warning",      label: "Adjustment" },
  opening:    { icon: Wallet,         tone: "text-muted-foreground", label: "Opening" },
};

function Tile({ label, value, strong }: { label: string; value: React.ReactNode; strong?: boolean }) {
  return (
    <div className="rounded-lg border bg-card px-3 py-2.5">
      <p className="text-2xs uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className={cn("mt-0.5 tabular-nums", strong ? "text-lg font-bold text-primary" : "text-sm font-semibold")}>
        {value}
      </p>
    </div>
  );
}

export default function KhataDetailDialog({
  customer,
  open,
  onOpenChange,
  onRecordPayment,
  canRecordPayment,
}: {
  customer: Customer | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onRecordPayment: (c: Customer) => void;
  /** Owners and managers only — the same people who may change a credit limit. */
  canRecordPayment: boolean;
}) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("ledger");
  const [editingLimit, setEditingLimit] = useState(false);
  const [limitInput, setLimitInput] = useState("");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["khata-detail", customer?.id],
    queryFn: () => customersApi.khataDetail(customer!.id),
    enabled: open && !!customer,
  });

  const { mutate: saveLimit, isPending: savingLimit } = useMutation({
    mutationFn: (paise: number | null) =>
      customersApi.update(customer!.id, { credit_limit_paise: paise }),
    onSuccess: () => {
      toast({ title: "Credit limit updated", variant: "success" });
      qc.invalidateQueries({ queryKey: ["khata-detail"] });
      qc.invalidateQueries({ queryKey: ["khata-report"] });
      setEditingLimit(false);
    },
    onError: (err: unknown) => {
      const d = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
      const msg = d ? Object.values(d).flat().find((v) => typeof v === "string") : null;
      toast({
        title: "Could not update the limit",
        description: typeof msg === "string" ? msg : undefined,
        variant: "error",
      });
    },
  });

  useEffect(() => {
    if (!open) setEditingLimit(false);
  }, [open]);

  if (!customer) return null;

  const waUrl = whatsappReminderUrl(
    customer.phone,
    customer.name,
    data?.summary.outstanding_paise ?? customer.outstanding_paise,
  );

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "ledger", label: "Ledger", count: data?.ledger.length },
    { id: "purchases", label: "Credit purchases", count: data?.credit_sales.length },
    { id: "payments", label: "Payments", count: data?.payments.length },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[88vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="pr-8">
            {customer.name || "Customer"}
            {customer.phone && (
              <span className="ml-2 text-sm font-normal text-muted-foreground tabular-nums">
                {customer.phone}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-14">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {isError && (
          <EmptyState
            icon={AlertTriangle}
            title="Could not load this khata"
            description="The history could not be fetched. This does not mean the balance is zero."
            action={<Button onClick={() => refetch()}>Retry</Button>}
          />
        )}

        {data && (
          <div className="space-y-4">
            {!data.summary.is_reconciled && (
              <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive-bg px-3 py-2.5 text-sm text-destructive">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <p className="font-semibold">This balance does not match its ledger</p>
                  <p className="text-xs">
                    Stored <Money paise={data.summary.outstanding_paise} />, ledger totals{" "}
                    <Money paise={data.summary.ledger_balance_paise} />. Do not collect against
                    this figure until it is investigated.
                  </p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Tile label="Total charged" value={<Money paise={data.summary.total_charged_paise} />} />
              <Tile label="Paid" value={<Money paise={data.summary.total_paid_paise} />} />
              <Tile label="Returned / voided" value={<Money paise={data.summary.total_reversed_paise} />} />
              <Tile label="Balance due" value={<Money paise={data.summary.outstanding_paise} />} strong />
            </div>

            {/* Credit limit */}
            <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/40 px-3 py-2.5 text-sm">
              <ShieldCheck className="h-4 w-4 shrink-0 text-muted-foreground" />
              {editingLimit ? (
                <>
                  <span className="text-muted-foreground">Credit limit (Rs)</span>
                  <Input
                    autoFocus
                    type="number"
                    min="0"
                    step="1"
                    value={limitInput}
                    onChange={(e) => setLimitInput(e.target.value)}
                    placeholder="blank = shop default"
                    className="h-8 w-40 tabular-nums"
                  />
                  <Button
                    size="sm"
                    disabled={savingLimit}
                    onClick={() => {
                      const raw = limitInput.trim();
                      if (raw === "") return saveLimit(null);
                      const paise = Math.round(parseFloat(raw) * 100);
                      if (!Number.isFinite(paise) || paise < 0) {
                        toast({ title: "Enter a valid amount", variant: "error" });
                        return;
                      }
                      saveLimit(paise);
                    }}
                  >
                    {savingLimit ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setEditingLimit(false)}>
                    <X className="h-4 w-4" />
                  </Button>
                </>
              ) : (
                <>
                  <span className="text-muted-foreground">Credit limit</span>
                  <span className="font-semibold tabular-nums">
                    {data.customer.effective_credit_limit_paise === null
                      ? "No limit"
                      : <Money paise={data.customer.effective_credit_limit_paise} />}
                  </span>
                  {data.customer.available_credit_paise !== null && (
                    <Badge variant={data.customer.available_credit_paise > 0 ? "neutral" : "danger"}>
                      <Money paise={data.customer.available_credit_paise} /> left
                    </Badge>
                  )}
                  {data.customer.credit_limit_paise === null && (
                    <span className="text-xs text-muted-foreground">(shop default)</span>
                  )}
                  {canRecordPayment && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="ms-auto"
                      onClick={() => {
                        setLimitInput(
                          data.customer.credit_limit_paise === null
                            ? ""
                            : String(data.customer.credit_limit_paise / 100),
                        );
                        setEditingLimit(true);
                      }}
                    >
                      <Pencil className="h-3.5 w-3.5" /> Edit
                    </Button>
                  )}
                </>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground">
              <span>{data.summary.credit_sale_count} credit purchase(s)</span>
              <span>{data.summary.payment_count} payment(s)</span>
              {data.summary.days_since_first_credit !== null && (
                <span>Oldest charge {data.summary.days_since_first_credit} days ago</span>
              )}
              {data.summary.last_payment_at && (
                <span>
                  Last paid <Money paise={data.summary.last_payment_paise} /> on{" "}
                  <DateTime value={data.summary.last_payment_at} />
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-2 border-y py-3">
              {canRecordPayment && data.summary.outstanding_paise > 0 && (
                <Button size="sm" onClick={() => onRecordPayment(customer)}>
                  <Wallet className="h-4 w-4" /> Record payment
                </Button>
              )}
              <Button size="sm" variant="outline" onClick={() => openKhataStatement(customer.id)}>
                <FileText className="h-4 w-4" /> Statement PDF
              </Button>
              {waUrl && data.summary.outstanding_paise > 0 && (
                <Button size="sm" variant="outline"
                        onClick={() => window.open(waUrl, "_blank", "noopener")}>
                  <MessageCircle className="h-4 w-4" /> Remind on WhatsApp
                </Button>
              )}
            </div>

            <div className="flex gap-1 border-b">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTab(t.id)}
                  className={cn(
                    "-mb-px border-b-2 px-3 py-2 text-sm transition-colors",
                    tab === t.id
                      ? "border-accent font-semibold text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground",
                  )}
                >
                  {t.label}
                  {t.count !== undefined && (
                    <span className="ml-1.5 text-xs text-muted-foreground">{t.count}</span>
                  )}
                </button>
              ))}
            </div>

            {tab === "ledger" && (
              data.ledger.length === 0 ? (
                <EmptyState icon={Wallet} title="No credit activity yet"
                            description="Credit purchases and payments will appear here." />
              ) : (
                <div className="divide-y rounded-lg border">
                  {data.ledger.map((e) => {
                    const style = KIND_STYLE[e.kind] ?? KIND_STYLE.adjustment;
                    const Icon = style.icon;
                    const owed = e.delta_paise > 0;
                    return (
                      <div key={e.id} className="flex items-center gap-3 px-3 py-2.5">
                        <Icon className={cn("h-4 w-4 shrink-0", style.tone)} />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">
                            {e.sale_number ?? style.label}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            <DateTime value={e.created_at} format="short" />
                            {e.note ? ` · ${e.note}` : ""}
                            {e.created_by_name && e.created_by_name !== "—" ? ` · ${e.created_by_name}` : ""}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className={cn("text-sm font-semibold tabular-nums",
                                           owed ? "text-foreground" : "text-success")}>
                            {owed ? "+" : "−"} <Money paise={Math.abs(e.delta_paise)} />
                          </p>
                          <p className="text-xs text-muted-foreground tabular-nums">
                            bal <Money paise={e.balance_after_paise} />
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )
            )}

            {tab === "purchases" && (
              data.credit_sales.length === 0 ? (
                <EmptyState icon={Receipt} title="No credit purchases" />
              ) : (
                <div className="divide-y rounded-lg border">
                  {data.credit_sales.map((s) => (
                    <div key={s.id} className="flex items-center gap-3 px-3 py-2.5">
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-mono text-sm">{s.sale_number}</p>
                        <p className="text-xs text-muted-foreground">
                          <DateTime value={s.created_at} format="short" /> · {s.item_count} item(s)
                        </p>
                      </div>
                      {s.status === "voided" && <Badge variant="danger">Voided</Badge>}
                      <p className={cn("shrink-0 text-sm font-semibold tabular-nums",
                                       s.status === "voided" && "line-through text-muted-foreground")}>
                        <Money paise={s.total_paise} />
                      </p>
                    </div>
                  ))}
                </div>
              )
            )}

            {tab === "payments" && (
              data.payments.length === 0 ? (
                <EmptyState icon={Wallet} title="No payments recorded yet" />
              ) : (
                <div className="divide-y rounded-lg border">
                  {data.payments.map((p) => (
                    <div key={p.id} className="flex items-center gap-3 px-3 py-2.5">
                      <ArrowDownLeft className="h-4 w-4 shrink-0 text-success" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm">
                          <DateTime value={p.received_date} format="short" />
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          {p.received_by_name || "—"}
                          {p.notes ? ` · ${p.notes}` : ""}
                        </p>
                      </div>
                      <p className="shrink-0 text-sm font-semibold tabular-nums text-success">
                        <Money paise={p.amount_paise} />
                      </p>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
