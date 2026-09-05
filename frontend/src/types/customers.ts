export type CustomerGender = "M" | "F" | "O";

export interface Customer {
  id: number;
  name: string;
  phone: string | null;
  gender: CustomerGender;
  notes: string;
  display_name: string;
  total_sales: number;
  total_revenue_paise: number;
  outstanding_paise: number; // Khata / credit balance
  /** Per-customer ceiling. null = fall back to the shop default. 0 = no credit. */
  credit_limit_paise: number | null;
  /** The limit actually in force. null = unlimited. */
  effective_credit_limit_paise: number | null;
  /** How much more may go on khata. null = unlimited. */
  available_credit_paise: number | null;
  days_overdue: number | null; // Days since the oldest unpaid credit charge
  created_at: string;
}

export interface PaymentReceived {
  id: number;
  customer: number;
  amount_paise: number;
  received_date: string;
  notes: string;
  received_by: number;
  received_by_name: string;
}

export type LedgerKind =
  | "sale"
  | "payment"
  | "return"
  | "void"
  | "adjustment"
  | "opening";

export interface CreditLedgerEntry {
  id: number;
  kind: LedgerKind;
  kind_display: string;
  /** Positive = customer owes more. Negative = customer owes less. */
  delta_paise: number;
  balance_after_paise: number;
  note: string;
  sale: string | null;
  sale_number: string | null;
  payment: number | null;
  created_by_name: string;
  created_at: string;
}

export interface KhataCreditSale {
  id: string;
  sale_number: string;
  created_at: string;
  total_paise: number;
  item_count: number;
  status: string;
}

export interface KhataSummary {
  outstanding_paise: number;
  ledger_balance_paise: number;
  total_charged_paise: number;
  total_paid_paise: number;
  total_reversed_paise: number;
  credit_sale_count: number;
  payment_count: number;
  first_credit_at: string | null;
  last_payment_at: string | null;
  last_payment_paise: number;
  is_reconciled: boolean;
  days_since_first_credit: number | null;
}

export interface KhataDetail {
  customer: Customer;
  summary: KhataSummary;
  ledger: CreditLedgerEntry[];
  credit_sales: KhataCreditSale[];
  payments: PaymentReceived[];
}

export interface KhataReport {
  current: Customer[];
  days_30: Customer[];
  days_60: Customer[];
  days_90_plus: Customer[];
  total_outstanding_paise: number;
  customer_count: number;
  /** Collection insights over the trailing 30 days */
  collected_30d_paise: number;
  charged_30d_paise: number;
  net_30d_paise: number;
  largest_balance_paise: number;
  largest_balance_name: string | null;
  oldest_credit_days: number | null;
}
