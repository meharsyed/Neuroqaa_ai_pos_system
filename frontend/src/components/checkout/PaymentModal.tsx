import { useMemo, useState } from "react";
import {
  AlertTriangle, Banknote, CheckCircle2, CreditCard, Landmark, Plus, Wallet, X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Money } from "@/components/ui/money";
import { paiseToRupees } from "@/lib/catalog";
import type { CartItem, PaymentMethod, TenderInput, TenderMethod } from "@/types/sales";
import type { Customer } from "@/types/customers";

interface PaymentModalProps {
  cartItems: CartItem[];
  discountPaise: number;
  taxPaise: number;
  /** Labour on this bill. Included in totalPaise; shown separately so the
   *  cashier can see what the customer is paying for. */
  installationPaise?: number;
  /** What the customer pays: goods + installation. */
  totalPaise: number;
  /**
   * `tenders` is everything the customer actually handed over. Whatever it
   * leaves unpaid goes on the khata — an empty list is a pure credit sale.
   */
  onConfirm: (tenders: TenderInput[]) => void;
  onCancel: () => void;
  isLoading: boolean;
  error?: string;
  customer?: Customer | null;
}

const METHODS: {
  key: TenderMethod | "credit";
  label: string;
  Icon: React.FC<{ className?: string }>;
}[] = [
  { key: "cash", label: "Cash", Icon: Banknote },
  { key: "card", label: "Card", Icon: CreditCard },
  { key: "bank_transfer", label: "Bank", Icon: Landmark },
  { key: "credit", label: "Khata", Icon: Wallet },
];

const LABEL: Record<TenderMethod, string> = {
  cash: "Cash",
  card: "Card",
  bank_transfer: "Bank transfer",
  upi: "UPI",
};

/** One row the cashier is filling in. `amountStr` is rupees, as typed. */
interface Row {
  id: number;
  method: TenderMethod;
  amountStr: string;
}

const rupees = (paise: number) =>
  (paise / 100) % 1 === 0 ? String(paise / 100) : (paise / 100).toFixed(2);

export default function PaymentModal({
  cartItems,
  discountPaise,
  taxPaise,
  installationPaise = 0,
  totalPaise,
  onConfirm,
  onCancel,
  isLoading,
  error,
  customer,
}: PaymentModalProps) {
  const canPayOnCredit = customer !== null && customer !== undefined;

  const [rows, setRows] = useState<Row[]>([
    { id: 1, method: "cash", amountStr: rupees(totalPaise) },
  ]);
  const nextId = useMemo(() => ({ current: 2 }), []);

  /**
   * Work out what each row actually settles.
   *
   * A cash row is capped at what is still owed — hand over Rs 500 for a
   * Rs 350 bill and Rs 350 settles the bill while Rs 150 comes back as
   * change. Card and bank rows settle exactly what is typed, because there
   * is no change from a card.
   */
  const applied = useMemo(() => {
    let settled = 0;
    return rows.map((row) => {
      const entered = Math.round((parseFloat(row.amountStr) || 0) * 100);
      const outstanding = Math.max(0, totalPaise - settled);
      const amount =
        row.method === "cash" ? Math.min(Math.max(0, entered), outstanding) : Math.max(0, entered);
      settled += amount;
      return { row, entered, amount, change: row.method === "cash" ? entered - amount : 0 };
    });
  }, [rows, totalPaise]);

  const paidPaise = applied.reduce((sum, a) => sum + a.amount, 0);
  const changePaise = applied.reduce((sum, a) => sum + Math.max(0, a.change), 0);
  const remainderPaise = totalPaise - paidPaise;

  const overpaid = remainderPaise < 0;
  const needsKhata = remainderPaise > 0;
  const availablePaise = customer?.available_credit_paise ?? null;
  const creditLimitPaise = customer?.effective_credit_limit_paise ?? null;
  // null means unlimited. The server enforces this too — the UI just refuses
  // to submit a sale it already knows will be rejected.
  const overLimit =
    needsKhata && availablePaise !== null && remainderPaise > availablePaise;

  const blocked =
    overpaid || (needsKhata && (!canPayOnCredit || overLimit)) || (!needsKhata && paidPaise <= 0 && totalPaise > 0);

  /** One tap on a method button = settle the whole bill that way. */
  function pickSingleMethod(key: TenderMethod | "credit") {
    if (key === "credit") {
      setRows([]);
    } else {
      setRows([{ id: nextId.current++, method: key, amountStr: rupees(totalPaise) }]);
    }
  }

  function addRow() {
    const used = new Set(rows.map((r) => r.method));
    const next = (["cash", "card", "bank_transfer"] as TenderMethod[]).find((m) => !used.has(m));
    setRows([
      ...rows,
      { id: nextId.current++, method: next ?? "cash", amountStr: rupees(Math.max(0, remainderPaise)) },
    ]);
  }

  function updateRow(id: number, patch: Partial<Row>) {
    setRows(rows.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  function removeRow(id: number) {
    setRows(rows.filter((r) => r.id !== id));
  }

  function submit() {
    onConfirm(
      applied
        .filter((a) => a.amount > 0)
        .map(({ row, entered, amount }) => ({
          method: row.method,
          amount_paise: amount,
          amount_tendered_paise: row.method === "cash" ? Math.max(entered, amount) : amount,
        }))
    );
  }

  // Which method the buttons should look selected for: a single full-value
  // tender, or Khata when nothing is being paid now.
  const singleMethod: PaymentMethod | null =
    rows.length === 0 ? "credit" : rows.length === 1 && !needsKhata ? rows[0].method : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onKeyDown={(e) => { if (e.key === "Escape") onCancel(); }}
    >
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[92vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Complete Payment</h2>
          <p className="text-sm text-muted-foreground">{cartItems.length} item{cartItems.length !== 1 ? "s" : ""}</p>
        </div>

        <div className="p-6 space-y-5">
          {/* Receipt preview */}
          <div className="bg-muted/40 rounded-lg p-4 text-sm font-mono space-y-1 max-h-44 overflow-y-auto">
            {cartItems.map((item, i) => {
              const lineGross = item.qty * item.unit_price_paise;
              const lineNet = lineGross - item.discount_paise;
              return (
                <div key={i}>
                  <div className="flex justify-between">
                    <span className="truncate mr-4">
                      {item.product_sku} · {item.product_name}
                      <span className="text-muted-foreground ml-1">×{item.qty}</span>
                    </span>
                    <span className="tabular-nums shrink-0">{paiseToRupees(lineNet)}</span>
                  </div>
                  {item.discount_pct > 0 && (
                    <div className="flex justify-between text-warning text-xs pl-2">
                      <span>{item.discount_pct}% item disc.</span>
                      <span className="tabular-nums">− {paiseToRupees(item.discount_paise)}</span>
                    </div>
                  )}
                </div>
              );
            })}
            {discountPaise > 0 && (
              <div className="flex justify-between text-warning pt-1 border-t border-dashed">
                <span>Bill discount</span>
                <span>− {paiseToRupees(discountPaise)}</span>
              </div>
            )}
            {taxPaise > 0 && (
              <div className="flex justify-between text-warning pt-1 border-t border-dashed">
                <span>Tax (FBR/GST)</span>
                <span>+ {paiseToRupees(taxPaise)}</span>
              </div>
            )}
            {installationPaise > 0 && (
              <div className="flex justify-between text-info pt-1 border-t border-dashed">
                <span>Installation / labour</span>
                <span>+ {paiseToRupees(installationPaise)}</span>
              </div>
            )}
            <div className="flex justify-between font-bold pt-1 border-t">
              <span>{installationPaise > 0 ? "AMOUNT DUE" : "TOTAL"}</span>
              <span>{paiseToRupees(totalPaise)}</span>
            </div>
          </div>

          {/* One tap = pay the whole bill this way. */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
              Payment Method
            </p>
            <div className="flex gap-2">
              {METHODS.map(({ key, label, Icon }) => {
                if (key === "credit" && !canPayOnCredit) return null;
                return (
                  <button
                    key={key}
                    onClick={() => pickSingleMethod(key)}
                    className={`flex-1 flex flex-col items-center gap-1 py-3 rounded-lg border-2 text-sm font-medium transition-colors ${
                      singleMethod === key
                        ? "border-primary bg-primary/5 text-primary"
                        : "border-border text-muted-foreground hover:border-primary/50"
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* What the customer is actually handing over. Type less than the
              total here and the rest goes on their khata. */}
          {rows.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Paying now
              </p>
              {applied.map(({ row, change }, idx) => (
                <div key={row.id} className="flex items-center gap-2">
                  <select
                    value={row.method}
                    onChange={(e) => updateRow(row.id, { method: e.target.value as TenderMethod })}
                    className="h-10 rounded-md border border-input bg-background px-2 text-sm"
                    aria-label="Payment method"
                  >
                    {(["cash", "card", "bank_transfer"] as TenderMethod[]).map((m) => (
                      <option key={m} value={m}>{LABEL[m]}</option>
                    ))}
                  </select>
                  <div className="relative flex-1">
                    <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                      Rs
                    </span>
                    <Input
                      type="number"
                      min={0}
                      step="50"
                      value={row.amountStr}
                      onChange={(e) => updateRow(row.id, { amountStr: e.target.value })}
                      className="ps-9 text-lg font-mono"
                      autoFocus={idx === 0}
                      aria-label={`${LABEL[row.method]} amount`}
                    />
                  </div>
                  {change > 0 && (
                    <span className="whitespace-nowrap text-xs font-medium text-success">
                      change <Money paise={change} />
                    </span>
                  )}
                  {rows.length > 1 && (
                    <Button size="icon" variant="ghost" onClick={() => removeRow(row.id)} aria-label="Remove">
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
              {rows.length < 3 && (
                <Button variant="ghost" size="sm" onClick={addRow} className="h-8 px-2 text-xs">
                  <Plus className="h-3.5 w-3.5" /> Add another method
                </Button>
              )}
            </div>
          )}

          {rows.length === 0 && (
            <Button variant="outline" size="sm" onClick={addRow} className="w-full">
              <Plus className="h-4 w-4" /> Take a part payment now
            </Button>
          )}

          {/* Change is worth its own line — it is what the cashier hands back. */}
          {changePaise > 0 && (
            <div className="flex items-center justify-between rounded-lg border border-success/30 bg-success-bg px-4 py-2">
              <span className="text-sm font-medium text-success">Change to give</span>
              <span className="text-lg font-bold tabular-nums text-success">
                <Money paise={changePaise} />
              </span>
            </div>
          )}

          {overpaid && (
            <p className="rounded-lg border border-destructive/40 bg-destructive-bg px-3 py-2 text-sm text-destructive">
              That is <Money paise={-remainderPaise} /> more than the bill. Reduce a
              payment — a card or bank transfer cannot give change.
            </p>
          )}

          {/* The remainder, and who carries it. */}
          {needsKhata && (
            <div className="space-y-2">
              <div className="rounded-lg border bg-accent-soft p-3 text-sm space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-muted-foreground">Paid now</span>
                  <span className="tabular-nums"><Money paise={paidPaise} /></span>
                </div>
                <div className="flex items-center justify-between border-t pt-1">
                  <span className="font-semibold">Goes on khata</span>
                  <span className="font-bold tabular-nums text-warning">
                    <Money paise={remainderPaise} />
                  </span>
                </div>

                {canPayOnCredit ? (
                  <>
                    <div className="flex items-center justify-between border-t pt-1">
                      <span className="font-medium text-muted-foreground">Customer</span>
                      <span className="font-medium">{customer!.display_name}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-muted-foreground">Currently owes</span>
                      <span className="tabular-nums"><Money paise={customer!.outstanding_paise} /></span>
                    </div>
                    {creditLimitPaise !== null && (
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-muted-foreground">Credit limit</span>
                        <span className="tabular-nums">
                          <Money paise={creditLimitPaise} />
                          {availablePaise !== null && (
                            <span className="ms-1.5 text-xs text-muted-foreground">
                              (<Money paise={availablePaise} /> left)
                            </span>
                          )}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center justify-between border-t pt-1">
                      <span className="font-medium text-muted-foreground">Will owe after this</span>
                      <span className="font-semibold tabular-nums">
                        <Money paise={customer!.outstanding_paise + remainderPaise} />
                      </span>
                    </div>
                  </>
                ) : null}
              </div>

              {!canPayOnCredit && (
                <div className="flex items-start gap-2 rounded-lg border border-warning/40 bg-warning-bg px-3 py-2.5 text-sm text-warning">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <p className="font-semibold">Nobody to bill the rest to</p>
                    <p className="text-xs">
                      <Money paise={remainderPaise} /> is unpaid. Add a customer to put it
                      on khata, or take the full amount now.
                    </p>
                  </div>
                </div>
              )}

              {overLimit && (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive-bg px-3 py-2.5 text-sm text-destructive">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <p className="font-semibold">This would break the credit limit</p>
                    <p className="text-xs">
                      Only <Money paise={availablePaise ?? 0} /> of credit is left — collect
                      at least <Money paise={remainderPaise - (availablePaise ?? 0)} /> more
                      now, or ask an owner to raise the limit.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Error banner — shown when the API returns 400 */}
        {error && (
          <div className="mx-6 mb-4 rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Footer */}
        <div className="px-6 pb-6 flex gap-3">
          <Button variant="outline" onClick={onCancel} className="flex-1" disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={submit} className="flex-1" disabled={isLoading || blocked}>
            {isLoading ? (
              "Processing…"
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                {needsKhata && paidPaise > 0 ? "Pay part & put rest on khata" : "Complete Sale"}
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
