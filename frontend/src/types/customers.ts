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
  created_at: string;
}