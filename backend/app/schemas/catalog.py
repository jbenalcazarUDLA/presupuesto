from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# --- Categoría ---
class CategoryBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    display_order: int = 0
    is_active: bool = True

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Cuenta ---
class AccountBase(BaseModel):
    category_id: int
    code: str = Field("", max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    responsible: str = Field("", max_length=100)
    provider: str = Field("", max_length=150)
    display_order: int = 0
    is_active: bool = True

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    category_id: Optional[int] = None
    code: Optional[str] = None
    name: Optional[str] = None
    responsible: Optional[str] = None
    provider: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

class AccountResponse(AccountBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Año Presupuestario ---
class BudgetYearCreate(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    notes: Optional[str] = None
    copy_from_year: Optional[int] = None  # Si se especifica, clona cuentas y/o valores

class BudgetYearResponse(BaseModel):
    year: int
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
