export interface AccountMatrixItem {
  id: number;
  code: string;
  name: string;
  responsible: string;
  provider: string;
  display_order: number;
  months: { [month: number]: string };
  annual_total: string;
}

export interface CategoryMatrixItem {
  id: number;
  code: string;
  name: string;
  display_order: number;
  accounts: AccountMatrixItem[];
  monthly_totals: { [month: number]: string };
  annual_total: string;
}

export interface BudgetMatrix {
  year: number;
  status: 'DRAFT' | 'APPROVED' | 'CLOSED';
  notes?: string;
  categories: CategoryMatrixItem[];
  general_monthly_totals: { [month: number]: string };
  general_annual_total: string;
  is_balanced: boolean;
}

export interface BudgetYear {
  year: number;
  status: 'DRAFT' | 'APPROVED' | 'CLOSED';
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface AuditLogItem {
  id: number;
  year: number;
  account_id: number;
  account_code: string;
  account_name: string;
  category_name: string;
  month: number;
  previous_amount: string;
  new_amount: string;
  modified_by: string;
  reason?: string;
  created_at: string;
}

export interface ProjectionUpdate {
  account_id: number;
  month: number;
  amount: string;
}
