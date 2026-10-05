from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Union
from pydantic import BaseModel, Field, field_validator

def to_money_decimal(val) -> Decimal:
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        d = val
    else:
        try:
            d = Decimal(str(val).strip().replace(',', '.'))
        except Exception:
            return Decimal("0.00")
    if d < Decimal("0.00"):
        return Decimal("0.00")
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def format_money(val: Decimal) -> str:
    if val is None:
        return "0.00"
    if not isinstance(val, Decimal):
        val = to_money_decimal(val)
    return str(val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

# =========================================================================
# EMPRESAS
# =========================================================================
class CompanyCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=150)
    trade_name: Optional[str] = Field("", max_length=150)
    tax_id: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field("ACTIVO", max_length=20)

class CompanyUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    trade_name: Optional[str] = None
    tax_id: Optional[str] = None
    status: Optional[str] = None

class CompanyOut(BaseModel):
    id: int
    code: str
    name: str
    trade_name: Optional[str] = ""
    tax_id: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# =========================================================================
# CATEGORÍAS
# =========================================================================
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field("", max_length=50)
    company_id: Optional[int] = None

class CategoryOut(BaseModel):
    id: int
    company_id: int
    code: Optional[str] = ""
    name: str

    class Config:
        from_attributes = True

# =========================================================================
# CUENTAS
# =========================================================================
class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    code: Optional[str] = Field("", max_length=50)
    provider: Optional[str] = Field("", max_length=150)

class AccountUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    code: Optional[str] = Field("", max_length=50)
    provider: Optional[str] = Field("", max_length=150)
    category_id: Optional[int] = None
    is_active: Optional[bool] = None

class AccountOut(BaseModel):
    id: int
    category_id: int
    code: Optional[str] = ""
    name: str
    provider: Optional[str] = ""
    is_active: bool = True

    class Config:
        from_attributes = True

# =========================================================================
# GASTOS MENSUALES
# =========================================================================
class ExpenseItemUpdate(BaseModel):
    account_id: int
    year: Optional[int] = 2026
    month: int = Field(..., ge=1, le=12)
    amount: Decimal = Field(..., ge=Decimal("0.00"))

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v):
        return to_money_decimal(v)

class ExpenseBulkUpdateRequest(BaseModel):
    updates: List[ExpenseItemUpdate]
    username: Optional[str] = "system"

# =========================================================================
# ESTRUCTURA JERÁRQUICA CON TOTALES CALCULADOS
# =========================================================================
class AccountSummary(BaseModel):
    id: int
    category_id: int = 0
    code: Optional[str] = ""
    name: str
    provider: Optional[str] = ""
    is_active: bool = True
    months: Dict[Union[int, str], str]        # Mes 1..12 -> string decimal exacto
    annual_total: str                         # Total anual de la cuenta

class CategorySummary(BaseModel):
    id: int
    company_id: int = 0
    code: Optional[str] = ""
    name: str
    accounts: List[AccountSummary]
    monthly_totals: Dict[Union[int, str], str] # Total mensual de la categoría
    annual_total: str                          # Total anual de la categoría

class BudgetSummary(BaseModel):
    company_id: int = 1
    company_code: str = ""
    company_name: str = ""
    year: int = 2026
    categories: List[CategorySummary]
    general_monthly_totals: Dict[Union[int, str], str] # Total mensual general de la empresa
    general_annual_total: str                          # Total anual general de la empresa
    is_balanced: bool                                  # Verificación cuadre cruzado

# =========================================================================
# CONSOLIDACIÓN CORPORATIVA MULTIEMPRESA (SPRINT 3)
# =========================================================================
class CorporateCompanyBreakdown(BaseModel):
    company_id: int
    company_code: str
    company_name: str
    monthly_totals: Dict[Union[int, str], str]
    annual_total: str
    percentage_share: str

class CorporateConsolidationOut(BaseModel):
    year: int
    selected_company_ids: List[int]
    companies_breakdown: List[CorporateCompanyBreakdown]
    consolidated_monthly_totals: Dict[Union[int, str], str]
    total_annual: str
    is_balanced: bool
    companies_count: int

# =========================================================================
# DASHBOARD Y COMPARACIÓN
# =========================================================================
class ComparisonCategoryRow(BaseModel):
    category_id: int
    category_name: str
    base_annual: str
    projected_annual: str
    variation_amount: str
    variation_pct: str

class ComparisonTotal(BaseModel):
    base_annual: str
    projected_annual: str
    variation_amount: str
    variation_pct: str

class BudgetComparisonOut(BaseModel):
    projected_year: int
    base_year: int
    has_sufficient_data: bool
    message: Optional[str] = None
    rows: List[ComparisonCategoryRow]
    total: ComparisonTotal

class DashboardDataOut(BaseModel):
    company_id: int
    company_code: str
    company_name: str
    year: int
    base_year: int
    budget_summary: BudgetSummary
    comparison: BudgetComparisonOut
    available_years: List[int]

# =========================================================================
# USUARIOS, ROLES Y AUDITORÍA
# =========================================================================
class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = ""
    is_superuser: bool

    class Config:
        from_attributes = True

class UserCompanyRoleOut(BaseModel):
    company_id: int
    company_code: str
    company_name: str
    role: str

class AuditLogOut(BaseModel):
    id: int
    company_id: Optional[int]
    username: str
    action: str
    year: int
    category_name: Optional[str]
    account_name: Optional[str]
    month: Optional[int]
    old_amount: str
    new_amount: str
    created_at: datetime
