/** Quotations. Deliberately separate from Sale — a quotation moves no stock. */

export type QuotationStatus = "draft" | "sent" | "accepted" | "declined" | "expired";

export interface BusinessProfile {
  id: number;
  name: string;
  address: string;
  phone: string;
  email: string;
  tax_number: string;
  footer: string;
  is_default: boolean;
  is_active: boolean;
}

export interface QuotationItem {
  id: number;
  product: number | null;
  name: string;
  sku: string;
  description: string;
  qty: string;
  unit: string;
  unit_price_paise: number;
  discount_paise: number;
  position: number;
  line_total_paise: number;
  /** True for a line the shop does not stock — priced by hand. */
  is_off_catalogue: boolean;
}

export interface Quotation {
  id: number;
  number: string;
  /** "QT-…-00007 rev 3" once it has been revised. */
  display_number: string;
  revision: number;
  status: QuotationStatus;
  profile: number | null;
  profile_name: string | null;
  customer: number | null;
  customer_name: string;
  customer_phone: string;
  customer_address: string;
  valid_days: number;
  valid_until: string | null;
  is_expired: boolean;
  subtotal_paise: number;
  discount_paise: number;
  tax_paise: number;
  tax_pct: string | null;
  installation_paise: number;
  installation_note: string;
  total_paise: number;
  notes: string;
  terms: string;
  items: QuotationItem[];
  created_by: number;
  created_by_name: string;
  converted_sale: number | null;
  converted_at: string | null;
  created_at: string;
  updated_at: string;
}

/** A line being typed. `product_id` absent means an off-catalogue line. */
export interface QuotationLineInput {
  product_id?: number | null;
  name?: string;
  sku?: string;
  description?: string;
  qty: string;
  unit?: string;
  unit_price_paise?: number;
  discount_paise?: number;
}

export interface CreateQuotationPayload {
  items: QuotationLineInput[];
  profile_id?: number | null;
  customer_id?: number | null;
  customer_name?: string;
  customer_phone?: string;
  customer_address?: string;
  discount_paise?: number;
  tax_pct?: number | null;
  installation_paise?: number;
  installation_note?: string;
  valid_days?: number;
  notes?: string;
  terms?: string;
}

/** What the till needs to pick a quotation up. */
export interface QuotationCart {
  quotation_id: number;
  number: string;
  customer_id: number | null;
  items: {
    product_id: number;
    name: string;
    sku: string;
    qty: string;
    unit_price_paise: number;
    discount_paise: number;
  }[];
  /** Lines with nothing in stock to sell — the cashier has to handle these. */
  off_catalogue_items: {
    name: string;
    sku: string;
    qty: string;
    unit_price_paise: number;
    discount_paise: number;
  }[];
  discount_paise: number;
  tax_pct: string | null;
  installation_paise: number;
  installation_note: string;
}
