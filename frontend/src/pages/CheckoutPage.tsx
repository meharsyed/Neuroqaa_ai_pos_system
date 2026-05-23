import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Barcode, Search, Trash2, Minus, Plus, X, ShoppingCart,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import PaymentModal from "@/components/checkout/PaymentModal";
import { catalogApi, paiseToRupees, rupeesToPaise } from "@/lib/catalog";
import { salesApi } from "@/lib/sales";
import type { CartItem, PaymentMethod, Sale } from "@/types/sales";
import type { Product } from "@/types/catalog";

// ── helpers ────────────────────────────────────────────────────────────────

function cartSubtotal(items: CartItem[]): number {
  return items.reduce((sum, i) => sum + i.qty * i.unit_price_paise - i.discount_paise, 0);
}

// ── Main component ─────────────────────────────────────────────────────────

export default function CheckoutPage() {
  const qc = useQueryClient();

  // Cart state
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [saleDiscountRupees, setSaleDiscountRupees] = useState("0");

  // Search / barcode state
  const [barcodeVal, setBarcodeVal] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // UI state
  const [showPayment, setShowPayment] = useState(false);
  const [completedSale, setCompletedSale] = useState<Sale | null>(null);
  const [barcodeError, setBarcodeError] = useState("");

  // Refs for focus management
  const barcodeRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const discountRef = useRef<HTMLInputElement>(null);

  // Auto-focus barcode on mount
  useEffect(() => {
    barcodeRef.current?.focus();
  }, []);

  // ── Product search ─────────────────────────────────────────────────────

  const { data: searchResults } = useQuery({
    queryKey: ["products-search", searchQuery],
    queryFn: () => catalogApi.products.list({ search: searchQuery, page: 1 }),
    enabled: searchQuery.trim().length >= 2,
    staleTime: 10_000,
  });

  // ── Cart operations ────────────────────────────────────────────────────

  const addToCart = useCallback((product: Product) => {
    setCartItems((prev) => {
      const existing = prev.findIndex((i) => i.product_id === product.id);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = { ...updated[existing], qty: updated[existing].qty + 1 };
        setSelectedIdx(existing);
        return updated;
      }
      const newItem: CartItem = {
        product_id: product.id,
        product_sku: product.sku,
        product_name: product.name,
        product_unit: product.unit,
        qty: 1,
        unit_price_paise: product.sell_price_paise,
        discount_paise: 0,
      };
      setSelectedIdx(prev.length);
      return [...prev, newItem];
    });
    // Clear search after adding
    setSearchQuery("");
    setBarcodeVal("");
    setBarcodeError("");
    // Re-focus barcode for next scan
    setTimeout(() => barcodeRef.current?.focus(), 50);
  }, []);

  const removeItem = useCallback((idx: number) => {
    setCartItems((prev) => prev.filter((_, i) => i !== idx));
    setSelectedIdx((prev) => (prev === idx ? null : prev !== null && prev > idx ? prev - 1 : prev));
  }, []);

  const adjustQty = useCallback((idx: number, delta: number) => {
    setCartItems((prev) => {
      const updated = [...prev];
      const newQty = updated[idx].qty + delta;
      if (newQty <= 0) {
        setSelectedIdx(null);
        return prev.filter((_, i) => i !== idx);
      }
      updated[idx] = { ...updated[idx], qty: newQty };
      return updated;
    });
  }, []);

  const clearCart = useCallback(() => {
    setCartItems([]);
    setSelectedIdx(null);
    setSaleDiscountRupees("0");
    setCompletedSale(null);
    barcodeRef.current?.focus();
  }, []);

  // ── Barcode lookup ─────────────────────────────────────────────────────

  const handleBarcodeEnter = useCallback(async () => {
    const barcode = barcodeVal.trim();
    if (!barcode) return;
    setBarcodeError("");
    try {
      const product = await catalogApi.products.byBarcode(barcode);
      addToCart(product);
    } catch {
      setBarcodeError(`Barcode "${barcode}" not found.`);
      setBarcodeVal("");
    }
  }, [barcodeVal, addToCart]);

  // ── Create sale mutation ───────────────────────────────────────────────

  const { mutate: submitSale, isPending: isSaleLoading } = useMutation({
    mutationFn: salesApi.create,
    onSuccess: (sale) => {
      setCompletedSale(sale);
      setShowPayment(false);
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["low-stock"] });
    },
  });

  const handlePaymentConfirm = useCallback(
    (method: PaymentMethod, amountTenderedPaise: number) => {
      const discountPaise = rupeesToPaise(saleDiscountRupees || "0");
      submitSale({
        items: cartItems.map((i) => ({
          product_id: i.product_id,
          qty: String(i.qty),
          unit_price_paise: i.unit_price_paise,
          discount_paise: i.discount_paise,
        })),
        payment_method: method,
        amount_tendered_paise: amountTenderedPaise,
        discount_paise: discountPaise,
      });
    },
    [cartItems, saleDiscountRupees, submitSale]
  );

  // ── Totals ─────────────────────────────────────────────────────────────

  const subtotalPaise = useMemo(() => cartSubtotal(cartItems), [cartItems]);
  const discountPaise = useMemo(() => rupeesToPaise(saleDiscountRupees || "0"), [saleDiscountRupees]);
  const totalPaise = Math.max(0, subtotalPaise - discountPaise);

  // ── Keyboard shortcuts ─────────────────────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const inInput = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;

      switch (e.key) {
        case "F2":
          e.preventDefault();
          searchRef.current?.focus();
          break;
        case "F3":
          e.preventDefault();
          barcodeRef.current?.focus();
          break;
        case "F9":
          e.preventDefault();
          discountRef.current?.focus();
          break;
        case "F12":
          e.preventDefault();
          if (cartItems.length > 0 && !showPayment) setShowPayment(true);
          break;
        case "Escape":
          if (showPayment) setShowPayment(false);
          break;
        case "+":
        case "=":
          if (!inInput && selectedIdx !== null) {
            e.preventDefault();
            adjustQty(selectedIdx, 1);
          }
          break;
        case "-":
          if (!inInput && selectedIdx !== null) {
            e.preventDefault();
            adjustQty(selectedIdx, -1);
          }
          break;
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [cartItems.length, showPayment, selectedIdx, adjustQty]);

  // ── Post-sale success screen ────────────────────────────────────────────

  if (completedSale) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-4">
        <div className="rounded-full bg-green-100 p-6">
          <ShoppingCart className="h-12 w-12 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold">Sale Complete!</h2>
        <p className="text-muted-foreground font-mono">{completedSale.sale_number}</p>
        <p className="text-3xl font-bold tabular-nums">{paiseToRupees(completedSale.total_paise)}</p>
        {completedSale.payment.change_paise > 0 && (
          <p className="text-lg text-green-600 font-semibold">
            Change: {paiseToRupees(completedSale.payment.change_paise)}
          </p>
        )}
        <div className="flex gap-3 pt-4">
          <Button onClick={clearCart} size="lg">
            New Sale
          </Button>
          <Button variant="outline" size="lg" asChild>
            <Link to="/dashboard">Back to Dashboard</Link>
          </Button>
        </div>
      </div>
    );
  }

  // ── Main checkout layout ───────────────────────────────────────────────

  return (
    <>
      {/* Top bar */}
      <header className="flex items-center gap-3 px-4 py-2 border-b bg-card shrink-0">
        <Link
          to="/dashboard"
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Link>
        <span className="text-muted-foreground">·</span>
        <span className="font-semibold text-sm">Checkout</span>
        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
          <kbd className="px-1.5 py-0.5 border rounded text-[10px]">F2</kbd>
          <span>Search</span>
          <kbd className="px-1.5 py-0.5 border rounded text-[10px]">F3</kbd>
          <span>Barcode</span>
          <kbd className="px-1.5 py-0.5 border rounded text-[10px]">F12</kbd>
          <span>Pay</span>
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* ── Left: Cart ─────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col border-r overflow-hidden">
          {/* Cart items */}
          <div className="flex-1 overflow-y-auto">
            {cartItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-2">
                <ShoppingCart className="h-12 w-12 opacity-20" />
                <p className="text-sm">Cart is empty — scan a barcode or search for a product</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/30 sticky top-0">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium text-muted-foreground">Product</th>
                    <th className="px-2 py-2 text-center font-medium text-muted-foreground w-28">Qty</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">Price</th>
                    <th className="px-4 py-2 text-right font-medium text-muted-foreground">Subtotal</th>
                    <th className="w-8" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {cartItems.map((item, idx) => (
                    <tr
                      key={idx}
                      onClick={() => setSelectedIdx(idx)}
                      className={`cursor-pointer transition-colors ${
                        selectedIdx === idx ? "bg-primary/5" : "hover:bg-muted/30"
                      }`}
                    >
                      <td className="px-4 py-2.5">
                        <span className="font-mono text-xs text-muted-foreground mr-2">
                          {item.product_sku}
                        </span>
                        <span className="font-medium">{item.product_name}</span>
                      </td>
                      <td className="px-2 py-2.5">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={(e) => { e.stopPropagation(); adjustQty(idx, -1); }}
                            className="h-6 w-6 rounded border flex items-center justify-center hover:bg-muted transition-colors"
                          >
                            <Minus className="h-3 w-3" />
                          </button>
                          <span className="w-10 text-center tabular-nums font-mono">
                            {item.qty}
                          </span>
                          <button
                            onClick={(e) => { e.stopPropagation(); adjustQty(idx, 1); }}
                            className="h-6 w-6 rounded border flex items-center justify-center hover:bg-muted transition-colors"
                          >
                            <Plus className="h-3 w-3" />
                          </button>
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums text-muted-foreground">
                        {paiseToRupees(item.unit_price_paise)}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums font-medium">
                        {paiseToRupees(item.qty * item.unit_price_paise - item.discount_paise)}
                      </td>
                      <td className="pr-3">
                        <button
                          onClick={(e) => { e.stopPropagation(); removeItem(idx); }}
                          className="text-muted-foreground hover:text-destructive transition-colors"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Totals footer */}
          <div className="border-t bg-card p-4 space-y-2 shrink-0">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Subtotal ({cartItems.length} item{cartItems.length !== 1 ? "s" : ""})</span>
              <span className="tabular-nums">{paiseToRupees(subtotalPaise)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Discount (Rs.)
                <span className="ml-1 text-xs text-muted-foreground/60">[F9]</span>
              </span>
              <Input
                ref={discountRef}
                type="number"
                min={0}
                value={saleDiscountRupees}
                onChange={(e) => setSaleDiscountRupees(e.target.value)}
                className="w-28 h-7 text-right font-mono text-sm"
              />
            </div>
            <div className="flex justify-between font-bold text-lg pt-1 border-t">
              <span>TOTAL</span>
              <span className="tabular-nums">{paiseToRupees(totalPaise)}</span>
            </div>
            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={clearCart}
                disabled={cartItems.length === 0}
                className="flex-1"
              >
                <Trash2 className="h-4 w-4 mr-1.5" />
                Clear
              </Button>
              <Button
                size="sm"
                onClick={() => setShowPayment(true)}
                disabled={cartItems.length === 0}
                className="flex-1"
              >
                <ShoppingCart className="h-4 w-4 mr-1.5" />
                Pay Now
                <Badge variant="secondary" className="ml-2 text-xs">F12</Badge>
              </Button>
            </div>
          </div>
        </div>

        {/* ── Right: Add items panel ────────────────────────────────── */}
        <div className="w-80 xl:w-96 flex flex-col shrink-0 overflow-hidden">
          <div className="p-4 border-b space-y-3">
            {/* Barcode field */}
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1 mb-1">
                <Barcode className="h-3.5 w-3.5" />
                Scan Barcode
                <span className="ml-auto text-muted-foreground/60">[F3]</span>
              </label>
              <div className="relative">
                <Input
                  ref={barcodeRef}
                  value={barcodeVal}
                  onChange={(e) => { setBarcodeVal(e.target.value); setBarcodeError(""); }}
                  onKeyDown={(e) => e.key === "Enter" && handleBarcodeEnter()}
                  placeholder="Scan or type barcode, press Enter…"
                  className="pr-16 font-mono text-sm"
                />
                {barcodeVal && (
                  <button
                    onClick={() => { setBarcodeVal(""); setBarcodeError(""); barcodeRef.current?.focus(); }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
              {barcodeError && (
                <p className="text-xs text-destructive mt-1">{barcodeError}</p>
              )}
            </div>

            {/* Search field */}
            <div>
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide flex items-center gap-1 mb-1">
                <Search className="h-3.5 w-3.5" />
                Search by Name / SKU
                <span className="ml-auto text-muted-foreground/60">[F2]</span>
              </label>
              <Input
                ref={searchRef}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Type at least 2 characters…"
                className="text-sm"
              />
            </div>
          </div>

          {/* Search results */}
          <div className="flex-1 overflow-y-auto">
            {searchQuery.trim().length >= 2 && (
              <>
                {searchResults && searchResults.results.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center p-6">No products found.</p>
                ) : (
                  <div className="divide-y">
                    {searchResults?.results.map((product) => (
                      <button
                        key={product.id}
                        onClick={() => addToCart(product)}
                        className="w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="font-medium text-sm truncate">{product.name}</p>
                            <p className="text-xs text-muted-foreground font-mono">
                              {product.sku}
                              {product.category_name && ` · ${product.category_name}`}
                            </p>
                          </div>
                          <div className="text-right shrink-0">
                            <p className="text-sm font-semibold tabular-nums">{product.sell_price}</p>
                            <p className="text-xs text-muted-foreground">
                              Stock: {product.stock_qty} {product.unit}
                            </p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
            {searchQuery.trim().length === 0 && (
              <div className="p-6 text-center text-sm text-muted-foreground">
                <Barcode className="h-8 w-8 mx-auto mb-2 opacity-20" />
                <p>Scan a barcode or search for a product above.</p>
                <p className="mt-3 text-xs space-y-1">
                  <span className="block"><kbd className="border px-1 rounded">+</kbd> / <kbd className="border px-1 rounded">-</kbd> adjust qty of selected item</span>
                  <span className="block"><kbd className="border px-1 rounded">F9</kbd> jump to discount field</span>
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Payment modal */}
      {showPayment && (
        <PaymentModal
          cartItems={cartItems}
          subtotalPaise={subtotalPaise}
          discountPaise={discountPaise}
          totalPaise={totalPaise}
          onConfirm={handlePaymentConfirm}
          onCancel={() => setShowPayment(false)}
          isLoading={isSaleLoading}
        />
      )}
    </>
  );
}