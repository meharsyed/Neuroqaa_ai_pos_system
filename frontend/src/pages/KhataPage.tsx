import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle, Clock, Eye, Loader2, Search, TrendingDown, TrendingUp,
  User, Wallet,
} from "lucide-react";

import { PageContainer } from "@/layouts/components/PageContainer";
import { PageHeader } from "@/layouts/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Money } from "@/components/ui/money";
import KhataDetailDialog from "@/components/khata/KhataDetailDialog";
import { customersApi } from "@/lib/customers";
import { useToast } from "@/lib/use-toast";
import { useAuthStore } from "@/store/authStore";
import { cn } from "@/lib/utils";
import type { Customer } from "@/types/customers";

type BucketId = "current" | "days_30" | "days_60" | "days_90_plus";

const BUCKETS: {
  id: BucketId;
  label: string;
  hint: string;
  badge: "success" | "warning" | "danger";
  accent: string;
}[] = [
  { id: "current",      label: "Current",       hint: "under 30 days",  badge: "success", accent: "border-l-success" },
  { id: "days_30",      label: "30+ days",      hint: "30 to 59 days",  badge: "warning", accent: "border-l-warning" },
  { id: "days_60",      label: "60+ days",      hint: "60 to 89 days",  badge: "warning", accent: "border-l-warning" },
  { id: "days_90_plus", label: "90+ days",      hint: "chase these",    badge: "danger",  accent: "border-l-destructive" },
];

function Insight({
  icon: Icon, label, value, sub, tone,
}: {
  icon: typeof Wallet; label: string; value: React.ReactNode;
  sub?: React.ReactNode; tone?: "danger" | "success";
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <p className={cn(
        "mt-1 text-2xl font-bold tabular-nums",
        tone === "danger" && "text-destructive",
        tone === "success" && "text-success",
      )}>
        {value}
      </p>
      {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

export default function KhataPage() {
  const qc = useQueryClient();
  const { toast } = useToast();
  const role = useAuthStore((s) => s.user?.role);
  const canRecordPayment = role === "owner" || role === "manager";

  const [search, setSearch] = useState("");
  const [detailFor, setDetailFor] = useState<Customer | null>(null);
  const [payFor, setPayFor] = useState<Customer | null>(null);
  const [amount, setAmount] = useState("");
  const [notes, setNotes] = useState("");

  const { data: report, isLoading, isError, refetch } = useQuery({
    queryKey: ["khata-report"],
    queryFn: customersApi.khataReport,
    refetchInterval: 60_000,
  });

  const { mutate: submitPayment, isPending } = useMutation({
    mutationFn: (d: { customer_id: number; amount_paise: number; notes?: string }) =>
      customersApi.recordPayment(d),
    onSuccess: (res) => {
      toast({
        title: "Payment recorded",
        description: `Balance is now Rs ${(res.customer.outstanding_paise / 100).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        variant: "success",
      });
      qc.invalidateQueries({ queryKey: ["khata-report"] });
      qc.invalidateQueries({ queryKey: ["khata-detail"] });
      setPayFor(null);
      setAmount("");
      setNotes("");
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: unknown } })?.response?.data;
      let detail = "Could not record the payment.";
      if (data && typeof data === "object") {
        const obj = data as Record<string, unknown>;
        const first = Object.values(obj).flat().find((v) => typeof v === "string");
        if (typeof obj.detail === "string") detail = obj.detail;
        else if (typeof first === "string") detail = first;
      }
      toast({ title: "Payment failed", description: detail, variant: "error" });
    },
  });

  const filtered = useMemo(() => {
    if (!report) return null;
    const q = search.trim().toLowerCase();
    const match = (c: Customer) =>
      !q ||
      c.name?.toLowerCase().includes(q) ||
      (c.phone ?? "").toLowerCase().includes(q);
    return {
      current: report.current.filter(match),
      days_30: report.days_30.filter(match),
      days_60: report.days_60.filter(match),
      days_90_plus: report.days_90_plus.filter(match),
    };
  }, [report, search]);

  function handleSubmit() {
    if (!payFor) return;
    const paise = Math.round(parseFloat(amount) * 100);
    if (!Number.isFinite(paise) || paise <= 0) {
      toast({ title: "Enter an amount", variant: "error" });
      return;
    }
    if (paise > payFor.outstanding_paise) {
      toast({
        title: "Amount is too high",
        description: "It cannot exceed the outstanding balance.",
        variant: "error",
      });
      return;
    }
    submitPayment({ customer_id: payFor.id, amount_paise: paise, notes });
  }

  const header = (
    <PageHeader
      title="Khata / Customer Credit"
      subtitle="Outstanding balances, ageing and collections"
    />
  );

  if (isLoading) {
    return (
      <PageContainer>
        {header}
        <div className="flex items-center justify-center p-10">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      </PageContainer>
    );
  }

  // A failed request must never render as "everyone has paid" on a
  // receivables screen — that reports the opposite of the truth.
  if (isError || !report || !filtered) {
    return (
      <PageContainer>
        {header}
        <EmptyState
          icon={AlertCircle}
          title="Could not load the khata report"
          description="Balances could not be fetched, so nothing is shown here. This does not mean customers have no outstanding balance."
          action={<Button onClick={() => refetch()}>Retry</Button>}
        />
      </PageContainer>
    );
  }

  const totalRows =
    filtered.current.length + filtered.days_30.length +
    filtered.days_60.length + filtered.days_90_plus.length;

  return (
    <PageContainer>
      {header}

      <div className="max-w-6xl space-y-6">
        {/* Insight strip */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Insight
            icon={Wallet}
            label="Total outstanding"
            value={<Money paise={report.total_outstanding_paise} />}
            sub={`across ${report.customer_count} customer${report.customer_count === 1 ? "" : "s"}`}
          />
          <Insight
            icon={TrendingDown}
            label="Collected (30 days)"
            value={<Money paise={report.collected_30d_paise} />}
            tone="success"
            sub={<>New credit given <Money paise={report.charged_30d_paise} /></>}
          />
          <Insight
            icon={TrendingUp}
            label="Net change (30 days)"
            value={<Money paise={report.net_30d_paise} sign />}
            tone={report.net_30d_paise > 0 ? "danger" : "success"}
            sub={report.net_30d_paise > 0 ? "credit is growing" : "credit is shrinking"}
          />
          <Insight
            icon={Clock}
            label="Oldest unpaid credit"
            value={report.oldest_credit_days !== null ? `${report.oldest_credit_days} days` : "—"}
            tone={(report.oldest_credit_days ?? 0) >= 90 ? "danger" : undefined}
            sub={report.largest_balance_name
              ? <>Largest: {report.largest_balance_name}</>
              : undefined}
          />
        </div>

        {/* Search */}
        <div className="relative max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or phone…"
            className="ps-9"
          />
        </div>

        {report.customer_count === 0 ? (
          <EmptyState
            icon={Wallet}
            title="No outstanding balances"
            description="Every customer is paid up."
          />
        ) : totalRows === 0 ? (
          <EmptyState
            icon={Search}
            title="No customer matches that search"
            description="Try a different name or phone number."
            action={<Button variant="outline" onClick={() => setSearch("")}>Clear search</Button>}
          />
        ) : (
          BUCKETS.map((b) => {
            const rows = filtered[b.id];
            if (rows.length === 0) return null;
            const bucketTotal = rows.reduce((s, c) => s + c.outstanding_paise, 0);
            return (
              <div key={b.id} className={cn("overflow-hidden rounded-lg border border-l-4", b.accent)}>
                <div className="flex items-center justify-between gap-3 border-b bg-muted/40 px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-semibold">{b.label}</span>
                    <span className="text-xs text-muted-foreground">{b.hint}</span>
                    <Badge variant={b.badge}>{rows.length}</Badge>
                  </div>
                  <span className="text-sm font-semibold tabular-nums">
                    <Money paise={bucketTotal} />
                  </span>
                </div>

                <div className="divide-y">
                  {rows.map((c) => (
                    <div key={c.id} className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent-soft/60">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
                        {(c.name || "?").charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">
                          {c.name || "Unnamed"}
                          {c.phone && (
                            <span className="ml-2 text-xs font-normal text-muted-foreground tabular-nums">
                              {c.phone}
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {c.days_overdue !== null ? `${c.days_overdue} days outstanding` : "—"}
                        </p>
                      </div>
                      <span className="shrink-0 text-sm font-semibold tabular-nums">
                        <Money paise={c.outstanding_paise} />
                      </span>
                      <div className="flex shrink-0 items-center gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          aria-label={`View khata for ${c.name || "customer"}`}
                          title="View khata"
                          onClick={() => setDetailFor(c)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        {canRecordPayment && (
                          <Button size="sm" variant="outline" onClick={() => setPayFor(c)}>
                            Record payment
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        )}

        {!canRecordPayment && report.customer_count > 0 && (
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <User className="h-3.5 w-3.5" />
            Only an owner or manager can record payments against a khata.
          </p>
        )}
      </div>

      <KhataDetailDialog
        customer={detailFor}
        open={!!detailFor}
        onOpenChange={(v) => !v && setDetailFor(null)}
        canRecordPayment={canRecordPayment}
        onRecordPayment={(c) => { setDetailFor(null); setPayFor(c); }}
      />

      {/* Record payment */}
      <Dialog open={!!payFor} onOpenChange={(v) => !v && setPayFor(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Record payment</DialogTitle>
          </DialogHeader>
          {payFor && (
            <div className="space-y-4">
              <div className="rounded-lg border bg-muted/40 px-3 py-2.5">
                <p className="text-sm font-medium">{payFor.name || "Customer"}</p>
                <p className="text-xs text-muted-foreground">
                  Outstanding <Money paise={payFor.outstanding_paise} />
                </p>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="khata-amount" className="text-sm font-medium">
                  Amount received (Rs)
                </label>
                <Input
                  id="khata-amount"
                  type="number"
                  min="0"
                  step="0.01"
                  autoFocus
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="tabular-nums"
                />
                <div className="flex gap-1.5 pt-1">
                  {[0.25, 0.5, 1].map((f) => (
                    <Button
                      key={f}
                      size="sm"
                      variant="subtle"
                      type="button"
                      onClick={() => setAmount((payFor.outstanding_paise * f / 100).toFixed(2))}
                    >
                      {f === 1 ? "Full amount" : `${f * 100}%`}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="khata-notes" className="text-sm font-medium">
                  Note <span className="text-muted-foreground">(optional)</span>
                </label>
                <Input
                  id="khata-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. cash received at shop"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPayFor(null)}>Cancel</Button>
            <Button onClick={handleSubmit} disabled={isPending}>
              {isPending ? <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</> : "Record payment"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
