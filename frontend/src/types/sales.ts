export type PaymentMethod = "cash" | "card" | "upi";

export interface SaleItemInput {
  product_id: number;
  qty: string;
  unit_price_paise: number;
  discount_paise?: number;
}

export interface CreateSalePayload {
  items: SaleItemInput[];
  payment_method: PaymentMethod;
  amount_tendered_paise: number;
  discount_paise?: number;
  notes?: string;
  customer_id?: number | null;
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
}

export interface PaymentRecord {
  method: PaymentMethod;
  amount_tendered_paise: number;
  change_paise: number;
}

export interface Sale {
  id: number;
  sale_number: string;
  status: "completed" | "voided";
  cashier: number;
  cashier_name: string;
  customer: number | null;
  customer_name: string | null;
  customer_phone: string | null;
  subtotal_paise: number;
  discount_paise: number;
  tax_paise: number;
  total_paise: number;
  notes: string;
  items: SaleItemRecord[];
  payment: PaymentRecord;
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
}