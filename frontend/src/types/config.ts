export interface Setting {
  id: number;
  key: string;
  value: string;
  label: string;
  description: string;
}

export interface Shift {
  id: number;
  cashier: number;
  cashier_name: string;
  opened_at: string;
  closed_at: string | null;
  opening_float_paise: number;
  closing_cash_paise: number | null;
  closing_notes: string;
  notes: string;
  is_open: boolean;
}

export interface ShiftReconciliation {
  opening_float_paise: number;
  cash_sales_total_paise: number;
  expected_cash_paise: number;
  total_sales: number;
  total_revenue_paise: number;
}

export interface ShiftCloseResult {
  shift: Shift;
  summary: {
    opening_float_paise: number;
    cash_sales_total_paise: number;
    expected_cash_paise: number;
    actual_cash_paise: number;
    variance_paise: number;
    total_sales: number;
    total_revenue_paise: number;
  };
}

export interface DailySummary {
  date: string;
  transaction_count: number;
  total_revenue_paise: number;
  total_discount_paise: number;
  payment_breakdown: Record<string, { total_paise: number; count: number }>;
  top_products: Array<{
    product__sku: string;
    product__name: string;
    qty_sold: string;
    revenue_paise: number;
  }>;
}

export interface DateRangeSummary {
  start: string;
  end: string;
  transaction_count: number;
  total_revenue_paise: number;
  total_discount_paise: number;
  daily_breakdown: Array<{
    date: string;
    revenue_paise: number;
    count: number;
  }>;
}

export interface InventoryValuation {
  products: Array<{
    sku: string;
    name: string;
    stock_qty: string;
    cost_price_paise: number;
    sell_price_paise: number;
    cost_value_paise: number;
    sell_value_paise: number;
  }>;
  total_cost_value_paise: number;
  total_sell_value_paise: number;
  potential_profit_paise: number;
}