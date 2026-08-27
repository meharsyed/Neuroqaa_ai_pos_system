import { useState } from "react";
import { Banknote, CreditCard, Smartphone, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { paiseToRupees } from "@/lib/catalog";
import type { CartItem, PaymentMethod } from "@/types/sales";

interface PaymentModalProps {
  cartItems: CartItem[];
  discountPaise: number;
  taxPaise: number;
  totalPaise: number;
  onConfirm: (method: PaymentMethod, amountTenderedPaise: number) => void;
  onCancel: () => void;
  isLoading: boolean;
  error?: string;
}

const METHODS: { key: PaymentMethod; label: string; Icon: React.FC<{ className?: string }> }[] = [
  { key: "cash", label: "Cash", Icon: Banknote },
  { key: "card", label: "Card", Icon: CreditCard },
  { key: "upi", label: "UPI", Icon: Smartphone },
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
}: PaymentModalProps) {
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [tenderedStr, setTenderedStr] = useState(
    () => ((totalPaise / 100) % 1 === 0 ? String(totalPaise / 100) : (totalPaise / 100).toFixed(2))
  );

  const tenderedPaise = Math.round(parseFloat(tenderedStr || "0") * 100);
  const changePaise = Math.max(0, tenderedPaise - totalPaise);
  const isShort = method === "cash" && tenderedPaise < totalPaise;

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
              {METHODS.map(({ key, label, Icon }) => (
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
              ))}
            </div>
          </div>

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
                <div className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-4 py-2">
                  <span className="text-sm font-medium text-green-700">Change</span>
                  <span className="text-lg font-bold font-mono text-green-700">
                    {paiseToRupees(changePaise)}
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
            disabled={isLoading || (method === "cash" && isShort)}
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