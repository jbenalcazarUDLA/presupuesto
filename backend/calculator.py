from decimal import Decimal
from typing import Dict, Tuple, List, Optional
from sqlalchemy.orm import Session
from database import Company, Category, Account, MonthlyExpense
from schemas import to_money_decimal, format_money

ZERO = Decimal("0.00")

def calculate_budget_summary(db: Session, company_id: int = 1, year: int = 2026) -> dict:
    """
    Construye la jerarquía para una empresa y año específicos:
    EMPRESA -> CATEGORÍA -> CUENTA -> GASTOS MENSUALES (Meses 1 al 12)
    Y calcula automáticamente los 6 totales requeridos para esa empresa:
    1. Total mensual de cada cuenta.
    2. Total anual de cada cuenta.
    3. Total mensual de cada categoría (sumando sus cuentas).
    4. Total anual de cada categoría.
    5. Total mensual general de la empresa.
    6. Total anual general de la empresa y cuadre horizontal vs vertical.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    comp_name = company.name if company else f"Empresa #{company_id}"
    comp_code = company.code if company else f"EMP{company_id}"

    # Categorías pertenecientes exclusivamente a la empresa
    categories = db.query(Category).filter(
        Category.company_id == company_id
    ).order_by(Category.id).all()

    # Recoger IDs de cuentas pertenecientes a esta empresa
    account_ids = []
    for cat in categories:
        for acc in cat.accounts:
            account_ids.append(acc.id)

    # Filtrar gastos por cuentas de la empresa y el año seleccionado
    if account_ids:
        all_expenses = db.query(MonthlyExpense).filter(
            MonthlyExpense.account_id.in_(account_ids),
            MonthlyExpense.year == year
        ).all()
    else:
        all_expenses = []

    # Mapeo de gastos por (account_id, month) -> Decimal
    expense_map: Dict[Tuple[int, int], Decimal] = {
        (e.account_id, e.month): to_money_decimal(e.amount) for e in all_expenses
    }

    # Acumuladores de totales generales de la empresa
    gen_monthly: Dict[int, Decimal] = {m: ZERO for m in range(1, 13)}
    gen_annual = ZERO

    cat_summaries = []

    for cat in categories:
        cat_monthly: Dict[int, Decimal] = {m: ZERO for m in range(1, 13)}
        cat_annual = ZERO
        acc_summaries = []

        for acc in cat.accounts:
            acc_months: Dict[int, str] = {}
            acc_annual = ZERO

            for m in range(1, 13):
                amt = expense_map.get((acc.id, m), ZERO)
                acc_months[m] = format_money(amt)  # 1. Total mensual de la cuenta

                # 2. Total anual de la cuenta
                acc_annual += amt

                # 3. Total mensual de la categoría
                cat_monthly[m] += amt

            # 4. Total anual de la categoría
            cat_annual += acc_annual

            acc_summaries.append({
                "id": acc.id,
                "category_id": acc.category_id,
                "code": acc.code or "",
                "name": acc.name,
                "provider": acc.provider or "",
                "is_active": acc.is_active,
                "months": acc_months,
                "annual_total": format_money(acc_annual)
            })

        # 5. Acumular totales mensuales generales
        for m in range(1, 13):
            gen_monthly[m] += cat_monthly[m]

        # 6. Acumular total anual general
        gen_annual += cat_annual

        cat_summaries.append({
            "id": cat.id,
            "company_id": cat.company_id,
            "code": cat.code or "",
            "name": cat.name,
            "accounts": acc_summaries,
            "monthly_totals": {m: format_money(cat_monthly[m]) for m in range(1, 13)},
            "annual_total": format_money(cat_annual)
        })

    sum_gen_monthly = sum(gen_monthly.values(), ZERO)
    is_balanced = (sum_gen_monthly == gen_annual)

    return {
        "company_id": company_id,
        "company_code": comp_code,
        "company_name": comp_name,
        "year": year,
        "categories": cat_summaries,
        "general_monthly_totals": {m: format_money(gen_monthly[m]) for m in range(1, 13)},
        "general_annual_total": format_money(gen_annual),
        "is_balanced": is_balanced
    }

def calculate_corporate_consolidation(db: Session, company_ids: List[int], year: int = 2026) -> dict:
    """
    CONSOLIDADO CORPORATIVO (Secciones 10, 11 y 21):
    Calcula dinámicamente y al vuelo la agregación de múltiples empresas sin duplicar datos en BD:
    Enero_Consolidado = SUM(Empresa_i Enero) ... Dic_Consolidado = SUM(Empresa_i Dic)
    Total_Anual_Consolidado = SUM(Empresa_i Total_Anual)
    Participación % = (Total Empresa_i / Total Consolidado) * 100
    """
    if not company_ids:
        # Si no se especifican, consolidar todas las empresas activas
        active_comps = db.query(Company).filter(Company.status == "ACTIVO").all()
        company_ids = [c.id for c in active_comps]

    companies_breakdown = []
    consolidated_monthly: Dict[int, Decimal] = {m: ZERO for m in range(1, 13)}
    total_consolidated_annual = ZERO

    # Calcular individualmente el resumen oficial de cada empresa seleccionada
    summaries = []
    for cid in company_ids:
        summary = calculate_budget_summary(db, company_id=cid, year=year)
        summaries.append(summary)
        c_annual = Decimal(summary["general_annual_total"])
        total_consolidated_annual += c_annual

        for m in range(1, 13):
            c_month_val = Decimal(summary["general_monthly_totals"][m])
            consolidated_monthly[m] += c_month_val

    # Calcular desglose y participación porcentual de cada empresa
    for summary in summaries:
        c_annual = Decimal(summary["general_annual_total"])
        if total_consolidated_annual > ZERO:
            share = ((c_annual / total_consolidated_annual) * Decimal("100")).quantize(Decimal("0.01"))
            share_str = f"{share:.2f}%"
        else:
            share_str = "0.00%"

        companies_breakdown.append({
            "company_id": summary["company_id"],
            "company_code": summary["company_code"],
            "company_name": summary["company_name"],
            "monthly_totals": summary["general_monthly_totals"],
            "annual_total": summary["general_annual_total"],
            "percentage_share": share_str
        })

    # Verificar cuadre cruzado del consolidado
    sum_months = sum(consolidated_monthly.values(), ZERO)
    is_balanced = (sum_months == total_consolidated_annual)

    return {
        "year": year,
        "selected_company_ids": company_ids,
        "companies_count": len(company_ids),
        "companies_breakdown": companies_breakdown,
        "consolidated_monthly_totals": {m: format_money(consolidated_monthly[m]) for m in range(1, 13)},
        "total_annual": format_money(total_consolidated_annual),
        "is_balanced": is_balanced
    }

def calculate_budget_comparison(db: Session, company_id: int = 1, projected_year: int = 2026, base_year: int = 2025) -> dict:
    """
    Compara el presupuesto del año proyectado vs año base para una empresa específica
    utilizando exactamente las reglas de cálculo oficiales.
    """
    proj_summary = calculate_budget_summary(db, company_id=company_id, year=projected_year)
    base_summary = calculate_budget_summary(db, company_id=company_id, year=base_year)

    base_annual_total = Decimal(base_summary["general_annual_total"])
    proj_annual_total = Decimal(proj_summary["general_annual_total"])

    # Comprobar suficiencia de datos en el año base para esta empresa
    has_sufficient_data = (base_annual_total > ZERO)

    if not has_sufficient_data:
        return {
            "has_sufficient_data": False,
            "base_year": base_year,
            "projected_year": projected_year,
            "message": "No existen datos suficientes para realizar la comparación.",
            "rows": [],
            "total": None
        }

    rows = []
    base_cat_map = {c["id"]: Decimal(c["annual_total"]) for c in base_summary["categories"]}

    for proj_cat in proj_summary["categories"]:
        c_id = proj_cat["id"]
        c_name = proj_cat["name"]
        p_val = Decimal(proj_cat["annual_total"])
        b_val = base_cat_map.get(c_id, ZERO)

        diff_amt = p_val - b_val

        # Variación % con control de división por cero
        if b_val > ZERO:
            var_pct = ((p_val - b_val) / b_val) * Decimal("100")
            var_pct_str = f"{var_pct:+.2f}%"
        elif p_val == ZERO:
            var_pct_str = "0.00%"
        else:
            var_pct_str = "+100.00%"

        rows.append({
            "category_id": c_id,
            "category_name": c_name,
            "base_annual": format_money(b_val),
            "projected_annual": format_money(p_val),
            "variation_amount": format_money(diff_amt),
            "variation_pct": var_pct_str
        })

    # Total General
    gen_diff = proj_annual_total - base_annual_total
    if base_annual_total > ZERO:
        gen_var_pct = ((proj_annual_total - base_annual_total) / base_annual_total) * Decimal("100")
        gen_pct_str = f"{gen_var_pct:+.2f}%"
    elif proj_annual_total == ZERO:
        gen_pct_str = "0.00%"
    else:
        gen_pct_str = "+100.00%"

    return {
        "has_sufficient_data": True,
        "base_year": base_year,
        "projected_year": projected_year,
        "message": "",
        "rows": rows,
        "total": {
            "base_annual": format_money(base_annual_total),
            "projected_annual": format_money(proj_annual_total),
            "variation_amount": format_money(gen_diff),
            "variation_pct": gen_pct_str
        }
    }
