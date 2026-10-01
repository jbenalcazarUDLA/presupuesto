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

# --- Creación de Categorías ---
class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class CategoryOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

# --- Creación de Cuentas ---
class AccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    provider: Optional[str] = Field("", max_length=150)

class AccountUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    provider: Optional[str] = Field("", max_length=150)
    category_id: Optional[int] = None

class AccountOut(BaseModel):
    id: int
    category_id: int
    name: str
    provider: Optional[str] = ""

    class Config:
        from_attributes = True

# --- Registro de Gastos Mensuales ---
class ExpenseItemUpdate(BaseModel):
    account_id: int
    month: int = Field(..., ge=1, le=12)
    amount: Decimal = Field(..., ge=Decimal("0.00"))

    @field_validator("amount", mode="before")
    @classmethod
    def parse_amount(cls, v):
        return to_money_decimal(v)

class ExpenseBulkUpdateRequest(BaseModel):
    updates: List[ExpenseItemUpdate]

# --- Estructura Jerárquica con Totales Calculados ---
class AccountSummary(BaseModel):
    id: int
    category_id: int = 0
    name: str
    provider: Optional[str] = ""
    months: Dict[Union[int, str], str]        # Mes 1..12 -> string decimal exacto
    annual_total: str                         # 2. Total anual de cada cuenta

class CategorySummary(BaseModel):
    id: int
    name: str
    accounts: List[AccountSummary]
    monthly_totals: Dict[Union[int, str], str] # 3. Total mensual de cada categoría
    annual_total: str                          # 4. Total anual de cada categoría

class BudgetSummary(BaseModel):
    categories: List[CategorySummary]
    general_monthly_totals: Dict[Union[int, str], str] # 5. Total mensual general
    general_annual_total: str                          # 6. Total anual general
    is_balanced: bool                                  # Verificación cuadre cruzado
