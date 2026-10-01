from decimal import Decimal
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from app.models.budget_year import BudgetYear
from app.models.category import Category
from app.models.account import Account
from app.models.projection import BudgetMonthlyProjection
from app.models.audit_log import BudgetAuditLog
from app.core.decimal_math import to_decimal, format_decimal, ZERO_DECIMAL
from app.schemas.budget import BudgetUpdateRequest, BudgetMatrixResponse

class BudgetCalculatorService:

    @staticmethod
    def get_budget_matrix(db: Session, year: int) -> dict:
        """
        Calcula y construye la estructura jerárquica completa para el año presupuestario:
        1. Total mensual de cada cuenta.
        2. Total anual de cada cuenta.
        3. Total mensual de cada categoría, sumando todas sus cuentas.
        4. Total anual de cada categoría.
        5. Total mensual general.
        6. Total anual general.
        """
        budget_year = db.query(BudgetYear).filter(BudgetYear.year == year).first()
        if not budget_year:
            # Si no existe, creamos el año automáticamente en estado DRAFT
            budget_year = BudgetYear(year=year, status="DRAFT", notes=f"Presupuesto {year}")
            db.add(budget_year)
            db.commit()
            db.refresh(budget_year)

        # Obtener todas las categorías activas ordenadas
        categories = db.query(Category).filter(Category.is_active == True).order_by(Category.display_order, Category.id).all()

        # Obtener todas las proyecciones del año
        projections = db.query(BudgetMonthlyProjection).filter(BudgetMonthlyProjection.year == year).all()
        # Mapear proyecciones por (account_id, month) -> Decimal
        proj_map: Dict[Tuple[int, int], Decimal] = {
            (p.account_id, p.month): to_decimal(p.amount) for p in projections
        }

        # Inicializadores para totales generales
        general_monthly_dec: Dict[int, Decimal] = {m: ZERO_DECIMAL for m in range(1, 13)}
        general_annual_dec = ZERO_DECIMAL

        categories_matrix = []

        for cat in categories:
            cat_monthly_dec: Dict[int, Decimal] = {m: ZERO_DECIMAL for m in range(1, 13)}
            cat_annual_dec = ZERO_DECIMAL
            accounts_matrix = []

            for acc in cat.accounts:
                if not acc.is_active:
                    continue

                acc_months_dec: Dict[int, Decimal] = {}
                acc_months_str: Dict[int, str] = {}
                acc_annual_dec = ZERO_DECIMAL

                for m in range(1, 13):
                    amt = proj_map.get((acc.id, m), ZERO_DECIMAL)
                    acc_months_dec[m] = amt
                    acc_months_str[m] = format_decimal(amt)

                    # 1. Total mensual de cada cuenta = amt
                    # 2. Acumulación para Total anual de cada cuenta
                    acc_annual_dec += amt

                    # 3. Acumulación para Total mensual de la categoría
                    cat_monthly_dec[m] += amt

                # 4. Acumulación para Total anual de la categoría
                cat_annual_dec += acc_annual_dec

                accounts_matrix.append({
                    "id": acc.id,
                    "code": acc.code or "",
                    "name": acc.name,
                    "responsible": acc.responsible or "",
                    "provider": acc.provider or "",
                    "display_order": acc.display_order,
                    "months": acc_months_str,
                    "annual_total": format_decimal(acc_annual_dec)
                })

            # 5. Acumulación para Totales mensuales generales
            for m in range(1, 13):
                general_monthly_dec[m] += cat_monthly_dec[m]

            # 6. Acumulación para Total anual general
            general_annual_dec += cat_annual_dec

            categories_matrix.append({
                "id": cat.id,
                "code": cat.code,
                "name": cat.name,
                "display_order": cat.display_order,
                "accounts": accounts_matrix,
                "monthly_totals": {m: format_decimal(cat_monthly_dec[m]) for m in range(1, 13)},
                "annual_total": format_decimal(cat_annual_dec)
            })

        # Verificación de cuadre cruzado:
        # Suma de totales mensuales generales vs suma de totales anuales de categorías
        sum_monthly_generals = sum(general_monthly_dec.values(), ZERO_DECIMAL)
        is_balanced = (sum_monthly_generals == general_annual_dec)

        return {
            "year": budget_year.year,
            "status": budget_year.status,
            "notes": budget_year.notes,
            "categories": categories_matrix,
            "general_monthly_totals": {m: format_decimal(general_monthly_dec[m]) for m in range(1, 13)},
            "general_annual_total": format_decimal(general_annual_dec),
            "is_balanced": is_balanced
        }

    @staticmethod
    def update_projections(db: Session, year: int, payload: BudgetUpdateRequest) -> dict:
        """
        Aplica actualizaciones a las proyecciones mensuales para un año determinado.
        Registra cada cambio en la tabla de auditoría (budget_audit_logs).
        Retorna la matriz recalculada.
        """
        budget_year = db.query(BudgetYear).filter(BudgetYear.year == year).first()
        if not budget_year:
            budget_year = BudgetYear(year=year, status="DRAFT", notes=f"Presupuesto {year}")
            db.add(budget_year)
            db.flush()

        for item in payload.updates:
            new_amt = to_decimal(item.amount)
            if new_amt < ZERO_DECIMAL:
                raise ValueError(f"El importe para la cuenta {item.account_id} no puede ser negativo: {new_amt}")

            # Buscar proyección existente
            proj = db.query(BudgetMonthlyProjection).filter(
                BudgetMonthlyProjection.year == year,
                BudgetMonthlyProjection.account_id == item.account_id,
                BudgetMonthlyProjection.month == item.month
            ).first()

            prev_amt = to_decimal(proj.amount) if proj else ZERO_DECIMAL

            if proj:
                if prev_amt != new_amt:
                    proj.amount = new_amt
                    # Registrar auditoría
                    audit = BudgetAuditLog(
                        year=year,
                        account_id=item.account_id,
                        month=item.month,
                        previous_amount=prev_amt,
                        new_amount=new_amt,
                        modified_by=payload.modified_by,
                        reason=payload.reason
                    )
                    db.add(audit)
            else:
                proj = BudgetMonthlyProjection(
                    year=year,
                    account_id=item.account_id,
                    month=item.month,
                    amount=new_amt
                )
                db.add(proj)
                if new_amt != ZERO_DECIMAL:
                    audit = BudgetAuditLog(
                        year=year,
                        account_id=item.account_id,
                        month=item.month,
                        previous_amount=ZERO_DECIMAL,
                        new_amount=new_amt,
                        modified_by=payload.modified_by,
                        reason=payload.reason
                    )
                    db.add(audit)

        db.commit()
        return BudgetCalculatorService.get_budget_matrix(db, year)
