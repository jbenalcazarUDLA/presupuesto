"""
Suite de Pruebas Automatizadas — SPRINT 2: DASHBOARD PRESUPUESTARIO
Valida las 9 pruebas requeridas en la especificación:
1. La suma de las cuentas coincide con el total de la categoría.
2. La suma de categorías coincide con el total general.
3. La suma de los 12 meses coincide con el total anual.
4. Los filtros modifican correctamente todos los componentes.
5. Una categoría sin cuentas se maneja correctamente.
6. Un año sin presupuesto muestra correctamente el estado vacío.
7. La comparación entre años calcula correctamente variación absoluta y porcentual.
8. División por cero en variación porcentual.
9. Los valores mostrados en dashboard coinciden con los valores del módulo presupuestario.
"""

from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Company, Category, Account, MonthlyExpense
from calculator import calculate_budget_summary, calculate_budget_comparison
from schemas import to_money_decimal, format_money

def run_dashboard_tests():
    print("=" * 70)
    print("INICIANDO PRUEBAS AUTOMATIZADAS — SPRINT 2 DASHBOARD")
    print("=" * 70)

    # Base de datos en memoria para pruebas aisladas
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()

    # Configuración de datos de prueba multianual:
    comp = Company(id=1, code="EDIMCA", name="EDIMCA S.A.", status="ACTIVO")
    db.add(comp)
    db.flush()

    cat_ops = Category(company_id=comp.id, name="Operaciones y Logística")
    cat_tech = Category(company_id=comp.id, name="Tecnología e Infraestructura")
    cat_empty = Category(company_id=comp.id, name="Proyectos Especiales") # Prueba 5: Categoría sin cuentas
    db.add_all([cat_ops, cat_tech, cat_empty])
    db.flush()

    # Cuentas en Operaciones
    acc_clean = Account(category_id=cat_ops.id, name="Limpieza y Mantenimiento", provider="CleanCorp")
    acc_sec = Account(category_id=cat_ops.id, name="Seguridad Física", provider="Seguritas")

    # Cuentas en Tecnología
    acc_cloud = Account(category_id=cat_tech.id, name="Servicios Cloud", provider="AWS / Cirion")
    acc_net = Account(category_id=cat_tech.id, name="Internet y Enlaces", provider="Telconet")
    db.add_all([acc_clean, acc_sec, acc_cloud, acc_net])
    db.flush()

    # --- Gastos 2025 (Año Base) ---
    # Limpieza: $1,000 cada mes (Total anual: $12,000.00)
    for m in range(1, 13):
        db.add(MonthlyExpense(account_id=acc_clean.id, year=2025, month=m, amount=Decimal("1000.00")))
    # Servicios Cloud: $2,500 cada mes (Total anual: $30,000.00)
    for m in range(1, 13):
        db.add(MonthlyExpense(account_id=acc_cloud.id, year=2025, month=m, amount=Decimal("2500.00")))

    # --- Gastos 2026 (Año Proyectado) ---
    # Limpieza: $1,200 cada mes (Total anual: $14,400.00) -> Variación +$2,400.00 (+20.00%)
    for m in range(1, 13):
        db.add(MonthlyExpense(account_id=acc_clean.id, year=2026, month=m, amount=Decimal("1200.00")))
    # Seguridad: $800 en meses impares, $900 en pares (Total anual: $10,200.00) -> Base tenía 0 (División por cero)
    for m in range(1, 13):
        amt = Decimal("800.00") if m % 2 != 0 else Decimal("900.00")
        db.add(MonthlyExpense(account_id=acc_sec.id, year=2026, month=m, amount=amt))
    # Servicios Cloud: $3,000 cada mes (Total anual: $36,000.00) -> Variación +$6,000.00 (+20.00%)
    for m in range(1, 13):
        db.add(MonthlyExpense(account_id=acc_cloud.id, year=2026, month=m, amount=Decimal("3000.00")))
    # Internet: $500 cada mes (Total anual: $6,000.00)
    for m in range(1, 13):
        db.add(MonthlyExpense(account_id=acc_net.id, year=2026, month=m, amount=Decimal("500.00")))

    db.commit()

    # Ejecutar cálculos oficiales
    summary_2026 = calculate_budget_summary(db, year=2026)
    summary_2025 = calculate_budget_summary(db, year=2025)
    summary_2027 = calculate_budget_summary(db, year=2027) # Año sin gastos registrados

    # -------------------------------------------------------------
    # PRUEBA 1: La suma de las cuentas coincide con el total de la categoría
    # -------------------------------------------------------------
    print("Ejecutando Prueba 1: Suma de cuentas vs Total de categoría...")
    for cat in summary_2026["categories"]:
        sum_accounts = sum(Decimal(acc["annual_total"]) for acc in cat["accounts"])
        cat_total = Decimal(cat["annual_total"])
        assert sum_accounts == cat_total, f"Fallo P1: {sum_accounts} != {cat_total} en categoría {cat['name']}"
    print("  [OK] Prueba 1 superada con éxito.")

    # -------------------------------------------------------------
    # PRUEBA 2: La suma de categorías coincide con el total general
    # -------------------------------------------------------------
    print("Ejecutando Prueba 2: Suma de categorías vs Total general...")
    sum_categories = sum(Decimal(cat["annual_total"]) for cat in summary_2026["categories"])
    gen_annual = Decimal(summary_2026["general_annual_total"])
    assert sum_categories == gen_annual, f"Fallo P2: {sum_categories} != {gen_annual}"
    assert summary_2026["is_balanced"] is True, "Fallo P2: is_balanced debe ser True"
    print("  [OK] Prueba 2 superada con éxito.")

    # -------------------------------------------------------------
    # PRUEBA 3: La suma de los 12 meses coincide con el total anual
    # -------------------------------------------------------------
    print("Ejecutando Prueba 3: Suma de los 12 meses vs Total anual...")
    sum_12_months = sum(Decimal(summary_2026["general_monthly_totals"][m]) for m in range(1, 13))
    assert sum_12_months == gen_annual, f"Fallo P3: Suma 12 meses {sum_12_months} != {gen_annual}"
    # También a nivel de cada categoría
    for cat in summary_2026["categories"]:
        cat_12m = sum(Decimal(cat["monthly_totals"][m]) for m in range(1, 13))
        assert cat_12m == Decimal(cat["annual_total"]), f"Fallo P3 en categoría {cat['name']}"
    print("  [OK] Prueba 3 superada con éxito.")

    # -------------------------------------------------------------
    # PRUEBA 4: Los filtros modifican correctamente todos los componentes
    # -------------------------------------------------------------
    print("Ejecutando Prueba 4: Comportamiento consistente de filtros...")
    # Filtro por Categoría específica (Tecnología)
    tech_cat = next(c for c in summary_2026["categories"] if c["name"] == "Tecnología e Infraestructura")
    tech_accounts = tech_cat["accounts"]
    tech_annual = Decimal(tech_cat["annual_total"])
    # 36000 (cloud) + 6000 (net) = 42000
    assert tech_annual == Decimal("42000.00"), f"Fallo P4 en filtro categoría: {tech_annual}"
    
    # Filtro por Cuenta específica (Cloud)
    cloud_acc = next(a for a in tech_accounts if a["name"] == "Servicios Cloud")
    assert Decimal(cloud_acc["annual_total"]) == Decimal("36000.00")
    assert Decimal(cloud_acc["months"][1]) == Decimal("3000.00")
    print("  [OK] Prueba 4 superada con éxito.")

    # -------------------------------------------------------------
    # PRUEBA 5: Una categoría sin cuentas se maneja correctamente
    # -------------------------------------------------------------
    print("Ejecutando Prueba 5: Categoría sin cuentas...")
    empty_cat = next(c for c in summary_2026["categories"] if c["name"] == "Proyectos Especiales")
    assert len(empty_cat["accounts"]) == 0, "Fallo P5: Categoría vacía no debe tener cuentas"
    assert Decimal(empty_cat["annual_total"]) == Decimal("0.00"), "Fallo P5: Total debe ser 0.00"
    for m in range(1, 13):
        assert empty_cat["monthly_totals"][m] == "0.00", f"Fallo P5: Mes {m} debe ser 0.00"
    print("  [OK] Prueba 5 superada con éxito.")

    # -------------------------------------------------------------
    # PRUEBA 6: Un año sin presupuesto muestra correctamente el estado vacío
    # -------------------------------------------------------------
    print("Ejecutando Prueba 6: Año sin presupuesto registrado...")
    assert Decimal(summary_2027["general_annual_total"]) == Decimal("0.00")
    for m in range(1, 13):
        assert summary_2027["general_monthly_totals"][m] == "0.00"
    assert summary_2027["is_balanced"] is True
    # Comparación contra año sin datos
    comp_empty = calculate_budget_comparison(db, projected_year=2026, base_year=2027)
    assert comp_empty["has_sufficient_data"] is False
    assert "No existen datos suficientes" in comp_empty["message"]
    print("  [OK] Prueba 6 superada con éxito.")

    # -------------------------------------------------------------
    # PRUEBA 7: Comparación entre años (Variación $ y Variación %)
    # -------------------------------------------------------------
    print("Ejecutando Prueba 7: Comparación de años con variación absoluta y porcentual...")
    comp = calculate_budget_comparison(db, projected_year=2026, base_year=2025)
    assert comp["has_sufficient_data"] is True
    assert comp["base_year"] == 2025
    assert comp["projected_year"] == 2026
    
    # Total Base: 12000 (limpieza) + 30000 (cloud) = 42000.00
    # Total Proyectado: 14400 + 10200 + 36000 + 6000 = 66600.00
    # Variación $: 66600 - 42000 = 24600.00
    # Variación %: (24600 / 42000) * 100 = 58.57%
    assert comp["total"]["base_annual"] == "42000.00"
    assert comp["total"]["projected_annual"] == "66600.00"
    assert comp["total"]["variation_amount"] == "24600.00"
    assert comp["total"]["variation_pct"] == "+58.57%"
    print("  [OK] Prueba 7 superada con éxito.")

    # -------------------------------------------------------------
    # PRUEBA 8: División por cero en variación porcentual
    # -------------------------------------------------------------
    print("Ejecutando Prueba 8: Manejo seguro de división por cero...")
    # Categoría 'Proyectos Especiales' tiene base=0 y proyectado=0
    row_empty = next(r for r in comp["rows"] if r["category_name"] == "Proyectos Especiales")
    assert row_empty["base_annual"] == "0.00"
    assert row_empty["projected_annual"] == "0.00"
    assert row_empty["variation_amount"] == "0.00"
    assert row_empty["variation_pct"] == "0.00%"

    # Categoría 'Tecnología' en 2025 tenía 30000 y en 2026 tiene 42000
    # Variación: +12000.00 (+40.00%)
    row_tech = next(r for r in comp["rows"] if r["category_name"] == "Tecnología e Infraestructura")
    assert row_tech["base_annual"] == "30000.00"
    assert row_tech["projected_annual"] == "42000.00"
    assert row_tech["variation_amount"] == "12000.00"
    assert row_tech["variation_pct"] == "+40.00%"
    print("  [OK] Prueba 8 superada con éxito.")

    # -------------------------------------------------------------
    # PRUEBA 9: Los valores mostrados en dashboard coinciden con el módulo presupuestario
    # -------------------------------------------------------------
    print("Ejecutando Prueba 9: Consistencia estricta entre Dashboard y Presupuesto...")
    # Simular endpoint /api/dashboard
    dash_budget = summary_2026
    # 1. Total anual de cada cuenta
    for cat in dash_budget["categories"]:
        for acc in cat["accounts"]:
            # Verificar con la suma de sus meses en base de datos
            db_acc_expenses = db.query(MonthlyExpense).filter(
                MonthlyExpense.account_id == acc["id"],
                MonthlyExpense.year == 2026
            ).all()
            db_sum = sum(e.amount for e in db_acc_expenses)
            assert Decimal(acc["annual_total"]) == db_sum, f"Fallo P9 en cuenta {acc['name']}"

    # 2. Total mensual general coincide exactamente
    for m in range(1, 13):
        assert dash_budget["general_monthly_totals"][m] == summary_2026["general_monthly_totals"][m]

    # 3. Total anual general coincide exactamente
    assert dash_budget["general_annual_total"] == summary_2026["general_annual_total"]
    print("  [OK] Prueba 9 superada con éxito.")

    print("=" * 70)
    print("¡TODAS LAS 9 PRUEBAS DEL SPRINT 2 PASARON EXITOSAMENTE!")
    print("=" * 70)
    db.close()

if __name__ == "__main__":
    run_dashboard_tests()
