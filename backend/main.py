import os
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import init_db, get_db, SessionLocal, Category, Account, MonthlyExpense
from schemas import (
    CategoryCreate, CategoryOut,
    AccountCreate, AccountUpdate, AccountOut,
    ExpenseBulkUpdateRequest,
    BudgetSummary, to_money_decimal
)
from calculator import calculate_budget_summary

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar tablas y ejecutar auto-migración
    init_db()
    # Si la base está vacía, agregar un ejemplo mínimo para comenzar
    with SessionLocal() as db:
        if db.query(Category).count() == 0:
            c1 = Category(name="Servicios Tecnológicos")
            db.add(c1)
            db.flush()
            a1 = Account(category_id=c1.id, name="Servidores en la Nube", provider="Cirion / AWS")
            a2 = Account(category_id=c1.id, name="Conectividad e Internet", provider="Celerity / Claro")
            db.add_all([a1, a2])
            db.commit()
    yield

app = FastAPI(
    title="Planificador de Presupuesto - Categorías, Cuentas y Gastos Mensuales",
    description="API para gestionar la estructura jerárquica de presupuesto y registrar gastos mensuales con cálculo automático de totales.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. GESTIÓN DE CATEGORÍAS ---
@app.get("/api/categories", response_model=List[CategoryOut], tags=["Categorías"])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.id).all()

@app.post("/api/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED, tags=["Categorías"])
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    name_clean = payload.name.strip()
    existing = db.query(Category).filter(Category.name.ilike(name_clean)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"La categoría '{name_clean}' ya existe.")
    
    cat = Category(name=name_clean)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@app.put("/api/categories/{category_id}", response_model=CategoryOut, tags=["Categorías"])
def update_category(category_id: int, payload: CategoryCreate, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")
    name_clean = payload.name.strip()
    existing = db.query(Category).filter(Category.name.ilike(name_clean), Category.id != category_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe otra categoría llamada '{name_clean}'.")
    cat.name = name_clean
    db.commit()
    db.refresh(cat)
    return cat

@app.delete("/api/categories/{category_id}", tags=["Categorías"])
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")
    db.delete(cat)
    db.commit()
    return {"message": f"Categoría '{cat.name}' eliminada correctamente."}

# --- 2. GESTIÓN DE CUENTAS DENTRO DE CATEGORÍAS ---
@app.post("/api/categories/{category_id}/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED, tags=["Cuentas"])
def create_account_in_category(category_id: int, payload: AccountCreate, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="La categoría especificada no existe.")
    
    name_clean = payload.name.strip()
    existing = db.query(Account).filter(Account.category_id == category_id, Account.name.ilike(name_clean)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe una cuenta llamada '{name_clean}' en esta categoría.")

    provider_clean = payload.provider.strip() if payload.provider else ""
    acc = Account(category_id=category_id, name=name_clean, provider=provider_clean)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

@app.put("/api/accounts/{account_id}", response_model=AccountOut, tags=["Cuentas"])
def update_account(account_id: int, payload: AccountUpdate, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    acc.name = payload.name.strip()
    if payload.provider is not None:
        acc.provider = payload.provider.strip()
    if payload.category_id is not None and payload.category_id != acc.category_id:
        cat = db.query(Category).filter(Category.id == payload.category_id).first()
        if not cat:
            raise HTTPException(status_code=404, detail="La categoría de destino no existe.")
        acc.category_id = payload.category_id
    db.commit()
    db.refresh(acc)
    return acc

@app.delete("/api/accounts/{account_id}", tags=["Cuentas"])
def delete_account(account_id: int, db: Session = Depends(get_db)):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
    db.delete(acc)
    db.commit()
    return {"message": f"Cuenta '{acc.name}' eliminada correctamente."}

# --- 3. REGISTRO DE GASTOS MENSUALES ---
@app.put("/api/expenses", tags=["Gastos Mensuales"])
def update_monthly_expenses(payload: ExpenseBulkUpdateRequest, db: Session = Depends(get_db)):
    """
    Registra o actualiza importes para cuentas en meses específicos (1 a 12).
    """
    for item in payload.updates:
        # Verificar que la cuenta exista
        acc = db.query(Account).filter(Account.id == item.account_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail=f"Cuenta ID {item.account_id} no encontrada.")

        expense = db.query(MonthlyExpense).filter(
            MonthlyExpense.account_id == item.account_id,
            MonthlyExpense.month == item.month
        ).first()

        clean_amount = to_money_decimal(item.amount)

        if expense:
            expense.amount = clean_amount
        else:
            expense = MonthlyExpense(
                account_id=item.account_id,
                month=item.month,
                amount=clean_amount
            )
            db.add(expense)

    db.commit()
    return calculate_budget_summary(db)

# --- 4. RESUMEN COMPLETO Y TOTALES CALCULADOS ---
@app.get("/api/budget-summary", response_model=BudgetSummary, tags=["Presupuesto"])
def get_budget_summary(db: Session = Depends(get_db)):
    """
    Retorna la estructura jerárquica completa y los 6 totales calculados automáticamente:
    1. Total mensual de cada cuenta
    2. Total anual de cada cuenta
    3. Total mensual de cada categoría
    4. Total anual de cada categoría
    5. Total mensual general
    6. Total anual general
    """
    try:
        return calculate_budget_summary(db)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al calcular resumen: {str(e)}")

# --- Servir Interfaz Web Estática ---
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Planificador de Presupuesto API activa. Visite /docs"}
