from decimal import Decimal
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, field_validator
from app.core.decimal_math import to_decimal, format_decimal

class ProjectionUpdateItem(BaseModel):
    account_id: int
    month: int = Field(..., ge=1, le=12, description="Mes del 1 al 12")
    amount: Decimal = Field(..., ge=Decimal("0.00"), description="Importe proyectado, no negativo")

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v):
        dec = to_decimal(v)
        if dec < Decimal("0.00"):
            raise ValueError("El importe proyectado debe ser mayor o igual a 0.00")
        return dec

class BudgetUpdateRequest(BaseModel):
    modified_by: str = Field("Usuario", min_length=1, max_length=100)
    reason: Optional[str] = Field(None, max_length=500)
    updates: List[ProjectionUpdateItem] = Field(..., min_length=1)

class AccountMatrixItem(BaseModel):
    id: int
    code: str
    name: str
    responsible: str
    provider: str
    display_order: int
    months: Dict[int, str]      # Mes 1..12 -> string decimal exacto "0.00"
    annual_total: str           # Suma 12 meses

class CategoryMatrixItem(BaseModel):
    id: int
    code: str
    name: str
    display_order: int
    accounts: List[AccountMatrixItem]
    monthly_totals: Dict[int, str]  # Total mensual por categoría (1..12)
    annual_total: str               # Total anual por categoría

class BudgetMatrixResponse(BaseModel):
    year: int
    status: str
    notes: Optional[str]
    categories: List[CategoryMatrixItem]
    general_monthly_totals: Dict[int, str]  # Total mensual general (1..12)
    general_annual_total: str               # Total anual general
    is_balanced: bool                       # Verificación de cuadre horizontal vs vertical
