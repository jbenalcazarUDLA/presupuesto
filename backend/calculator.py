from decimal import Decimal
from typing import Dict, Tuple
from sqlalchemy.orm import Session
from database import Category, Account, MonthlyExpense
from schemas import to_money_decimal, format_money

ZERO = Decimal("0.00")

def calculate_budget_summary(db: Session) -> dict:
    """
    Construye la jerarquía:
    CATEGORÍA -> CUENTA -> GASTOS MENSUALES (Meses 1 al 12)
    Y calcula automáticamente los 6 totales requeridos:
    1. Total mensual de cada cuenta.
    2. Total anual de cada cuenta.
    3. Total mensual de cada categoría (sumando sus cuentas).
    4. Total anual de cada categoría.
    5. Total mensual general.
    6. Total anual general.
    """
    categories = db.query(Category).order_by(Category.id).all()
    all_expenses = db.query(MonthlyExpense).all()

    # Mapeo de gastos por (account_id, month) -> Decimal
    expense_map: Dict[Tuple[int, int], Decimal] = {
        (e.account_id, e.month): to_money_decimal(e.amount) for e in all_expenses
    }

    # Acumuladores de totales generales
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
                acc_months[m] = format_money(amt) # 1. Total mensual de la cuenta

                # 2. Total anual de la cuenta
                acc_annual += amt

                # 3. Total mensual de la categoría
                cat_monthly[m] += amt

            # 4. Total anual de la categoría
            cat_annual += acc_annual

            acc_summaries.append({
                "id": acc.id,
                "category_id": acc.category_id,
                "name": acc.name,
                "provider": acc.provider or "",
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
            "name": cat.name,
            "accounts": acc_summaries,
            "monthly_totals": {m: format_money(cat_monthly[m]) for m in range(1, 13)},
            "annual_total": format_money(cat_annual)
        })

    sum_gen_monthly = sum(gen_monthly.values(), ZERO)
    is_balanced = (sum_gen_monthly == gen_annual)

    return {
        "categories": cat_summaries,
        "general_monthly_totals": {m: format_money(gen_monthly[m]) for m in range(1, 13)},
        "general_annual_total": format_money(gen_annual),
        "is_balanced": is_balanced
    }
