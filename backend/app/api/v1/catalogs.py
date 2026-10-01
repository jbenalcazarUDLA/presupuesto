from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.budget_year import BudgetYear
from app.models.category import Category
from app.models.account import Account
from app.models.projection import BudgetMonthlyProjection
from app.schemas.catalog import (
    BudgetYearCreate, BudgetYearResponse,
    CategoryCreate, CategoryUpdate, CategoryResponse,
    AccountCreate, AccountUpdate, AccountResponse
)

router = APIRouter()

# --- Años Presupuestarios ---
@router.get("/years", response_model=List[BudgetYearResponse], summary="Listar años presupuestarios")
def get_years(db: Session = Depends(get_db)):
    years = db.query(BudgetYear).order_by(BudgetYear.year.desc()).all()
    return years

@router.post("/years", response_model=BudgetYearResponse, status_code=status.HTTP_201_CREATED, summary="Crear o inicializar un nuevo año fiscal")
def create_year(payload: BudgetYearCreate, db: Session = Depends(get_db)):
    existing = db.query(BudgetYear).filter(BudgetYear.year == payload.year).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"El año fiscal {payload.year} ya existe.")

    by = BudgetYear(year=payload.year, status="DRAFT", notes=payload.notes or f"Presupuesto {payload.year}")
    db.add(by)
    db.flush()

    # Si se solicitó copiar de un año previo (clonación de proyecciones base)
    if payload.copy_from_year:
        prev_projections = db.query(BudgetMonthlyProjection).filter(
            BudgetMonthlyProjection.year == payload.copy_from_year
        ).all()
        for p in prev_projections:
            cloned = BudgetMonthlyProjection(
                year=payload.year,
                account_id=p.account_id,
                month=p.month,
                amount=p.amount
            )
            db.add(cloned)

    db.commit()
    db.refresh(by)
    return by

# --- Categorías ---
@router.get("/categories", summary="Listar todas las categorías con sus cuentas")
def get_categories(active_only: bool = True, db: Session = Depends(get_db)):
    query = db.query(Category)
    if active_only:
        query = query.filter(Category.is_active == True)
    cats = query.order_by(Category.display_order, Category.id).all()
    
    result = []
    for c in cats:
        accs = [
            {
                "id": a.id,
                "category_id": a.category_id,
                "code": a.code,
                "name": a.name,
                "responsible": a.responsible,
                "provider": a.provider,
                "display_order": a.display_order,
                "is_active": a.is_active,
                "created_at": a.created_at
            }
            for a in c.accounts if (not active_only or a.is_active)
        ]
        result.append({
            "id": c.id,
            "code": c.code,
            "name": c.name,
            "display_order": c.display_order,
            "is_active": c.is_active,
            "created_at": c.created_at,
            "accounts": accs
        })
    return result

@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED, summary="Crear una nueva categoría dinámica")
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.code == payload.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe una categoría con código {payload.code}")
    
    cat = Category(
        code=payload.code,
        name=payload.name,
        display_order=payload.display_order,
        is_active=payload.is_active
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@router.put("/categories/{category_id}", response_model=CategoryResponse, summary="Actualizar categoría")
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    if payload.name is not None:
        cat.name = payload.name
    if payload.display_order is not None:
        cat.display_order = payload.display_order
    if payload.is_active is not None:
        cat.is_active = payload.is_active

    db.commit()
    db.refresh(cat)
    return cat

# --- Cuentas ---
@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED, summary="Crear una nueva cuenta presupuestaria dinámica")
def create_account(payload: AccountCreate, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == payload.category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="La categoría especificada no existe")
    
    acc = Account(
        category_id=payload.category_id,
        code=payload.code,
        name=payload.name,
        responsible=payload.responsible,
        provider=payload.provider,
        display_order=payload.display_order,
        is_active=payload.is_active
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

@router.put("/accounts/{account_id}", response_model=AccountResponse, summary="Actualizar cuenta presupuestaria")
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    if payload.category_id is not None:
        cat = db.query(Category).filter(Category.id == payload.category_id).first()
        if not cat:
            raise HTTPException(status_code=404, detail="La categoría especificada no existe")
        acc.category_id = payload.category_id

    if payload.code is not None:
        acc.code = payload.code
    if payload.name is not None:
        acc.name = payload.name
    if payload.responsible is not None:
        acc.responsible = payload.responsible
    if payload.provider is not None:
        acc.provider = payload.provider
    if payload.display_order is not None:
        acc.display_order = payload.display_order
    if payload.is_active is not None:
        acc.is_active = payload.is_active

    db.commit()
    db.refresh(acc)
    return acc
