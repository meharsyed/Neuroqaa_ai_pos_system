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
  outstanding_paise: number;  // Khata / credit balance
  days_overdue: number | null;  // Days since first unpaid credit sale
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

export interface KhataReport {
  current: Customer[];
  days_30: Customer[];
  days_60: Customer[];
  days_90_plus: Customer[];
  total_outstanding_paise: number;
}