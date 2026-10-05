import os
import io
from contextlib import asynccontextmanager
from typing import List, Optional
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Header, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from database import (
    init_db, get_db, SessionLocal,
    Company, Category, Account, MonthlyExpense,
    User, UserCompanyRole, AuditLog
)
from schemas import (
    CompanyCreate, CompanyUpdate, CompanyOut,
    CategoryCreate, CategoryOut,
    AccountCreate, AccountUpdate, AccountOut,
    ExpenseBulkUpdateRequest,
    BudgetSummary, to_money_decimal, format_money,
    BudgetComparisonOut, DashboardDataOut,
    CorporateConsolidationOut, AuditLogOut, UserOut
)
from calculator import (
    calculate_budget_summary,
    calculate_budget_comparison,
    calculate_corporate_consolidation
)

def replicate_structure_from_edimca(db: Session, target_company_id: int, source_company_code: str = "EDIMCA") -> dict:
    """
    Replica todas las categorías y cuentas de la empresa plantilla (EDIMCA por defecto)
    hacia la empresa destino.
    Garantía Base 0: Se replica únicamente la estructura de cuentas y categorías,
    sin copiar montos ni valores presupuestarios (el presupuesto inicia en $0.00).
    Es idempotente: si la categoría o cuenta ya existe en la empresa destino, no la duplica.
    """
    source_comp = db.query(Company).filter(Company.code == source_company_code).first()
    if not source_comp:
        source_comp = db.query(Company).order_by(Company.id).first()

    if not source_comp or source_comp.id == target_company_id:
        return {"categories_created": 0, "accounts_created": 0}

    source_categories = db.query(Category).filter(Category.company_id == source_comp.id).all()
    categories_created = 0
    accounts_created = 0

    for src_cat in source_categories:
        # Buscar si ya existe la categoría con este nombre en la empresa destino
        tgt_cat = db.query(Category).filter(
            Category.company_id == target_company_id,
            Category.name == src_cat.name
        ).first()

        if not tgt_cat:
            tgt_cat = Category(
                company_id=target_company_id,
                code=src_cat.code or "",
                name=src_cat.name
            )
            db.add(tgt_cat)
            db.flush()
            categories_created += 1

        # Replicar cuentas pertenecientes a la categoría
        for src_acc in src_cat.accounts:
            tgt_acc = db.query(Account).filter(
                Account.category_id == tgt_cat.id,
                Account.name == src_acc.name
            ).first()

            if not tgt_acc:
                tgt_acc = Account(
                    category_id=tgt_cat.id,
                    code=src_acc.code or "",
                    name=src_acc.name,
                    provider=src_acc.provider or "",
                    is_active=src_acc.is_active
                )
                db.add(tgt_acc)
                accounts_created += 1

    db.commit()
    return {"categories_created": categories_created, "accounts_created": accounts_created}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inicializar tablas y ejecutar auto-migraciones
    init_db()

    # 2. Semillas iniciales si faltan datos
    with SessionLocal() as db:
        # Asegurar empresa EDIMCA con datos de ejemplo si está vacía
        edimca = db.query(Company).filter(Company.code == "EDIMCA").first()
        if edimca and db.query(Category).filter(Category.company_id == edimca.id).count() == 0:
            c1 = Category(company_id=edimca.id, name="Servicios Tecnológicos", code="TEC")
            c2 = Category(company_id=edimca.id, name="Operaciones y Mantenimiento", code="OPS")
            db.add_all([c1, c2])
            db.flush()

            a1 = Account(category_id=c1.id, name="Servidores Cloud AWS", provider="Cirion / AWS", code="510101")
            a2 = Account(category_id=c1.id, name="Enlaces de Fibra Óptica", provider="Telconet", code="510102")
            a3 = Account(category_id=c2.id, name="Seguridad Física Integral", provider="Seguritas", code="520101")
            db.add_all([a1, a2, a3])
            db.commit()

        # Semilla para PANELAT (segunda empresa para pruebas de aislamiento y consolidación)
        panelat = db.query(Company).filter(Company.code == "PANELAT").first()
        if panelat and db.query(Category).filter(Category.company_id == panelat.id).count() == 0:
            cp1 = Category(company_id=panelat.id, name="Servicios Tecnológicos", code="TEC") # Mismo nombre válido
            cp2 = Category(company_id=panelat.id, name="Producción y Planta", code="PROD")
            db.add_all([cp1, cp2])
            db.flush()

            ap1 = Account(category_id=cp1.id, name="Servidores Cloud AWS", provider="Amazon AWS", code="510101")
            ap2 = Account(category_id=cp2.id, name="Energía Eléctrica Planta", provider="Empresa Eléctrica", code="530101")
            db.add_all([ap1, ap2])
            db.commit()

        # 3. Replicar estructura de categorías y cuentas de EDIMCA a todas las demás empresas existentes
        if edimca:
            other_companies = db.query(Company).filter(Company.id != edimca.id).all()
            for other_comp in other_companies:
                replicate_structure_from_edimca(db, other_comp.id, source_company_code="EDIMCA")

    yield

app = FastAPI(
    title="Sistema Presupuestario Multiempresa y Consolidación Corporativa",
    description="Gestión presupuestaria con aislamiento total por empresa (Base 0), consolidación ejecutiva corporativa y cálculo automático de totales.",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# SEGURIDAD Y CONTROL DE AISLAMIENTO POR EMPRESA (Secciones 14, 15 y 16)
# =========================================================================
def get_current_user(x_user: Optional[str] = Header("admin"), db: Session = Depends(get_db)) -> User:
    username = (x_user or "admin").strip().lower()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        # Modo permisivo de desarrollo: crear o buscar admin por defecto
        user = db.query(User).filter(User.is_superuser == True).first()
        if not user:
            user = User(username="admin", email="admin@corporativo.com", full_name="Administrador", is_superuser=True)
            db.add(user)
            db.commit()
            db.refresh(user)
    return user

def verify_company_access(company_id: int, user: User, db: Session, required_role: str = "CONSULTA"):
    """
    Valida en backend que el usuario tenga autorización expresa sobre la empresa solicitada.
    Impide acceso indebido manipulando el ID en peticiones de API.
    """
    if user.is_superuser:
        return True

    role_entry = db.query(UserCompanyRole).filter(
        UserCompanyRole.user_id == user.id,
        UserCompanyRole.company_id == company_id
    ).first()

    if not role_entry:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acceso denegado: El usuario '{user.username}' no tiene permisos asignados para la empresa con ID {company_id}."
        )

    # Jerarquía de permisos: ADMINISTRADOR > PLANIFICADOR > CONSULTA
    role_hierarchy = {"ADMINISTRADOR": 3, "PLANIFICADOR": 2, "CONSULTA": 1}
    user_level = role_hierarchy.get(role_entry.role, 0)
    req_level = role_hierarchy.get(required_role, 1)

    if user_level < req_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permisos insuficientes: Se requiere rol {required_role}, pero su rol actual es {role_entry.role}."
        )

    return True

# =========================================================================
# 1. CATÁLOGO DE EMPRESAS (Sección 3)
# =========================================================================
@app.get("/api/companies", response_model=List[CompanyOut], tags=["Empresas"])
def list_companies(
    status_filter: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Company)
    if status_filter:
        query = query.filter(Company.status == status_filter)
    
    # Si no es superusuario, listar solo las empresas autorizadas
    if not user.is_superuser:
        allowed_ids = [r.company_id for r in user.roles]
        query = query.filter(Company.id.in_(allowed_ids))

    return query.order_by(Company.id).all()

@app.post("/api/companies", response_model=CompanyOut, status_code=status.HTTP_201_CREATED, tags=["Empresas"])
def create_company(
    payload: CompanyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Solo los administradores pueden crear empresas.")

    code_clean = payload.code.strip().upper()
    name_clean = payload.name.strip()

    if db.query(Company).filter(Company.code == code_clean).first():
        raise HTTPException(status_code=400, detail=f"El código de empresa '{code_clean}' ya está en uso.")

    if payload.tax_id:
        tax_clean = payload.tax_id.strip()
        if db.query(Company).filter(Company.tax_id == tax_clean).first():
            raise HTTPException(status_code=400, detail=f"La identificación tributaria/RUC '{tax_clean}' ya está registrada.")
    else:
        tax_clean = None

    company = Company(
        code=code_clean,
        name=name_clean,
        trade_name=payload.trade_name.strip() if payload.trade_name else name_clean,
        tax_id=tax_clean,
        status="ACTIVO"
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # Replicar automáticamente categorías y cuentas base de EDIMCA a la nueva empresa (Base 0)
    replicate_structure_from_edimca(db, company.id, source_company_code="EDIMCA")

    # Asignar rol de administrador al usuario creador
    if user:
        existing_role = db.query(UserCompanyRole).filter(
            UserCompanyRole.user_id == user.id,
            UserCompanyRole.company_id == company.id
        ).first()
        if not existing_role:
            db.add(UserCompanyRole(user_id=user.id, company_id=company.id, role="ADMINISTRADOR"))

        # Registro de auditoría
        audit = AuditLog(
            company_id=company.id,
            user_id=user.id,
            username=user.username,
            action="CREATE_COMPANY",
            year=2026,
            category_name="Catálogo Corporativo",
            account_name=company.name
        )
        db.add(audit)
        db.commit()

    return company

@app.post("/api/companies/{company_id}/replicate-from-edimca", tags=["Empresas"])
def replicate_company_structure_from_edimca(
    company_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_company_access(company_id, user, db, required_role="ADMINISTRADOR")
    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")

    res = replicate_structure_from_edimca(db, company_id, source_company_code="EDIMCA")
    return {
        "message": f"Estructura base de EDIMCA replicada a '{comp.name}'.",
        "categories_created": res["categories_created"],
        "accounts_created": res["accounts_created"]
    }

@app.post("/api/companies/replicate-base-structure", tags=["Empresas"])
def replicate_all_companies_from_edimca(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Solo administradores pueden ejecutar la replicación corporativa masiva.")

    edimca = db.query(Company).filter(Company.code == "EDIMCA").first()
    if not edimca:
        raise HTTPException(status_code=404, detail="No se encontró la empresa base EDIMCA.")

    other_comps = db.query(Company).filter(Company.id != edimca.id).all()
    total_cats = 0
    total_accs = 0
    for comp in other_comps:
        res = replicate_structure_from_edimca(db, comp.id, source_company_code="EDIMCA")
        total_cats += res["categories_created"]
        total_accs += res["accounts_created"]

    return {
        "message": f"Estructura base de EDIMCA replicada a {len(other_comps)} empresas.",
        "total_categories_created": total_cats,
        "total_accounts_created": total_accs
    }

@app.put("/api/companies/{company_id}", response_model=CompanyOut, tags=["Empresas"])
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_company_access(company_id, user, db, required_role="ADMINISTRADOR")
    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")

    if payload.code is not None:
        code_clean = payload.code.strip().upper()
        if code_clean and code_clean != comp.code:
            existing_code = db.query(Company).filter(Company.code == code_clean, Company.id != company_id).first()
            if existing_code:
                raise HTTPException(status_code=400, detail=f"El código '{code_clean}' ya está en uso por otra empresa.")
            comp.code = code_clean

    if payload.name is not None:
        comp.name = payload.name.strip()
    if payload.trade_name is not None:
        comp.trade_name = payload.trade_name.strip()
    if payload.tax_id is not None:
        tax_clean = payload.tax_id.strip() if payload.tax_id else None
        if tax_clean:
            existing = db.query(Company).filter(Company.tax_id == tax_clean, Company.id != company_id).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"El RUC '{tax_clean}' ya pertenece a otra empresa.")
        comp.tax_id = tax_clean
    if payload.status is not None:
        comp.status = payload.status.upper()

    # Registro de auditoría
    audit = AuditLog(
        company_id=comp.id,
        user_id=user.id if user else None,
        username=user.username if user else "admin",
        action="UPDATE_COMPANY",
        year=2026,
        category_name="Catálogo Corporativo",
        account_name=comp.name
    )
    db.add(audit)

    db.commit()
    db.refresh(comp)
    return comp

@app.delete("/api/companies/{company_id}", tags=["Empresas"])
def delete_company(
    company_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_company_access(company_id, user, db, required_role="ADMINISTRADOR")
    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")

    # Regla: No eliminar físicamente una empresa que tenga información presupuestaria asociada
    category_ids = [c.id for c in comp.categories]
    account_ids = [a.id for a in db.query(Account).filter(Account.category_id.in_(category_ids)).all()] if category_ids else []
    
    has_expenses = False
    if account_ids:
        has_expenses = db.query(MonthlyExpense).filter(
            MonthlyExpense.account_id.in_(account_ids),
            MonthlyExpense.amount > Decimal("0.00")
        ).first() is not None

    if has_expenses:
        # Se aplica borrado lógico por integridad
        comp.status = "INACTIVO"
        db.commit()
        return {"message": f"La empresa '{comp.name}' tiene información presupuestaria activa. Se ha cambiado su estado a INACTIVO para preservar los datos históricos."}

    db.delete(comp)
    db.commit()
    return {"message": f"Empresa '{comp.name}' eliminada correctamente."}

# =========================================================================
# 2. CATEGORÍAS POR EMPRESA (Sección 4)
# =========================================================================
@app.get("/api/categories", response_model=List[CategoryOut], tags=["Categorías"])
def list_categories(
    company_id: int = Query(..., description="ID de la empresa contexto"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_company_access(company_id, user, db, required_role="CONSULTA")
    return db.query(Category).filter(Category.company_id == company_id).order_by(Category.id).all()

@app.post("/api/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED, tags=["Categorías"])
def create_category(
    payload: CategoryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    comp_id = payload.company_id if payload.company_id else 1
    verify_company_access(comp_id, user, db, required_role="PLANIFICADOR")

    comp = db.query(Company).filter(Company.id == comp_id).first()
    if not comp or comp.status != "ACTIVO":
        raise HTTPException(status_code=400, detail="No se puede crear categorías en una empresa inactiva o inexistente.")

    name_clean = payload.name.strip()
    # Unicidad evaluada dentro de la empresa
    existing = db.query(Category).filter(
        Category.company_id == comp_id,
        Category.name.ilike(name_clean)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe una categoría llamada '{name_clean}' en la empresa {comp.name}.")

    cat = Category(company_id=comp_id, name=name_clean, code=payload.code.strip() if payload.code else "")
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@app.put("/api/categories/{category_id}", response_model=CategoryOut, tags=["Categorías"])
def update_category(
    category_id: int,
    payload: CategoryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")

    verify_company_access(cat.company_id, user, db, required_role="PLANIFICADOR")

    name_clean = payload.name.strip()
    existing = db.query(Category).filter(
        Category.company_id == cat.company_id,
        Category.name.ilike(name_clean),
        Category.id != category_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe otra categoría llamada '{name_clean}' en esta empresa.")

    cat.name = name_clean
    if payload.code is not None:
        cat.code = payload.code.strip()
    db.commit()
    db.refresh(cat)
    return cat

@app.delete("/api/categories/{category_id}", tags=["Categorías"])
def delete_category(
    category_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada.")

    verify_company_access(cat.company_id, user, db, required_role="PLANIFICADOR")

    db.delete(cat)
    db.commit()
    return {"message": f"Categoría '{cat.name}' eliminada correctamente."}

# =========================================================================
# 3. CUENTAS POR CATEGORÍA Y EMPRESA (Sección 5)
# =========================================================================
@app.post("/api/categories/{category_id}/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED, tags=["Cuentas"])
def create_account_in_category(
    category_id: int,
    payload: AccountCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="La categoría especificada no existe.")

    verify_company_access(cat.company_id, user, db, required_role="PLANIFICADOR")

    name_clean = payload.name.strip()
    # Unicidad dentro de la categoría
    existing = db.query(Account).filter(Account.category_id == category_id, Account.name.ilike(name_clean)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe una cuenta llamada '{name_clean}' en esta categoría.")

    provider_clean = payload.provider.strip() if payload.provider else ""
    code_clean = payload.code.strip() if payload.code else ""

    acc = Account(
        category_id=category_id,
        name=name_clean,
        provider=provider_clean,
        code=code_clean,
        is_active=True
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc

@app.put("/api/accounts/{account_id}", response_model=AccountOut, tags=["Cuentas"])
def update_account(
    account_id: int,
    payload: AccountUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    verify_company_access(acc.category.company_id, user, db, required_role="PLANIFICADOR")

    acc.name = payload.name.strip()
    if payload.provider is not None:
        acc.provider = payload.provider.strip()
    if payload.code is not None:
        acc.code = payload.code.strip()
    if payload.is_active is not None:
        acc.is_active = payload.is_active

    if payload.category_id is not None and payload.category_id != acc.category_id:
        target_cat = db.query(Category).filter(Category.id == payload.category_id).first()
        if not target_cat:
            raise HTTPException(status_code=404, detail="Categoría de destino no existe.")
        if target_cat.company_id != acc.category.company_id:
            raise HTTPException(status_code=400, detail="No se puede transferir una cuenta a una categoría de otra empresa.")
        acc.category_id = payload.category_id

    db.commit()
    db.refresh(acc)
    return acc

@app.delete("/api/accounts/{account_id}", tags=["Cuentas"])
def delete_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    acc = db.query(Account).filter(Account.id == account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada.")

    verify_company_access(acc.category.company_id, user, db, required_role="PLANIFICADOR")

    db.delete(acc)
    db.commit()
    return {"message": f"Cuenta '{acc.name}' eliminada correctamente."}

# =========================================================================
# 4. REGISTRO DE GASTOS CON AUDITORÍA (Sección 6 y 17)
# =========================================================================
@app.put("/api/expenses", tags=["Gastos Mensuales"])
def update_monthly_expenses(
    payload: ExpenseBulkUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registra gastos mensuales garantizando aislamiento por empresa y guardando auditoría detallada:
    usuario, empresa, acción, año, categoría, cuenta, valor anterior, valor nuevo, fecha/hora.
    """
    if not payload.updates:
        return {"message": "No hay actualizaciones pendientes"}

    target_company_id = None
    target_year = 2026
    username = user.username if user else payload.username or "system"

    for item in payload.updates:
        acc = db.query(Account).filter(Account.id == item.account_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail=f"Cuenta ID {item.account_id} no encontrada.")

        comp_id = acc.category.company_id
        verify_company_access(comp_id, user, db, required_role="PLANIFICADOR")
        target_company_id = comp_id

        yr = item.year if item.year else 2026
        target_year = yr

        expense = db.query(MonthlyExpense).filter(
            MonthlyExpense.account_id == item.account_id,
            MonthlyExpense.year == yr,
            MonthlyExpense.month == item.month
        ).first()

        clean_amount = to_money_decimal(item.amount)
        old_val = expense.amount if expense else Decimal("0.00")

        if expense:
            expense.amount = clean_amount
        else:
            expense = MonthlyExpense(
                account_id=item.account_id,
                year=yr,
                month=item.month,
                amount=clean_amount
            )
            db.add(expense)

        # Registro de Auditoría (Sección 17)
        if old_val != clean_amount:
            audit = AuditLog(
                company_id=comp_id,
                user_id=user.id if user else None,
                username=username,
                action="UPDATE_EXPENSE",
                year=yr,
                category_name=acc.category.name,
                account_id=acc.id,
                account_name=acc.name,
                month=item.month,
                old_amount=old_val,
                new_amount=clean_amount
            )
            db.add(audit)

    db.commit()
    return calculate_budget_summary(db, company_id=target_company_id or 1, year=target_year)

# =========================================================================
# 5. RESUMEN Y DASHBOARD POR EMPRESA (Secciones 8 y 9)
# =========================================================================
@app.get("/api/budget-summary", response_model=BudgetSummary, tags=["Presupuesto"])
def get_budget_summary_endpoint(
    company_id: int = Query(1, description="ID de la empresa"),
    year: int = Query(2026, description="Año presupuestario"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_company_access(company_id, user, db, required_role="CONSULTA")
    return calculate_budget_summary(db, company_id=company_id, year=year)

@app.get("/api/budget-years", response_model=List[int], tags=["Presupuesto"])
def get_budget_years_endpoint(
    company_id: int = Query(1, description="ID de la empresa"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_company_access(company_id, user, db, required_role="CONSULTA")
    # Buscar años específicos que contengan gastos de cuentas de esta empresa
    cat_ids = [c.id for c in db.query(Category).filter(Category.company_id == company_id).all()]
    acc_ids = [a.id for a in db.query(Account).filter(Account.category_id.in_(cat_ids)).all()] if cat_ids else []
    
    years_db = []
    if acc_ids:
        years_db = [r[0] for r in db.query(MonthlyExpense.year).filter(
            MonthlyExpense.account_id.in_(acc_ids)
        ).distinct().all() if r[0] is not None]

    defaults = [2025, 2026, 2027]
    return sorted(list(set(defaults + years_db)))

@app.get("/api/dashboard", response_model=DashboardDataOut, tags=["Dashboard"])
def get_dashboard_data_endpoint(
    company_id: int = Query(1, description="ID de la empresa"),
    year: int = Query(2026, description="Año proyectado"),
    base_year: int = Query(2025, description="Año base"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_company_access(company_id, user, db, required_role="CONSULTA")
    comp = db.query(Company).filter(Company.id == company_id).first()
    comp_name = comp.name if comp else f"Empresa #{company_id}"
    comp_code = comp.code if comp else f"EMP{company_id}"

    budget_summary = calculate_budget_summary(db, company_id=company_id, year=year)
    comparison = calculate_budget_comparison(db, company_id=company_id, projected_year=year, base_year=base_year)

    # Años disponibles para esta empresa
    cat_ids = [c.id for c in db.query(Category).filter(Category.company_id == company_id).all()]
    acc_ids = [a.id for a in db.query(Account).filter(Account.category_id.in_(cat_ids)).all()] if cat_ids else []
    years_db = []
    if acc_ids:
        years_db = [r[0] for r in db.query(MonthlyExpense.year).filter(
            MonthlyExpense.account_id.in_(acc_ids)
        ).distinct().all() if r[0] is not None]

    defaults = [2025, 2026, 2027]
    available_years = sorted(list(set(defaults + years_db)))

    return {
        "company_id": company_id,
        "company_code": comp_code,
        "company_name": comp_name,
        "year": year,
        "base_year": base_year,
        "budget_summary": budget_summary,
        "comparison": comparison,
        "available_years": available_years
    }

# =========================================================================
# 6. CONSOLIDACIÓN CORPORATIVA MULTIEMPRESA (Secciones 10, 11, 20 y 21)
# =========================================================================
@app.get("/api/corporate/consolidation", response_model=CorporateConsolidationOut, tags=["Consolidado Corporativo"])
def get_corporate_consolidation_endpoint(
    company_ids: Optional[str] = Query(None, description="Lista de IDs de empresas separadas por coma (ej. 1,2,3)"),
    year: int = Query(2026, description="Año a consolidar"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna la vista agregada consolidada de las empresas seleccionadas calculada al vuelo sin duplicar datos.
    """
    if company_ids:
        try:
            ids_list = [int(x.strip()) for x in company_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de company_ids inválido.")
    else:
        # Todas las empresas activas
        active_comps = db.query(Company).filter(Company.status == "ACTIVO").all()
        ids_list = [c.id for c in active_comps]

    # Validar acceso de usuario a cada empresa solicitada (o filtrar las autorizadas)
    if not user.is_superuser:
        allowed_ids = set([r.company_id for r in user.roles])
        ids_list = [cid for cid in ids_list if cid in allowed_ids]

    if not ids_list:
        raise HTTPException(status_code=403, detail="No tiene permisos para consolidar ninguna de las empresas seleccionadas.")

    return calculate_corporate_consolidation(db, company_ids=ids_list, year=year)

# =========================================================================
# 7. REGISTRO DE AUDITORÍA (Sección 17)
# =========================================================================
@app.get("/api/audit-logs", response_model=List[AuditLogOut], tags=["Auditoría"])
def get_audit_logs(
    company_id: Optional[int] = None,
    year: Optional[int] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if company_id:
        verify_company_access(company_id, user, db, required_role="CONSULTA")
        query = query.filter(AuditLog.company_id == company_id)
    elif not user.is_superuser:
        allowed_ids = [r.company_id for r in user.roles]
        query = query.filter(AuditLog.company_id.in_(allowed_ids))

    if year:
        query = query.filter(AuditLog.year == year)

    return query.order_by(AuditLog.id.desc()).limit(limit).all()

# =========================================================================
# COPIAR PRESUPUESTO DE UN AÑO A OTRO (Utilidad de gestión)
# =========================================================================
@app.post("/api/companies/{company_id}/copy-year", tags=["Utilidades"])
def copy_budget_year(
    company_id: int,
    source_year: int = Query(..., description="Año origen (cuyos datos se copiarán)"),
    target_year: int = Query(..., description="Año destino (donde se escribirán los datos)"),
    overwrite: bool = Query(False, description="Si True, sobreescribe valores existentes en el año destino"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Copia todos los gastos mensuales de source_year → target_year para la empresa indicada.
    El año origen queda intacto.
    Si overwrite=False (defecto), no sobreescribe celdas que ya tengan valor en el año destino.
    Si overwrite=True, sobreescribe todos los valores del año destino con los del origen.
    """
    if source_year == target_year:
        raise HTTPException(status_code=400, detail="El año origen y el año destino no pueden ser el mismo.")

    verify_company_access(company_id, user, db, required_role="PLANIFICADOR")

    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")

    # Recoger todas las cuentas de la empresa
    categories = db.query(Category).filter(Category.company_id == company_id).all()
    account_ids = [acc.id for cat in categories for acc in cat.accounts]

    if not account_ids:
        raise HTTPException(status_code=404, detail="La empresa no tiene cuentas registradas.")

    # Gastos del año origen
    source_expenses = db.query(MonthlyExpense).filter(
        MonthlyExpense.account_id.in_(account_ids),
        MonthlyExpense.year == source_year
    ).all()

    if not source_expenses:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron gastos en el año {source_year} para la empresa '{comp.name}'."
        )

    # Mapa de gastos ya existentes en el año destino → (account_id, month): objeto
    existing_target = {
        (e.account_id, e.month): e
        for e in db.query(MonthlyExpense).filter(
            MonthlyExpense.account_id.in_(account_ids),
            MonthlyExpense.year == target_year
        ).all()
    }

    created = 0
    updated = 0
    skipped = 0

    for src in source_expenses:
        key = (src.account_id, src.month)
        existing = existing_target.get(key)

        if existing:
            if overwrite:
                existing.amount = src.amount
                updated += 1
            else:
                skipped += 1
        else:
            db.add(MonthlyExpense(
                account_id=src.account_id,
                year=target_year,
                month=src.month,
                amount=src.amount
            ))
            created += 1

    db.commit()

    # Registro de auditoría
    db.add(AuditLog(
        company_id=company_id,
        user_id=user.id if user else None,
        username=user.username if user else "admin",
        action="COPY_YEAR",
        year=target_year,
        category_name=f"Copia {source_year}→{target_year}",
        account_name=comp.name,
        old_amount=Decimal("0.00"),
        new_amount=Decimal("0.00")
    ))
    db.commit()

    return {
        "message": f"Presupuesto copiado de {source_year} → {target_year} para '{comp.name}'.",
        "company": comp.name,
        "source_year": source_year,
        "target_year": target_year,
        "records_created": created,
        "records_updated": updated,
        "records_skipped": skipped,
        "total_source_records": len(source_expenses)
    }

# =========================================================================
# 8. EXPORTACIÓN A EXCEL (openpyxl)
# =========================================================================
def _make_excel_response(wb, filename: str) -> StreamingResponse:
    """Convierte un Workbook de openpyxl en una StreamingResponse descargable."""
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition"
    }
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

def _build_budget_workbook(summary: dict, company_name: str, year: int):
    """
    Construye un workbook Excel con el presupuesto de una empresa:
      - Hoja 'Presupuesto': tabla completa con categorías, cuentas y 12 meses.
      - Hoja 'Resumen por Categoría': totales mensuales por categoría.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl no está instalado. Ejecuta: pip install openpyxl"
        )

    MONTH_NAMES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                   'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

    # ---------- Estilos ----------
    def thin_border():
        s = Side(style='thin', color='D1D5DB')
        return Border(left=s, right=s, top=s, bottom=s)

    TITLE_FONT   = Font(name='Calibri', bold=True, size=14, color='FFFFFF')
    HEADER_FONT  = Font(name='Calibri', bold=True, size=10, color='FFFFFF')
    CAT_FONT     = Font(name='Calibri', bold=True, size=10, color='1E293B')
    ACC_FONT     = Font(name='Calibri', size=10, color='374151')
    TOTAL_FONT   = Font(name='Calibri', bold=True, size=10, color='1E293B')
    MONEY_FMT    = '#,##0.00'

    BLUE_FILL    = PatternFill('solid', fgColor='3730A3')  # Indigo-800
    HEADER_FILL  = PatternFill('solid', fgColor='4F46E5')  # Indigo-600
    CAT_FILL     = PatternFill('solid', fgColor='E0E7FF')  # Indigo-100
    TOTAL_FILL   = PatternFill('solid', fgColor='C7D2FE')  # Indigo-200
    GRAND_FILL   = PatternFill('solid', fgColor='818CF8')  # Indigo-400
    WHITE_FILL   = PatternFill('solid', fgColor='FFFFFF')
    STRIPE_FILL  = PatternFill('solid', fgColor='F5F3FF')  # Indigo-50

    CENTER = Alignment(horizontal='center', vertical='center')
    RIGHT  = Alignment(horizontal='right',  vertical='center')
    LEFT   = Alignment(horizontal='left',   vertical='center')

    wb = openpyxl.Workbook()

    # ============================================================
    # HOJA 1: Presupuesto Detallado
    # ============================================================
    ws = wb.active
    ws.title = "Presupuesto Detallado"
    ws.freeze_panes = "D4"

    # --- Fila 1: Título principal ---
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=16)
    title_cell = ws.cell(1, 1, f"PRESUPUESTO {year} — {company_name.upper()}")
    title_cell.font     = TITLE_FONT
    title_cell.fill     = BLUE_FILL
    title_cell.alignment = CENTER

    # --- Fila 2: KPIs ---
    annual_total_str = summary.get('general_annual_total', '0.00')
    try:
        annual_total_val = float(annual_total_str.replace(',', ''))
    except Exception:
        annual_total_val = 0.0

    kpi_labels = [
        ("Total Anual", annual_total_val),
        ("Promedio Mensual", annual_total_val / 12),
        ("Categorías", len(summary.get('categories', []))),
    ]
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
    ws.cell(2, 1, f"Total Anual: ${annual_total_val:,.2f}").font = Font(bold=True, color='3730A3', size=11)

    # --- Fila 3: Cabeceras ---
    headers_row = 3
    col_headers = ['Proveedor', 'Categoría / Cuenta'] + MONTH_NAMES + ['Total Anual']
    col_widths  = [22, 38] + [13]*12 + [16]
    for ci, (hdr, w) in enumerate(zip(col_headers, col_widths), start=1):
        c = ws.cell(headers_row, ci, hdr)
        c.font      = HEADER_FONT
        c.fill      = HEADER_FILL
        c.alignment = CENTER if ci > 2 else LEFT
        c.border    = thin_border()
        ws.column_dimensions[get_column_letter(ci)].width = w

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 22

    # --- Filas de datos ---
    row = 4
    for cat in summary.get('categories', []):
        # Fila de categoría
        ws.cell(row, 1, '').fill = CAT_FILL
        c = ws.cell(row, 2, f"📁 {cat['name']}")
        c.font = CAT_FONT
        c.fill = CAT_FILL
        c.alignment = LEFT
        for m in range(1, 13):
            val_str = cat['monthly_totals'].get(m, '0.00')
            try:
                val = float(str(val_str).replace(',', ''))
            except Exception:
                val = 0.0
            mc = ws.cell(row, 2 + m, val)
            mc.number_format = MONEY_FMT
            mc.fill = CAT_FILL
            mc.font = CAT_FONT
            mc.alignment = RIGHT
            mc.border = thin_border()
        # Total anual categoría
        try:
            ann = float(str(cat['annual_total']).replace(',', ''))
        except Exception:
            ann = 0.0
        ac = ws.cell(row, 15, ann)
        ac.number_format = MONEY_FMT
        ac.fill = CAT_FILL
        ac.font = CAT_FONT
        ac.alignment = RIGHT
        ac.border = thin_border()
        ws.cell(row, 1).border = thin_border()
        ws.cell(row, 2).border = thin_border()
        ws.row_dimensions[row].height = 18
        row += 1

        # Filas de cuentas
        for i, acc in enumerate(cat.get('accounts', [])):
            fill = STRIPE_FILL if i % 2 == 1 else WHITE_FILL
            ws.cell(row, 1, acc.get('provider', '')).fill = fill
            ws.cell(row, 1).alignment = LEFT
            ws.cell(row, 1).font = ACC_FONT
            ws.cell(row, 1).border = thin_border()

            ws.cell(row, 2, f"  • {acc['name']}").fill = fill
            ws.cell(row, 2).alignment = LEFT
            ws.cell(row, 2).font = ACC_FONT
            ws.cell(row, 2).border = thin_border()

            for m in range(1, 13):
                val_str = acc['months'].get(m, '0.00')
                try:
                    val = float(str(val_str).replace(',', ''))
                except Exception:
                    val = 0.0
                mc = ws.cell(row, 2 + m, val)
                mc.number_format = MONEY_FMT
                mc.fill = fill
                mc.font = ACC_FONT
                mc.alignment = RIGHT
                mc.border = thin_border()

            try:
                ann = float(str(acc['annual_total']).replace(',', ''))
            except Exception:
                ann = 0.0
            ac = ws.cell(row, 15, ann)
            ac.number_format = MONEY_FMT
            ac.fill = fill
            ac.font = Font(name='Calibri', bold=True, size=10, color='374151')
            ac.alignment = RIGHT
            ac.border = thin_border()
            ws.row_dimensions[row].height = 16
            row += 1

    # Fila TOTAL GENERAL
    ws.cell(row, 1, '').fill = GRAND_FILL
    ws.cell(row, 1).border = thin_border()
    gt = ws.cell(row, 2, 'TOTAL GENERAL')
    gt.font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
    gt.fill = GRAND_FILL
    gt.alignment = LEFT
    gt.border = thin_border()
    for m in range(1, 13):
        val_str = summary.get('general_monthly_totals', {}).get(m, '0.00')
        try:
            val = float(str(val_str).replace(',', ''))
        except Exception:
            val = 0.0
        mc = ws.cell(row, 2 + m, val)
        mc.number_format = MONEY_FMT
        mc.fill = GRAND_FILL
        mc.font = Font(name='Calibri', bold=True, size=10, color='FFFFFF')
        mc.alignment = RIGHT
        mc.border = thin_border()
    ac = ws.cell(row, 15, annual_total_val)
    ac.number_format = MONEY_FMT
    ac.fill = GRAND_FILL
    ac.font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
    ac.alignment = RIGHT
    ac.border = thin_border()
    ws.row_dimensions[row].height = 20

    # ============================================================
    # HOJA 2: Resumen por Categoría
    # ============================================================
    ws2 = wb.create_sheet("Resumen por Categoría")
    ws2.freeze_panes = "C3"

    ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=15)
    t2 = ws2.cell(1, 1, f"RESUMEN POR CATEGORÍA — {company_name.upper()} — {year}")
    t2.font     = TITLE_FONT
    t2.fill     = BLUE_FILL
    t2.alignment = CENTER
    ws2.row_dimensions[1].height = 26

    headers2 = ['Categoría'] + MONTH_NAMES + ['Total Anual', '% del Total']
    col_widths2 = [35] + [13]*12 + [16, 13]
    for ci, (hdr, w) in enumerate(zip(headers2, col_widths2), start=1):
        c = ws2.cell(2, ci, hdr)
        c.font      = HEADER_FONT
        c.fill      = HEADER_FILL
        c.alignment = CENTER
        c.border    = thin_border()
        ws2.column_dimensions[get_column_letter(ci)].width = w
    ws2.row_dimensions[2].height = 20

    row2 = 3
    for i, cat in enumerate(summary.get('categories', [])):
        fill = STRIPE_FILL if i % 2 == 1 else WHITE_FILL
        ws2.cell(row2, 1, cat['name']).font = Font(name='Calibri', bold=True, size=10)
        ws2.cell(row2, 1).fill = fill
        ws2.cell(row2, 1).alignment = LEFT
        ws2.cell(row2, 1).border = thin_border()
        for m in range(1, 13):
            val_str = cat['monthly_totals'].get(m, '0.00')
            try:
                val = float(str(val_str).replace(',', ''))
            except Exception:
                val = 0.0
            mc = ws2.cell(row2, 1 + m, val)
            mc.number_format = MONEY_FMT
            mc.fill = fill
            mc.alignment = RIGHT
            mc.border = thin_border()
        try:
            ann = float(str(cat['annual_total']).replace(',', ''))
        except Exception:
            ann = 0.0
        ac = ws2.cell(row2, 14, ann)
        ac.number_format = MONEY_FMT
        ac.fill = fill
        ac.font = Font(name='Calibri', bold=True, size=10)
        ac.alignment = RIGHT
        ac.border = thin_border()
        # Porcentaje
        pct = (ann / annual_total_val * 100) if annual_total_val > 0 else 0.0
        pc = ws2.cell(row2, 15, pct / 100)
        pc.number_format = '0.00%'
        pc.fill = fill
        pc.alignment = RIGHT
        pc.border = thin_border()
        ws2.row_dimensions[row2].height = 16
        row2 += 1

    # Fila total resumen
    gt2 = ws2.cell(row2, 1, 'TOTAL GENERAL')
    gt2.font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
    gt2.fill = GRAND_FILL
    gt2.alignment = LEFT
    gt2.border = thin_border()
    for m in range(1, 13):
        val_str = summary.get('general_monthly_totals', {}).get(m, '0.00')
        try:
            val = float(str(val_str).replace(',', ''))
        except Exception:
            val = 0.0
        mc = ws2.cell(row2, 1 + m, val)
        mc.number_format = MONEY_FMT
        mc.fill = GRAND_FILL
        mc.font = Font(name='Calibri', bold=True, size=10, color='FFFFFF')
        mc.alignment = RIGHT
        mc.border = thin_border()
    ac2 = ws2.cell(row2, 14, annual_total_val)
    ac2.number_format = MONEY_FMT
    ac2.fill = GRAND_FILL
    ac2.font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
    ac2.alignment = RIGHT
    ac2.border = thin_border()
    ws2.cell(row2, 15, 1.0).number_format = '0.00%'
    ws2.cell(row2, 15).fill = GRAND_FILL
    ws2.cell(row2, 15).font = Font(name='Calibri', bold=True, color='FFFFFF')
    ws2.cell(row2, 15).alignment = RIGHT
    ws2.cell(row2, 15).border = thin_border()
    ws2.row_dimensions[row2].height = 20

    return wb


@app.get("/api/export/budget", tags=["Exportación"])
def export_budget_excel(
    company_id: int = Query(..., description="ID de la empresa"),
    year: int = Query(2026, description="Año presupuestario"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exporta el presupuesto de una empresa y año específico a un archivo Excel (.xlsx).
    Incluye hoja de detalle completo (Proveedor + Cuenta + 12 meses + Total Anual)
    y hoja de resumen por categoría con porcentaje sobre el total.
    """
    verify_company_access(company_id, user, db, required_role="CONSULTA")
    comp = db.query(Company).filter(Company.id == company_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada.")

    summary = calculate_budget_summary(db, company_id=company_id, year=year)
    company_name = comp.name
    wb = _build_budget_workbook(summary, company_name, year)

    safe_name = comp.code.replace('/', '-').replace('\\', '-')
    filename = f"Presupuesto_{safe_name}_{year}.xlsx"
    return _make_excel_response(wb, filename)


@app.get("/api/export/consolidation", tags=["Exportación"])
def export_consolidation_excel(
    company_ids: Optional[str] = Query(None, description="IDs de empresas separados por coma (ej. 1,2,3)"),
    year: int = Query(2026, description="Año a consolidar"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exporta el consolidado corporativo de múltiples empresas a un archivo Excel (.xlsx).
    Incluye hoja de consolidado mensual y hoja de participación por empresa.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl no está instalado. Ejecuta: pip install openpyxl"
        )

    if company_ids:
        try:
            ids_list = [int(x.strip()) for x in company_ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de company_ids inválido.")
    else:
        active_comps = db.query(Company).filter(Company.status == "ACTIVO").all()
        ids_list = [c.id for c in active_comps]

    if not user.is_superuser:
        allowed_ids = set(r.company_id for r in user.roles)
        ids_list = [cid for cid in ids_list if cid in allowed_ids]

    if not ids_list:
        raise HTTPException(status_code=403, detail="Sin permisos para consolidar las empresas seleccionadas.")

    consolidation = calculate_corporate_consolidation(db, company_ids=ids_list, year=year)

    MONTH_NAMES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio',
                   'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

    def thin_border():
        s = Side(style='thin', color='D1D5DB')
        return Border(left=s, right=s, top=s, bottom=s)

    TITLE_FONT  = Font(name='Calibri', bold=True, size=14, color='FFFFFF')
    HEADER_FONT = Font(name='Calibri', bold=True, size=10, color='FFFFFF')
    BOLD_FONT   = Font(name='Calibri', bold=True, size=10)
    NORM_FONT   = Font(name='Calibri', size=10)
    BLUE_FILL   = PatternFill('solid', fgColor='1E1B4B')
    HEADER_FILL = PatternFill('solid', fgColor='4F46E5')
    STRIPE_FILL = PatternFill('solid', fgColor='EEF2FF')
    GRAND_FILL  = PatternFill('solid', fgColor='818CF8')
    WHITE_FILL  = PatternFill('solid', fgColor='FFFFFF')
    MONEY_FMT   = '#,##0.00'
    CENTER = Alignment(horizontal='center', vertical='center')
    RIGHT  = Alignment(horizontal='right',  vertical='center')
    LEFT   = Alignment(horizontal='left',   vertical='center')

    wb = openpyxl.Workbook()

    # ============================================================
    # HOJA 1: Consolidado mensual por empresa
    # ============================================================
    ws = wb.active
    ws.title = "Consolidado Mensual"
    ws.freeze_panes = "B3"

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=15)
    t = ws.cell(1, 1, f"CONSOLIDADO CORPORATIVO — {year}")
    t.font = TITLE_FONT
    t.fill = BLUE_FILL
    t.alignment = CENTER
    ws.row_dimensions[1].height = 26

    headers = ['Empresa'] + MONTH_NAMES + ['Total Anual', '% Participación']
    col_widths = [30] + [13]*12 + [16, 14]
    for ci, (hdr, w) in enumerate(zip(headers, col_widths), start=1):
        c = ws.cell(2, ci, hdr)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = CENTER
        c.border = thin_border()
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.row_dimensions[2].height = 20

    try:
        total_annual = float(str(consolidation.get('total_annual', '0.00')).replace(',', ''))
    except Exception:
        total_annual = 0.0

    row = 3
    for i, comp_summary in enumerate(consolidation.get('companies', [])):
        fill = STRIPE_FILL if i % 2 == 1 else WHITE_FILL
        ws.cell(row, 1, comp_summary.get('company_name', '')).font = BOLD_FONT
        ws.cell(row, 1).fill = fill
        ws.cell(row, 1).alignment = LEFT
        ws.cell(row, 1).border = thin_border()
        for m in range(1, 13):
            val_str = comp_summary.get('monthly_totals', {}).get(m, '0.00')
            try:
                val = float(str(val_str).replace(',', ''))
            except Exception:
                val = 0.0
            mc = ws.cell(row, 1 + m, val)
            mc.number_format = MONEY_FMT
            mc.fill = fill
            mc.font = NORM_FONT
            mc.alignment = RIGHT
            mc.border = thin_border()
        try:
            ann = float(str(comp_summary.get('annual_total', '0.00')).replace(',', ''))
        except Exception:
            ann = 0.0
        ac = ws.cell(row, 14, ann)
        ac.number_format = MONEY_FMT
        ac.fill = fill
        ac.font = BOLD_FONT
        ac.alignment = RIGHT
        ac.border = thin_border()
        pct = (ann / total_annual * 100) if total_annual > 0 else 0.0
        pc = ws.cell(row, 15, pct / 100)
        pc.number_format = '0.00%'
        pc.fill = fill
        pc.alignment = RIGHT
        pc.border = thin_border()
        ws.row_dimensions[row].height = 16
        row += 1

    # Fila total consolidado
    gt = ws.cell(row, 1, 'TOTAL CONSOLIDADO')
    gt.font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
    gt.fill = GRAND_FILL
    gt.alignment = LEFT
    gt.border = thin_border()
    for m in range(1, 13):
        val_str = consolidation.get('consolidated_monthly_totals', {}).get(m, '0.00')
        try:
            val = float(str(val_str).replace(',', ''))
        except Exception:
            val = 0.0
        mc = ws.cell(row, 1 + m, val)
        mc.number_format = MONEY_FMT
        mc.fill = GRAND_FILL
        mc.font = Font(name='Calibri', bold=True, size=10, color='FFFFFF')
        mc.alignment = RIGHT
        mc.border = thin_border()
    ac_g = ws.cell(row, 14, total_annual)
    ac_g.number_format = MONEY_FMT
    ac_g.fill = GRAND_FILL
    ac_g.font = Font(name='Calibri', bold=True, size=11, color='FFFFFF')
    ac_g.alignment = RIGHT
    ac_g.border = thin_border()
    ws.cell(row, 15, 1.0).number_format = '0.00%'
    ws.cell(row, 15).fill = GRAND_FILL
    ws.cell(row, 15).font = Font(name='Calibri', bold=True, color='FFFFFF')
    ws.cell(row, 15).alignment = RIGHT
    ws.cell(row, 15).border = thin_border()
    ws.row_dimensions[row].height = 22

    filename = f"Consolidado_Corporativo_{year}.xlsx"
    return _make_excel_response(wb, filename)


# =========================================================================
# 9. SERVIR INTERFAZ WEB ESTÁTICA
# =========================================================================
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index():
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Planificador de Presupuesto API activa. Visite /docs"}
