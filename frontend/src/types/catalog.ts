export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string;
  is_active: boolean;
}

export interface Supplier {
  id: number;
  name: string;
  contact_person: string;
  phone: string;
  email: string;
  address: string;
  notes: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: number;
  name: string;
  sku: string;
  barcode: string;
  category: number | null;
  category_name: string | null;
  unit: string;
  description: string;
  cost_price_paise: number;
  sell_price_paise: number;
  cost_price: string;    // formatted "Rs. 550.00"
  sell_price: string;    // formatted "Rs. 850.00"
  low_stock_threshold: string;
  is_active: boolean;
  image?: string | null;  // file path (e.g. "products/abc123.jpg")
  image_url?: string | null;  // full URL to image
  stock_qty: string;
  is_low_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface Inventory {
  id: number;
  product: number;
  sku: string;
  product_name: string;
  unit: string;
  stock_qty: string;
  low_stock_threshold: string;
  is_low_stock: boolean;
  updated_at: string;
}

export interface StockMovement {
  id: number;
  product: number;
  product_sku: string;
  product_name: string;
  supplier: number | null;
  supplier_name: string | null;
  movement_type: string;
  qty_change: string;
  qty_after: string;
  cost_price_paise: number | null;
  reference: string;
  notes: string;
  created_by_name: string | null;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ProductFilters {
  search?: string;
  category?: number | "";
  is_active?: boolean;
  /** Include archived products — products that have history and were removed. */
  include_inactive?: boolean;
  low_stock?: boolean;
  page?: number;
  ordering?: string;
}

export interface ProductFormValues {
  name: string;
  sku: string;
  barcode: string;
  category: number | null;
  unit: string;
  description: string;
  cost_price_paise: number;
  sell_price_paise: number;
  low_stock_threshold: string;
  is_active: boolean;
}

export interface StockInFormValues {
  product: number;
  qty: string;
  cost_price_paise?: number;
  supplier?: number | null;
  reference?: string;
  notes?: string;
}

export const UNIT_OPTIONS = [
  { value: "pcs", label: "Pieces" },
  { value: "kg", label: "Kilograms" },
  { value: "litre", label: "Litres" },
  { value: "metre", label: "Metres" },
  { value: "sq_metre", label: "Square Metres" },
  { value: "box", label: "Box" },
  { value: "dozen", label: "Dozen" },
  { value: "bundle", label: "Bundle" },
] as const;