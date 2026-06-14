import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, Barcode, Search, Trash2, Minus, Plus, X,
  ShoppingCart, FileText, Printer, CheckCircle2, Tag,
  Phone, UserCheck, UserPlus,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import PaymentModal from "@/components/checkout/PaymentModal";
import { catalogApi, paiseToRupees } from "@/lib/catalog";
import { salesApi } from "@/lib/sales";
import { customersApi } from "@/lib/customers";
import { configApi } from "@/lib/config";
import { openReceiptPdf, printReceipt } from "@/lib/reports";
import type { CartItem, PaymentMethod, Sale } from "@/types/sales";
import type { Product } from "@/types/catalog";
import type { Customer } from "@/types/customers";

// ── helpers ────────────────────────────────────────────────────────────────

function cartNetSubtotal(items: CartItem[]): number {
  return items.reduce((s, i) => s + i.qty * i.unit_price_paise - i.discount_paise, 0);
}

function cartItemDiscountsTotal(items: CartItem[]): number {
  return items.reduce((s, i) => s + i.discount_paise, 0);
}

function cartUnitCount(items: CartItem[]): number {
  return items.reduce((s, i) => s + i.qty, 0);
}

function computeItemDiscountPaise(qty: number, unitPricePaise: number, pct: number): number {
  const clamped = Math.min(100, Math.max(0, pct));
  return Math.round(qty * unitPricePaise * clamped / 100);
}

// ── Main component ─────────────────────────────────────────────────────────

export default function CheckoutPage() {
  const qc = useQueryClient();

  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [saleDiscountPct, setSaleDiscountPct] = useState("0");

  const [barcodeVal, setBarcodeVal] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const [showPayment, setShowPayment] = useState(false);
  const [completedSale, setCompletedSale] = useState<Sale | null>(null);
  const [barcodeError, setBarcodeError] = useState("");
  const [saleError, setSaleError] = useState("");

  // Optional customer state
  const [customerPhone, setCustomerPhone]   = useState("");
  const [customerName, setCustomerName]     = useState("");
  const [foundCustomer, setFoundCustomer]   = useState<Customer | null>(null);
  const [customerStatus, setCustomerStatus] = useState<"idle" | "found" | "new">("idle");

  // Tax state
  const [applyTax, setApplyTax] = useState(false);

  const barcodeRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const discountRef = useRef<HTMLInputElement>(null);

  useEffect(() => { barcodeRef.current?.focus(); }, []);

  // ── Tax setting ────────────────────────────────────────────────────────

  const { data: settings = [] } = useQuery({
    queryKey: ["settings"],
    queryFn: configApi.settings.list,
    staleTime: 30_000,  // refresh settings every 30s so tax rate changes appear quickly
  });
  const taxPct = parseFloat(settings.find((s) => s.key === "tax_pct")?.value ?? "0") || 0;

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
        const item = updated[existing];
        const newQty = item.qty + 1;
        updated[existing] = {
          product_id: item.product_id,
          product_sku: item.product_sku,
          product_name: item.product_name,
          product_unit: item.product_unit,
          unit_price_paise: item.unit_price_paise,
          discount_pct: item.discount_pct,
          qty: newQty,
          discount_paise: computeItemDiscountPaise(newQty, item.unit_price_paise, item.discount_pct),
        };
        setSelectedIdx(existing);
        return updated;
      }
      setSelectedIdx(prev.length);
      return [...prev, {
        product_id: product.id,
        product_sku: product.sku,
        product_name: product.name,
        product_unit: product.unit,
        qty: 1,
        unit_price_paise: product.sell_price_paise,
        discount_pct: 0,
        discount_paise: 0,
      }];
    });
    setSearchQuery("");
    setBarcodeVal("");
    setBarcodeError("");
    setTimeout(() => barcodeRef.current?.focus(), 50);
  }, []);

  const removeItem = useCallback((idx: number) => {
    setCartItems((prev) => prev.filter((_, i) => i !== idx));
    setSelectedIdx((prev) =>
      prev === idx ? null : prev !== null && prev > idx ? prev - 1 : prev
    );
  }, []);

  const adjustQty = useCallback((idx: number, delta: number) => {
    setCartItems((prev) => {
      const updated = [...prev];
      const item = updated[idx];
      const newQty = item.qty + delta;
      if (newQty <= 0) {
        setSelectedIdx(null);
        return prev.filter((_, i) => i !== idx);
      }
      updated[idx] = {
        product_id: item.product_id,
        product_sku: item.product_sku,
        product_name: item.product_name,
        product_unit: item.product_unit,
        unit_price_paise: item.unit_price_paise,
        discount_pct: item.discount_pct,
        qty: newQty,
        discount_paise: computeItemDiscountPaise(newQty, item.unit_price_paise, item.discount_pct),
      };
      return updated;
    });
  }, []);

  const setItemQty = useCallback((idx: number, qty: number) => {
    if (!Number.isFinite(qty) || qty < 1) return;
    setCartItems((prev) => {
      const updated = [...prev];
      const item = updated[idx];
      updated[idx] = {
        product_id: item.product_id,
        product_sku: item.product_sku,
        product_name: item.product_name,
        product_unit: item.product_unit,
        unit_price_paise: item.unit_price_paise,
        discount_pct: item.discount_pct,
        qty,
        discount_paise: computeItemDiscountPaise(qty, item.unit_price_paise, item.discount_pct),
      };
      return updated;
    });
  }, []);

  const setItemDiscountPct = useCallback((idx: number, pct: number) => {
    const clamped = Math.min(100, Math.max(0, Number.isFinite(pct) ? pct : 0));
    setCartItems((prev) => {
      const updated = [...prev];
      const item = updated[idx];
      updated[idx] = {
        product_id: item.product_id,
        product_sku: item.product_sku,
        product_name: item.product_name,
        product_unit: item.product_unit,
        unit_price_paise: item.unit_price_paise,
        qty: item.qty,
        discount_pct: clamped,
        discount_paise: computeItemDiscountPaise(item.qty, item.unit_price_paise, clamped),
      };
      return updated;
    });
  }, []);

  const clearCart = useCallback(() => {
    setCartItems([]);
    setSelectedIdx(null);
    setSaleDiscountPct("0");
    setCompletedSale(null);
    setCustomerPhone("");
    setCustomerName("");
    setFoundCustomer(null);
    setCustomerStatus("idle");
    setApplyTax(false);
    barcodeRef.current?.focus();
  }, []);

  // ── Customer lookup ────────────────────────────────────────────────────

  const handleCustomerLookup = useCallback(async () => {
    const phone = customerPhone.trim();
    if (!phone) return;
    try {
      const result = await customersApi.lookup(phone);
      if (result) {
        setFoundCustomer(result);
        setCustomerName(result.name);
        setCustomerStatus("found");
      } else {
        setFoundCustomer(null);
        setCustomerStatus("new");
      }
    } catch {
      setFoundCustomer(null);
      setCustomerStatus("new");
    }
  }, [customerPhone]);

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

  // ── Totals ─────────────────────────────────────────────────────────────

  const netSubtotalPaise = useMemo(() => cartNetSubtotal(cartItems), [cartItems]);
  const itemDiscountsTotalPaise = useMemo(() => cartItemDiscountsTotal(cartItems), [cartItems]);
  const totalUnits = useMemo(() => cartUnitCount(cartItems), [cartItems]);

  const billDiscountNum = useMemo(
    () => Math.min(100, Math.max(0, parseFloat(saleDiscountPct) || 0)),
    [saleDiscountPct]
  );
  const billDiscountPaise = useMemo(
    () => Math.round(netSubtotalPaise * billDiscountNum / 100),
    [netSubtotalPaise, billDiscountNum]
  );
  const taxableAmount = netSubtotalPaise - billDiscountPaise;
  const taxPaise = useMemo(
    () => (applyTax && taxPct > 0 ? Math.round(taxableAmount * taxPct / 100) : 0),
    [applyTax, taxPct, taxableAmount]
  );
  const totalPaise = Math.max(0, taxableAmount + taxPaise);

  // ── Create sale mutation ───────────────────────────────────────────────

  const { mutate: submitSale, isPending: isSaleLoading } = useMutation({
    mutationFn: salesApi.create,
    onSuccess: (sale) => {
      setCompletedSale(sale);
      setShowPayment(false);
      setSaleError("");
      qc.invalidateQueries({ queryKey: ["products"] });
      qc.invalidateQueries({ queryKey: ["low-stock"] });
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? "Sale failed. Please check your connection and try again.";
      setSaleError(detail);
    },
  });

  const handlePaymentConfirm = useCallback(
    async (method: PaymentMethod, amountTenderedPaise: number) => {
      // Resolve customer: use existing found customer, or create a new one on the fly
      let customer_id: number | null = foundCustomer?.id ?? null;
      if (!customer_id && customerPhone.trim() && customerStatus === "new") {
        try {
          const created = await customersApi.create({
            phone: customerPhone.trim(),
            name: customerName.trim() || undefined,
          });
          customer_id = created.id;
        } catch {
          // If creation fails (e.g. duplicate race condition) proceed without customer
        }
      }

      submitSale({
        items: cartItems.map((i) => ({
          product_id: i.product_id,
          qty: String(i.qty),
          unit_price_paise: i.unit_price_paise,
          discount_paise: i.discount_paise,
        })),
        payment_method: method,
        amount_tendered_paise: amountTenderedPaise,
        discount_paise: billDiscountPaise,
        tax_paise: taxPaise,
        customer_id,
      });
    },
    [cartItems, billDiscountPaise, taxPaise, foundCustomer, customerPhone, customerName, customerStatus, submitSale]
  );

  // ── Keyboard shortcuts ─────────────────────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const inInput = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;
      switch (e.key) {
        case "F2": e.preventDefault(); searchRef.current?.focus(); break;
        case "F3": e.preventDefault(); barcodeRef.current?.focus(); break;
        case "F9": e.preventDefault(); discountRef.current?.focus(); break;
        case "F12":
          e.preventDefault();
          if (cartItems.length > 0 && !showPayment) { setSaleError(""); setShowPayment(true); }
          break;
        case "Escape":
          if (showPayment) setShowPayment(false);
          break;
        case "+": case "=":
          if (!inInput && selectedIdx !== null) { e.preventDefault(); adjustQty(selectedIdx, 1); }
          break;
        case "-":
          if (!inInput && selectedIdx !== null) { e.preventDefault(); adjustQty(selectedIdx, -1); }
          break;
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [cartItems.length, showPayment, selectedIdx, adjustQty]);

  // ── Post-sale success screen ────────────────────────────────────────────

  if (completedSale) {
    return (
      <div className="min-h-full flex flex-col items-center justify-center bg-gradient-to-b from-background to-emerald-50/30 p-8">
        <div className="text-center space-y-5 max-w-sm w-full animate-fade-in-scale">
          <div className="w-20 h-20 rounded-full bg-emerald-100 flex items-center justify-center mx-auto shadow-lg shadow-emerald-200">
            <CheckCircle2 className="h-10 w-10 text-emerald-600" />
          </div>

          <div>
            <h2 className="text-2xl font-bold text-emerald-700">Sale Complete!</h2>
            <p className="text-sm text-muted-foreground font-mono mt-1">{completedSale.sale_number}</p>
          </div>

          <div className="bg-white rounded-xl border shadow-sm p-4 space-y-2 text-sm text-left">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Total charged</span>
              <span className="font-bold text-2xl tabular-nums">{paiseToRupees(completedSale.total_paise)}</span>
            </div>
            {completedSale.payment.change_paise > 0 && (
              <div className="flex justify-between text-emerald-600 font-semibold border-t pt-2">
                <span>Change to give</span>
                <span className="tabular-nums text-lg font-bold">{paiseToRupees(completedSale.payment.change_paise)}</span>
              </div>
            )}
            <div className="flex justify-between text-xs text-muted-foreground border-t pt-2">
              <span>Items</span>
              <span>{completedSale.items.length}</span>
            </div>
            {completedSale.discount_paise > 0 && (
              <div className="flex justify-between text-xs text-amber-600">
                <span>Bill discount</span>
                <span>− {paiseToRupees(completedSale.discount_paise)}</span>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2 w-full">
            <Button onClick={clearCart} size="lg" className="w-full bg-emerald-600 hover:bg-emerald-700">
              <ShoppingCart className="h-4 w-4 mr-2" />
              New Sale
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => openReceiptPdf(completedSale.id)}>
                <FileText className="h-4 w-4 mr-1.5" /> PDF
              </Button>
              <Button
                variant="outline"
                className="flex-1"
                onClick={() =>
                  printReceipt(completedSale.id)
                    .then(() => alert("Receipt sent to printer."))
                    .catch(() => alert("Printer not available. Check Settings → thermal_printer_ip."))
                }
              >
                <Printer className="h-4 w-4 mr-1.5" /> Print
              </Button>
              <Button variant="outline" className="flex-1" asChild>
                <Link to="/dashboard">Dashboard</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Main checkout layout ───────────────────────────────────────────────

  return (
    <>
      {/* Top bar */}
      <header className="flex items-center gap-3 px-4 py-2.5 border-b bg-card shrink-0 shadow-sm">
        <Link
          to="/dashboard"
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Dashboard
        </Link>
        <span className="text-border">·</span>
        <span className="font-semibold text-sm">Checkout</span>
        {cartItems.length > 0 && (
          <Badge variant="secondary" className="text-xs font-mono">
            {totalUnits} unit{totalUnits !== 1 ? "s" : ""}
          </Badge>
        )}
        <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          {(
            [["F2","Search"],["F3","Barcode"],["F9","Discount"],["F12","Pay"]] as const
          ).map(([key, label]) => (
            <span key={key} className="flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 border rounded text-[10px] bg-muted/60">{key}</kbd>
              {label}
            </span>
          ))}
        </div>
      </header>

      {/* Body */}
      <div className="flex-1 flex overflow-hidden">

        {/* ── Left: Cart ─────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col border-r overflow-hidden">

          {/* Cart items list */}
          <div className="flex-1 overflow-y-auto">
            {cartItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground">
                <div className="w-16 h-16 rounded-full bg-muted/40 flex items-center justify-center">
                  <ShoppingCart className="h-7 w-7 opacity-25" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium">Cart is empty</p>
                  <p className="text-xs text-muted-foreground/60 mt-0.5">
                    Scan a barcode or search for a product →
                  </p>
                </div>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead className="border-b bg-muted/40 sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Product
                    </th>
                    <th className="px-2 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground w-32">
                      Qty
                    </th>
                    <th className="px-1 py-2.5 text-center text-xs font-semibold uppercase tracking-wide text-muted-foreground w-[72px]">
                      Disc %
                    </th>
                    <th className="px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Unit Price
                    </th>
                    <th className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Total
                    </th>
                    <th className="w-9" />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {cartItems.map((item, idx) => {
                    const lineGross = item.qty * item.unit_price_paise;
                    const lineNet = lineGross - item.discount_paise;
                    const isSelected = selectedIdx === idx;
                    return (
                      <tr
                        key={idx}
                        onClick={() => setSelectedIdx(idx)}
                        className={`cursor-pointer transition-all duration-100 ${
                          isSelected
                            ? "bg-primary/[0.07] shadow-[inset_3px_0_0_hsl(var(--primary))]"
                            : "hover:bg-muted/25"
                        }`}
                      >
                        {/* Product name + SKU + discount badge */}
                        <td className="px-4 py-2.5">
                          <div className="font-medium leading-tight">{item.product_name}</div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="font-mono text-[10px] text-muted-foreground">
                              {item.product_sku}
                            </span>
                            {item.discount_pct > 0 && (
                              <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-amber-700 bg-amber-100 border border-amber-200 rounded px-1 py-0 leading-4">
                                <Tag className="h-2 w-2" />
                                {item.discount_pct}% off
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Qty — direct input + ± buttons */}
                        <td
                          className="px-2 py-2.5"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="flex items-center justify-center gap-1">
                            <button
                              tabIndex={-1}
                              onClick={() => adjustQty(idx, -1)}
                              className="h-6 w-6 rounded border flex items-center justify-center hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-colors shrink-0"
                            >
                              <Minus className="h-3 w-3" />
                            </button>
                            <input
                              type="number"
                              min={1}
                              value={item.qty}
                              onFocus={(e) => e.target.select()}
                              onChange={(e) => {
                                const val = parseInt(e.target.value, 10);
                                if (!isNaN(val)) setItemQty(idx, val);
                              }}
                              className="w-11 text-center tabular-nums font-mono text-sm border rounded px-1 py-0.5 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary bg-background"
                            />
                            <button
                              tabIndex={-1}
                              onClick={() => adjustQty(idx, 1)}
                              className="h-6 w-6 rounded border flex items-center justify-center hover:bg-primary/10 hover:text-primary hover:border-primary/30 transition-colors shrink-0"
                            >
                              <Plus className="h-3 w-3" />
                            </button>
                          </div>
                        </td>

                        {/* Item discount % */}
                        <td
                          className="px-1 py-2.5"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div className="relative flex items-center justify-center">
                            <input
                              type="number"
                              min={0}
                              max={100}
                              step={1}
                              value={item.discount_pct === 0 ? "" : item.discount_pct}
                              placeholder="0"
                              onFocus={(e) => e.target.select()}
                              onChange={(e) => {
                                const val = parseFloat(e.target.value);
                                setItemDiscountPct(idx, isNaN(val) ? 0 : val);
                              }}
                              className={`w-14 text-right tabular-nums text-xs border rounded pl-1 pr-5 py-1 focus:outline-none focus:ring-2 transition-colors ${
                                item.discount_pct > 0
                                  ? "border-amber-300 bg-amber-50 text-amber-800 font-semibold focus:ring-amber-200"
                                  : "border-border bg-background text-muted-foreground focus:ring-primary/20"
                              }`}
                            />
                            <span className="absolute right-1.5 text-[10px] text-muted-foreground pointer-events-none">
                              %
                            </span>
                          </div>
                        </td>

                        {/* Unit price */}
                        <td className="px-3 py-2.5 text-right tabular-nums text-muted-foreground text-xs">
                          {paiseToRupees(item.unit_price_paise)}
                        </td>

                        {/* Line total */}
                        <td className="px-4 py-2.5 text-right">
                          <div className="font-semibold tabular-nums">{paiseToRupees(lineNet)}</div>
                          {item.discount_paise > 0 && (
                            <div className="text-[10px] text-muted-foreground/60 tabular-nums line-through">
                              {paiseToRupees(lineGross)}
                            </div>
                          )}
                        </td>

                        {/* Remove */}
                        <td className="pr-2 text-center">
                          <button
                            tabIndex={-1}
                            onClick={(e) => { e.stopPropagation(); removeItem(idx); }}
                            className="text-muted-foreground hover:text-destructive transition-colors p-1 rounded hover:bg-destructive/10"
                          >
                            <X className="h-3.5 w-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Totals footer */}
          <div className="border-t bg-card shrink-0">
            <div className="px-4 pt-3 pb-2 space-y-1.5 text-sm">

              {/* Net subtotal (after item discounts) */}
              <div className="flex justify-between text-muted-foreground">
                <span>
                  Subtotal
                  <span className="text-xs ml-1.5 text-muted-foreground/60">
                    ({totalUnits} unit{totalUnits !== 1 ? "s" : ""})
                  </span>
                </span>
                <span className="tabular-nums">{paiseToRupees(netSubtotalPaise)}</span>
              </div>

              {/* Item discounts summary */}
              {itemDiscountsTotalPaise > 0 && (
                <div className="flex justify-between text-xs text-amber-600">
                  <span className="flex items-center gap-1">
                    <Tag className="h-3 w-3" />
                    Item discounts
                  </span>
                  <span className="tabular-nums">− {paiseToRupees(itemDiscountsTotalPaise)}</span>
                </div>
              )}

              {/* Bill-level discount % */}
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-1.5">
                  Bill discount
                  <kbd className="text-[9px] border px-1 py-px rounded bg-muted/60 font-mono">F9</kbd>
                </span>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Input
                      ref={discountRef}
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      value={saleDiscountPct}
                      onChange={(e) => setSaleDiscountPct(e.target.value)}
                      onFocus={(e) => e.target.select()}
                      className="w-20 h-7 text-right font-mono text-sm pr-7"
                    />
                    <span className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground pointer-events-none">
                      %
                    </span>
                  </div>
                  <span
                    className={`text-xs tabular-nums w-24 text-right font-medium ${
                      billDiscountPaise > 0 ? "text-amber-600" : "text-muted-foreground/30"
                    }`}
                  >
                    {billDiscountPaise > 0 ? `− ${paiseToRupees(billDiscountPaise)}` : "—"}
                  </span>
                </div>
              </div>


              {/* Tax toggle — always visible; shows "Set in Settings" if rate is 0 */}
              <div className="flex items-center justify-between">
                <label className={`flex items-center gap-2 cursor-pointer select-none ${taxPct > 0 ? "text-muted-foreground" : "text-muted-foreground/40"}`}>
                  <input
                    type="checkbox"
                    checked={applyTax}
                    disabled={taxPct === 0}
                    onChange={(e) => setApplyTax(e.target.checked)}
                    className="h-3.5 w-3.5 accent-primary"
                  />
                  <span className="text-xs">
                    {taxPct > 0 ? `Tax (${taxPct}% FBR/GST)` : "Tax — set rate in Settings"}
                  </span>
                </label>
                <span
                  className={`text-xs tabular-nums w-24 text-right font-medium ${
                    applyTax && taxPaise > 0 ? "text-orange-600" : "text-muted-foreground/30"
                  }`}
                >
                  {applyTax && taxPaise > 0 ? `+ ${paiseToRupees(taxPaise)}` : "—"}
                  </span>
                </div>
            </div>

            {/* Grand total */}
            <div className="px-4 py-3 border-t bg-muted/30 flex justify-between items-center">
              <span className="font-bold text-base tracking-wide">TOTAL</span>
              <span className="tabular-nums font-bold text-2xl">{paiseToRupees(totalPaise)}</span>
            </div>

            {/* Action buttons */}
            <div className="px-4 pb-4 pt-2 flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={clearCart}
                disabled={cartItems.length === 0}
                className="flex items-center gap-1.5 shrink-0"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Clear
              </Button>
              <Button
                size="sm"
                onClick={() => { setSaleError(""); setShowPayment(true); }}
                disabled={cartItems.length === 0}
                className="flex-1 bg-gradient-to-r from-primary to-indigo-600 hover:from-primary/90 hover:to-indigo-700 shadow-sm shadow-primary/25"
              >
                <ShoppingCart className="h-4 w-4 mr-1.5" />
                Pay Now
                <kbd className="ml-2 text-[10px] bg-white/20 text-white border-0 rounded px-1.5 py-0.5">
                  F12
                </kbd>
              </Button>
            </div>
          </div>
        </div>

        {/* ── Right: Add items panel ────────────────────────────────── */}
        <div className="w-80 xl:w-96 flex flex-col shrink-0 overflow-hidden bg-card border-l">

          {/* Panel header */}
          <div className="px-4 py-3 border-b bg-muted/20">
            <h2 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
              Add Items
            </h2>
          </div>

          {/* ── Optional customer section ─────────────────────────── */}
          <div className="px-4 py-3 border-b bg-background/50 space-y-2">
            <label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5">
              <Phone className="h-3.5 w-3.5" />
              Customer (optional)
            </label>
            <div className="flex gap-1.5">
              <Input
                value={customerPhone}
                onChange={(e) => {
                  setCustomerPhone(e.target.value);
                  if (customerStatus !== "idle") { setCustomerStatus("idle"); setFoundCustomer(null); }
                }}
                onKeyDown={(e) => e.key === "Enter" && handleCustomerLookup()}
                placeholder="03001234567"
                type="tel"
                className="flex-1 text-sm font-mono h-8"
              />
              <Button
                size="sm"
                variant="outline"
                className="h-8 px-2.5 shrink-0"
                disabled={!customerPhone.trim()}
                onClick={handleCustomerLookup}
              >
                <Search className="h-3.5 w-3.5" />
              </Button>
            </div>

            {customerStatus === "found" && foundCustomer && (
              <div className="flex items-center gap-1.5 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-2.5 py-1.5">
                <UserCheck className="h-3.5 w-3.5 shrink-0" />
                <span className="font-medium truncate">{foundCustomer.display_name}</span>
                <span className="ml-auto shrink-0 text-emerald-500">{foundCustomer.total_sales} visits</span>
              </div>
            )}

            {customerStatus === "new" && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs text-blue-600 bg-blue-50 border border-blue-200 rounded-lg px-2.5 py-1.5">
                  <UserPlus className="h-3.5 w-3.5 shrink-0" />
                  New customer — will be saved on checkout
                </div>
                <Input
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                  placeholder="Name (optional)"
                  className="text-sm h-7"
                />
              </div>
            )}

            {customerStatus !== "idle" && (
              <button
                onClick={() => { setCustomerPhone(""); setCustomerName(""); setFoundCustomer(null); setCustomerStatus("idle"); }}
                className="text-[10px] text-muted-foreground hover:text-destructive transition-colors"
              >
                × Remove customer
              </button>
            )}
          </div>

          <div className="p-4 border-b space-y-3 bg-background/50">
            {/* Barcode */}
            <div>
              <label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5 mb-1.5">
                <Barcode className="h-3.5 w-3.5" />
                Scan Barcode
                <span className="ml-auto font-mono text-muted-foreground/40">F3</span>
              </label>
              <div className="relative">
                <Input
                  ref={barcodeRef}
                  value={barcodeVal}
                  onChange={(e) => { setBarcodeVal(e.target.value); setBarcodeError(""); }}
                  onKeyDown={(e) => e.key === "Enter" && handleBarcodeEnter()}
                  placeholder="Scan or type barcode, Enter…"
                  className="pr-8 font-mono text-sm"
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
                <p className="text-xs text-destructive mt-1 flex items-center gap-1">
                  <X className="h-3 w-3 shrink-0" />
                  {barcodeError}
                </p>
              )}
            </div>

            {/* Search */}
            <div>
              <label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest flex items-center gap-1.5 mb-1.5">
                <Search className="h-3.5 w-3.5" />
                Search Product
                <span className="ml-auto font-mono text-muted-foreground/40">F2</span>
              </label>
              <Input
                ref={searchRef}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Name or SKU (2+ chars)…"
                className="text-sm"
              />
            </div>
          </div>

          {/* Search results / keyboard hints */}
          <div className="flex-1 overflow-y-auto">
            {searchQuery.trim().length >= 2 ? (
              <>
                {!searchResults || searchResults.results.length === 0 ? (
                  <div className="px-4 py-8 text-center">
                    <p className="text-sm text-muted-foreground">
                      No products found for <span className="font-medium">"{searchQuery}"</span>
                    </p>
                  </div>
                ) : (
                  <div className="divide-y">
                    {searchResults.results.map((product) => (
                      <button
                        key={product.id}
                        onClick={() => addToCart(product)}
                        className="w-full text-left px-4 py-3 hover:bg-primary/5 active:bg-primary/10 transition-colors group"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="font-medium text-sm truncate group-hover:text-primary transition-colors">
                              {product.name}
                            </p>
                            <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                              {product.sku}
                              {product.category_name && (
                                <span className="text-muted-foreground/50"> · {product.category_name}</span>
                              )}
                            </p>
                          </div>
                          <div className="text-right shrink-0">
                            <p className="text-sm font-semibold tabular-nums text-primary">
                              {product.sell_price}
                            </p>
                            <p className={`text-[10px] mt-0.5 ${
                              product.stock_qty <= (product.low_stock_threshold ?? 5)
                                ? "text-amber-600 font-medium"
                                : "text-muted-foreground"
                            }`}>
                              {product.stock_qty} {product.unit}
                            </p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="px-5 py-8 text-center text-muted-foreground space-y-4">
                <Barcode className="h-10 w-10 mx-auto opacity-10" />
                <div>
                  <p className="text-sm font-medium">Scan or search to add items</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">
                    Set % discount per item in the Disc% column
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs bg-muted/40 rounded-lg p-3 text-left">
                  {[
                    ["+  /  -", "qty of selected"],
                    ["F9", "bill discount"],
                    ["F12", "open payment"],
                    ["Esc", "close modal"],
                  ].map(([key, label]) => (
                    <div key={key} className="flex items-center gap-1.5">
                      <kbd className="border px-1.5 py-0.5 rounded bg-background text-[10px] font-mono shrink-0">
                        {key}
                      </kbd>
                      <span className="text-muted-foreground">{label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Payment modal */}
      {showPayment && (
        <PaymentModal
          cartItems={cartItems}
          discountPaise={billDiscountPaise}
          taxPaise={taxPaise}
          totalPaise={totalPaise}
          onConfirm={handlePaymentConfirm}
          onCancel={() => setShowPayment(false)}
          isLoading={isSaleLoading}
          error={saleError}
        />
      )}
    </>
  );
}