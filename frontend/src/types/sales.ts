export type PaymentMethod = "cash" | "card" | "upi" | "bank_transfer" | "credit";

/** Everything needed to send a customer their bill. See apps/sales/sharing.py. */
export interface ShareInfo {
  /** False when sharing by link is turned off in Settings. */
  enabled: boolean;
  /** Signed, expiring public URL. Empty when disabled or no base URL is set. */
  public_url: string;
  message: string;
  whatsapp_url: string;
  /** Customer number in international form, or null. */
  customer_phone: string | null;
  expires_days: number;
}

export interface SerialInput {
  serial: string;
  warranty_months?: number | null;
}

export interface SaleItemInput {
  product_id: number;
  qty: string;
  unit_price_paise: number;
  discount_paise?: number;
  serials?: SerialInput[];
}

/** Anything but credit — khata is what the tenders leave unpaid, not a tender. */
export type TenderMethod = Exclude<PaymentMethod, "credit">;

/** One way the cashier settled part of a bill. */
export interface TenderInput {
  method: TenderMethod;
  amount_paise: number;
  /** Cash only: what the customer handed over, so change can be worked out. */
  amount_tendered_paise?: number;
}

export interface CreateSalePayload {
  items: SaleItemInput[];
  payment_method: PaymentMethod;
  amount_tendered_paise: number;
  discount_paise?: number;
  /**
   * The rate for this bill. The server computes the amount from it and stamps
   * the rate on the sale, so a reprinted receipt shows what was charged rather
   * than today's shop setting. Send tax_paise only for a flat figure.
   */
  tax_pct?: number;
  tax_paise?: number;
  /**
   * Labour billed on this bill and passed on to the technician. Part of what
   * the customer pays; never part of the shop's revenue, so the server keeps
   * it out of total_paise.
   */
  installation_paise?: number;
  installation_note?: string;
  notes?: string;
  customer_id?: number | null;
  /**
   * When present this replaces payment_method entirely: the bill is settled by
   * these tenders and whatever is left over goes on the customer's khata.
   */
  tenders?: TenderInput[];
}

export interface SaleItemSerial {
  id: number;
  serial: string;
  warranty_months?: number | null;
}

export interface SaleItemRecord {
  id: number;
  product: number;
  product_sku: string;
  product_name: string;
  product_unit: string;
  qty: string;
  unit_price_paise: number;
  discount_paise: number;
  subtotal_paise: number;
  serials?: SaleItemSerial[];
}

export interface PaymentRecord {
  id?: number;
  method: PaymentMethod;
  /** What this tender settled. Change is amount_tendered_paise − amount_paise. */
  amount_paise: number;
  amount_tendered_paise: number;
  change_paise: number;
}

export interface Sale {
  id: number;
  sale_number: string;
  sale_type: "sale" | "return";
  status: "completed" | "voided";
  return_of: number | null;
  cashier: number;
  cashier_name: string;
  customer: number | null;
  customer_name: string | null;
  customer_phone: string | null;
  subtotal_paise: number;
  discount_paise: number;
  tax_paise: number;
  /** The rate this bill was charged at. Null when tax was a flat amount. */
  tax_pct: string | null;
  /** Goods total: subtotal − discount + tax. This is the revenue figure. */
  total_paise: number;
  installation_paise: number;
  installation_note: string;
  /** total_paise + installation_paise — what the customer actually pays. */
  amount_due_paise: number;
  notes: string;
  items: SaleItemRecord[];
  /**
   * The primary tender — the largest non-credit one. Kept so screens that only
   * ever showed one method keep working; `payments` is the full picture.
   */
  payment: PaymentRecord | null;
  payments: PaymentRecord[];
  /** Sum of every non-credit tender. */
  amount_paid_paise: number;
  /** total_paise − amount_paid_paise: what went on the khata. */
  credit_paise: number;
  voided_by: number | null;
  voided_at: string | null;
  created_at: string;
}

/** A single item in the checkout cart (frontend-only, not persisted) */
export interface CartItem {
  product_id: number;
  product_sku: string;
  product_name: string;
  product_unit: string;
  qty: number;
  unit_price_paise: number;
  discount_pct: number;   // 0–100, entered by user; drives discount_paise
  discount_paise: number; // derived: round(qty × unit_price_paise × discount_pct / 100)
  serials?: SerialInput[]; // optional per-item serial numbers
}