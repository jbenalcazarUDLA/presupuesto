from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, Category, Account, MonthlyExpense
from calculator import calculate_budget_summary

def run_tests():
    # Base de datos en memoria para pruebas
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()

    # 1. Crear categoría
    cat = Category(name="Operaciones")
    db.add(cat)
    db.flush()

    # 2. Crear cuentas dentro de la categoría
    acc1 = Account(category_id=cat.id, name="Internet", provider="Celerity")
    acc2 = Account(category_id=cat.id, name="Servidores", provider="AWS")
    db.add_all([acc1, acc2])
    db.flush()

    # 3. Registrar gastos mensuales para Internet (mes 1: 100.50, mes 2: 100.50)
    e1 = MonthlyExpense(account_id=acc1.id, month=1, amount=Decimal("100.50"))
    e2 = MonthlyExpense(account_id=acc1.id, month=2, amount=Decimal("100.50"))

    # Registrar gastos mensuales para Servidores (mes 1: 200.25, mes 2: 300.75)
    e3 = MonthlyExpense(account_id=acc2.id, month=1, amount=Decimal("200.25"))
    e4 = MonthlyExpense(account_id=acc2.id, month=2, amount=Decimal("300.75"))

    db.add_all([e1, e2, e3, e4])
    db.commit()

    # 4. Ejecutar motor de cálculo
    summary = calculate_budget_summary(db)

    # Validaciones:
    # Cuenta 1: mes 1 = 100.50, mes 2 = 100.50, anual = 201.00
    acc1_res = summary["categories"][0]["accounts"][0]
    assert acc1_res["provider"] == "Celerity", "Error proveedor cuenta 1"
    assert acc1_res["months"][1] == "100.50", "Error mensual cuenta 1 mes 1"
    assert acc1_res["annual_total"] == "201.00", "Error total anual cuenta 1"

    # Cuenta 2: mes 1 = 200.25, mes 2 = 300.75, anual = 501.00
    acc2_res = summary["categories"][0]["accounts"][1]
    assert acc2_res["provider"] == "AWS", "Error proveedor cuenta 2"
    assert acc2_res["months"][1] == "200.25", "Error mensual cuenta 2 mes 1"
    assert acc2_res["annual_total"] == "501.00", "Error total anual cuenta 2"

    # Categoría: mes 1 = 100.50 + 200.25 = 301.75; mes 2 = 100.50 + 300.75 = 401.25; anual = 702.00
    cat_res = summary["categories"][0]
    assert cat_res["monthly_totals"][1] == "301.75", "Error total mensual categoría mes 1"
    assert cat_res["monthly_totals"][2] == "401.25", "Error total mensual categoría mes 2"
    assert cat_res["annual_total"] == "702.00", "Error total anual categoría"

    # Total general mensual: mes 1 = 301.75, mes 2 = 401.25
    assert summary["general_monthly_totals"][1] == "301.75", "Error total general mensual mes 1"
    assert summary["general_monthly_totals"][2] == "401.25", "Error total general mensual mes 2"

    # Total general anual: 702.00
    assert summary["general_annual_total"] == "702.00", "Error total general anual"
    assert summary["is_balanced"] is True, "Error en balance cruzado"

    # 5. Prueba de modificación de cuenta
    acc1.name = "Internet Fibra Óptica"
    acc1.provider = "Telconet"
    db.commit()
    summary2 = calculate_budget_summary(db)
    acc1_res2 = summary2["categories"][0]["accounts"][0]
    assert acc1_res2["name"] == "Internet Fibra Óptica", "Error al modificar nombre de cuenta"
    assert acc1_res2["provider"] == "Telconet", "Error al modificar proveedor de cuenta"

    # 6. Prueba de modificación de categoría
    cat.name = "Infraestructura & Telecomunicaciones"
    db.commit()
    summary3 = calculate_budget_summary(db)
    assert summary3["categories"][0]["name"] == "Infraestructura & Telecomunicaciones", "Error al modificar nombre de categoría"

    # 7. Prueba de parsing decimal con punto y coma
    from schemas import to_money_decimal, ExpenseItemUpdate
    assert to_money_decimal("12.50") == Decimal("12.50"), "Error parseando 12.50 con punto"
    assert to_money_decimal("12,50") == Decimal("12.50"), "Error parseando 12,50 con coma"
    assert to_money_decimal("0,75") == Decimal("0.75"), "Error parseando 0,75 con coma"
    assert to_money_decimal(".5") == Decimal("0.50"), "Error parseando .5"
    assert to_money_decimal("") == Decimal("0.00"), "Error parseando vacio"
    
    item = ExpenseItemUpdate(account_id=acc1.id, month=1, amount="150,75")
    assert item.amount == Decimal("150.75"), "Error en Pydantic ExpenseItemUpdate con coma"

    print("✓ Todas las reglas de cálculo, validaciones, modificación de cuentas/categorías y manejo de decimales (punto y coma) pasaron exitosamente.")
    db.close()

if __name__ == "__main__":
    run_tests()
