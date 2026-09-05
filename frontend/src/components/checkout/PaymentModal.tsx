import { useState } from "react";
import { AlertTriangle, Banknote, CheckCircle2, CreditCard, Landmark, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Money } from "@/components/ui/money";
import { paiseToRupees } from "@/lib/catalog";
import type { CartItem, PaymentMethod } from "@/types/sales";
import type { Customer } from "@/types/customers";

interface PaymentModalProps {
  cartItems: CartItem[];
  discountPaise: number;
  taxPaise: number;
  totalPaise: number;
  onConfirm: (method: PaymentMethod, amountTenderedPaise: number) => void;
  onCancel: () => void;
  isLoading: boolean;
  error?: string;
  customer?: Customer | null;
}

const METHODS: { key: PaymentMethod; label: string; Icon: React.FC<{ className?: string }> }[] = [
  { key: "cash", label: "Cash", Icon: Banknote },
  { key: "card", label: "Card", Icon: CreditCard },
  { key: "bank_transfer", label: "Bank", Icon: Landmark },
  { key: "credit", label: "Khata", Icon: Wallet },
];

export default function PaymentModal({
  cartItems,
  discountPaise,
  taxPaise,
  totalPaise,
  onConfirm,
  onCancel,
  isLoading,
  error,
  customer,
}: PaymentModalProps) {
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [tenderedStr, setTenderedStr] = useState(
    () => ((totalPaise / 100) % 1 === 0 ? String(totalPaise / 100) : (totalPaise / 100).toFixed(2))
  );

  const tenderedPaise = Math.round(parseFloat(tenderedStr || "0") * 100);
  const changePaise = Math.max(0, tenderedPaise - totalPaise);
  const isShort = method === "cash" && tenderedPaise < totalPaise;
  const canPayOnCredit = customer !== null && customer !== undefined;

  // null means unlimited. The server enforces this too — the UI just refuses
  // to submit a sale it already knows will be rejected.
  const creditLimitPaise = customer?.effective_credit_limit_paise ?? null;
  const availablePaise = customer?.available_credit_paise ?? null;
  const overLimit =
    method === "credit" && availablePaise !== null && totalPaise > availablePaise;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onKeyDown={(e) => { if (e.key === "Escape") onCancel(); }}
    >
      <div className="bg-background rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
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
                    <div className="flex justify-between text-amber-600 text-xs pl-2">
                      <span>{item.discount_pct}% item disc.</span>
                      <span className="tabular-nums">− {paiseToRupees(item.discount_paise)}</span>
                    </div>
                  )}
                </div>
              );
            })}
            {discountPaise > 0 && (
              <div className="flex justify-between text-amber-600 pt-1 border-t border-dashed">
                <span>Bill discount</span>
                <span>− {paiseToRupees(discountPaise)}</span>
              </div>
            )}
            {taxPaise > 0 && (
              <div className="flex justify-between text-orange-600 pt-1 border-t border-dashed">
                <span>Tax (FBR/GST)</span>
                <span>+ {paiseToRupees(taxPaise)}</span>
              </div>
            )}
            <div className="flex justify-between font-bold pt-1 border-t">
              <span>TOTAL</span>
              <span>{paiseToRupees(totalPaise)}</span>
            </div>
          </div>

          {/* Payment method selector */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">Payment Method</p>
            <div className="flex gap-2">
              {METHODS.map(({ key, label, Icon }) => {
                if (key === "credit" && !canPayOnCredit) return null;
                return (
                  <button
                    key={key}
                    onClick={() => setMethod(key)}
                    className={`flex-1 flex flex-col items-center gap-1 py-3 rounded-lg border-2 text-sm font-medium transition-colors ${
                      method === key
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

          {/* Customer credit info (only for credit method) */}
          {method === "credit" && customer && (
            <div className="space-y-2">
              <div className="rounded-lg border bg-accent-soft p-3 text-sm space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-muted-foreground">Customer</span>
                  <span className="font-medium">{customer.display_name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-muted-foreground">Currently owes</span>
                  <span className="font-semibold tabular-nums">
                    <Money paise={customer.outstanding_paise} />
                  </span>
                </div>
                {creditLimitPaise !== null && (
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-muted-foreground">Credit limit</span>
                    <span className="tabular-nums">
                      <Money paise={creditLimitPaise} />
                      {availablePaise !== null && (
                        <span className="ml-1.5 text-xs text-muted-foreground">
                          (<Money paise={availablePaise} /> left)
                        </span>
                      )}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between border-t pt-1">
                  <span className="font-medium text-muted-foreground">After this sale</span>
                  <span className="font-semibold tabular-nums">
                    <Money paise={customer.outstanding_paise + totalPaise} />
                  </span>
                </div>
              </div>

              {overLimit && (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive-bg px-3 py-2.5 text-sm text-destructive">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <p className="font-semibold">This sale would break the credit limit</p>
                    <p className="text-xs">
                      Only <Money paise={availablePaise ?? 0} /> of credit is left.
                      Take a part payment in cash, collect against the khata first,
                      or ask an owner to raise the limit.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Cash tendered + change (only for cash) */}
          {method === "cash" && (
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Cash Tendered (Rs.)
                </label>
                <Input
                  type="number"
                  min={0}
                  step="50"
                  value={tenderedStr}
                  onChange={(e) => setTenderedStr(e.target.value)}
                  className="mt-1 text-lg font-mono"
                  autoFocus
                />
                {isShort && (
                  <p className="text-xs text-destructive mt-1">
                    Amount short by {paiseToRupees(totalPaise - tenderedPaise)}
                  </p>
                )}
              </div>
              {changePaise > 0 && (
                <div className="flex items-center justify-between rounded-lg border border-success/30 bg-success-bg px-4 py-2">
                  <span className="text-sm font-medium text-success">Change</span>
                  <span className="text-lg font-bold tabular-nums text-success">
                    <Money paise={changePaise} />
                  </span>
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
          <Button
            onClick={() => onConfirm(method, method === "cash" ? tenderedPaise : totalPaise)}
            className="flex-1"
            disabled={
              isLoading ||
              (method === "cash" && isShort) ||
              (method === "credit" && (!canPayOnCredit || overLimit))
            }
          >
            {isLoading ? (
              "Processing…"
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Complete Sale
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}