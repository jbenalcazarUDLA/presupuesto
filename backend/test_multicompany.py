"""
Suite de Pruebas Automatizadas — SPRINT MULTIEMPRESA Y CONSOLIDACIÓN CORPORATIVA
Valida las 10 pruebas obligatorias de la Sección 24:
1. Crear presupuesto para Empresa A (2027). Verificar que no aparezca en Empresa B.
2. Crear presupuesto para Empresa B (2027). Verificar que no aparezca en Empresa A.
3. Dos empresas pueden utilizar el mismo código de cuenta (AWS en Empresa A y Empresa B).
4. Modificar una cuenta de Empresa A. Verificar que Empresa B no sea afectada.
5. Consultar consolidado. Verificar: Consolidado = SUMA de empresas seleccionadas.
6. Usuario sin acceso a Empresa A intenta consultar información de Empresa A. Debe recibir acceso denegado (403).
7. Usuario con acceso a Empresa A y B puede cambiar entre ambas.
8. Usuario con acceso solamente a Empresa A no puede consultar Empresa B modificando parámetros de la API.
9. La suma mensual consolidada coincide con la suma mensual de las empresas.
10. La suma anual consolidada coincide con la suma anual de las empresas.
"""

from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import Base, Company, Category, Account, MonthlyExpense, User, UserCompanyRole
from calculator import calculate_budget_summary, calculate_corporate_consolidation
from main import app, get_db

def run_multicompany_tests():
    print("=" * 75)
    print("INICIANDO PRUEBAS OBLIGATORIAS — SPRINT MULTIEMPRESA & CONSOLIDACIÓN")
    print("=" * 75)

    # 1. Base de datos SQLite aislada en memoria para pruebas
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Sobrescribir dependencia de BD en FastAPI para pruebas de endpoints
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    # 2. Configurar Entidades de Prueba:
    # Empresa A: EDIMCA
    # Empresa B: PANELAT
    # Empresa C: COTOPAXI
    emp_a = Company(code="EDIMCA", name="EDIMCA S.A.", trade_name="EDIMCA", status="ACTIVO")
    emp_b = Company(code="PANELAT", name="PANELAT S.A.", trade_name="PANELAT", status="ACTIVO")
    emp_c = Company(code="COTOPAXI", name="Aglomerados Cotopaxi", trade_name="COTOPAXI", status="ACTIVO")
    db.add_all([emp_a, emp_b, emp_c])
    db.flush()

    # Usuarios para pruebas de seguridad:
    # user_a: solo acceso a Empresa A (EDIMCA)
    # user_ab: acceso a Empresa A y Empresa B
    # user_admin: superusuario
    user_a = User(username="user_edimca", email="user_a@edimca.com", is_superuser=False)
    user_ab = User(username="user_corporate", email="user_ab@corp.com", is_superuser=False)
    user_admin = User(username="admin_sys", email="admin@corp.com", is_superuser=True)
    db.add_all([user_a, user_ab, user_admin])
    db.flush()

    # Asignación de Roles
    db.add(UserCompanyRole(user_id=user_a.id, company_id=emp_a.id, role="PLANIFICADOR"))
    db.add(UserCompanyRole(user_id=user_ab.id, company_id=emp_a.id, role="PLANIFICADOR"))
    db.add(UserCompanyRole(user_id=user_ab.id, company_id=emp_b.id, role="PLANIFICADOR"))
    db.flush()

    # Categorías para Empresa A y Empresa B con el mismo nombre y código
    cat_a_tech = Category(company_id=emp_a.id, code="TEC", name="Tecnología")
    cat_b_tech = Category(company_id=emp_b.id, code="TEC", name="Tecnología")
    cat_c_ops = Category(company_id=emp_c.id, code="OPS", name="Operaciones")
    db.add_all([cat_a_tech, cat_b_tech, cat_c_ops])
    db.flush()

    # Cuentas con el mismo código contable y nombre en empresas distintas (AWS)
    acc_a_aws = Account(category_id=cat_a_tech.id, code="510100", name="AWS Cloud Services", provider="Amazon AWS")
    acc_b_aws = Account(category_id=cat_b_tech.id, code="510100", name="AWS Cloud Services", provider="Amazon AWS")
    acc_c_ops = Account(category_id=cat_c_ops.id, code="520100", name="Mantenimiento Industrial", provider="MaintCorp")
    db.add_all([acc_a_aws, acc_b_aws, acc_c_ops])
    db.flush()

    # -------------------------------------------------------------
    # PRUEBA 1: Crear presupuesto para Empresa A (2027) -> No en B
    # -------------------------------------------------------------
    print("Ejecutando Prueba 1: Aislamiento Empresa A -> Empresa B...")
    # Asignar $1,000.00 en cada mes de 2027 para Empresa A ($12,000.00 anual)
    for m in range(1, 13):
        db.add(MonthlyExpense(account_id=acc_a_aws.id, year=2027, month=m, amount=Decimal("1000.00")))
    db.commit()

    summary_a = calculate_budget_summary(db, company_id=emp_a.id, year=2027)
    summary_b = calculate_budget_summary(db, company_id=emp_b.id, year=2027)

    assert Decimal(summary_a["general_annual_total"]) == Decimal("12000.00"), "Fallo P1: Total Empresa A debe ser 12000.00"
    assert Decimal(summary_b["general_annual_total"]) == Decimal("0.00"), "Fallo P1: Empresa B no debe tener presupuesto de Empresa A"
    print("  [OK] Prueba 1 superada: Presupuesto de Empresa A no aparece en Empresa B.")

    # -------------------------------------------------------------
    # PRUEBA 2: Crear presupuesto para Empresa B (2027) -> No en A
    # -------------------------------------------------------------
    print("Ejecutando Prueba 2: Aislamiento Empresa B -> Empresa A...")
    # Asignar $2,500.00 en cada mes de 2027 para Empresa B ($30,000.00 anual)
    for m in range(1, 13):
        db.add(MonthlyExpense(account_id=acc_b_aws.id, year=2027, month=m, amount=Decimal("2500.00")))
    db.commit()

    summary_b_after = calculate_budget_summary(db, company_id=emp_b.id, year=2027)
    summary_a_after = calculate_budget_summary(db, company_id=emp_a.id, year=2027)

    assert Decimal(summary_b_after["general_annual_total"]) == Decimal("3000.00") * 10 or Decimal(summary_b_after["general_annual_total"]) == Decimal("30000.00")
    assert Decimal(summary_a_after["general_annual_total"]) == Decimal("12000.00"), "Fallo P2: Total Empresa A no debe alterarse"
    print("  [OK] Prueba 2 superada: Presupuesto de Empresa B no aparece en Empresa A.")

    # -------------------------------------------------------------
    # PRUEBA 3: Dos empresas pueden usar el mismo código de cuenta
    # -------------------------------------------------------------
    print("Ejecutando Prueba 3: Coexistencia de cuentas con mismo código y nombre...")
    assert acc_a_aws.code == acc_b_aws.code == "510100"
    assert acc_a_aws.name == acc_b_aws.name == "AWS Cloud Services"
    assert acc_a_aws.category.company_id == emp_a.id
    assert acc_b_aws.category.company_id == emp_b.id
    print("  [OK] Prueba 3 superada: Empresa A y Empresa B utilizan código 510100 sin conflicto.")

    # -------------------------------------------------------------
    # PRUEBA 4: Modificar una cuenta de Empresa A no afecta a Empresa B
    # -------------------------------------------------------------
    print("Ejecutando Prueba 4: Independencia en modificaciones...")
    # Cambiar mes de Diciembre en Empresa A a $1,500.00 (Total pasa a 12,500.00)
    exp_dec_a = db.query(MonthlyExpense).filter(
        MonthlyExpense.account_id == acc_a_aws.id,
        MonthlyExpense.year == 2027,
        MonthlyExpense.month == 12
    ).first()
    exp_dec_a.amount = Decimal("1500.00")
    db.commit()

    sum_a_mod = calculate_budget_summary(db, company_id=emp_a.id, year=2027)
    sum_b_check = calculate_budget_summary(db, company_id=emp_b.id, year=2027)

    assert Decimal(sum_a_mod["general_annual_total"]) == Decimal("12500.00")
    assert Decimal(sum_b_check["general_annual_total"]) == Decimal("30000.00")
    print("  [OK] Prueba 4 superada: Modificar Empresa A no alteró a Empresa B.")

    # Presupuesto para Empresa C ($500.00/mes -> $6,000.00 anual)
    for m in range(1, 13):
        db.add(MonthlyExpense(account_id=acc_c_ops.id, year=2027, month=m, amount=Decimal("500.00")))
    db.commit()

    # -------------------------------------------------------------
    # PRUEBA 5: Consultar consolidado = SUMA de empresas seleccionadas
    # -------------------------------------------------------------
    print("Ejecutando Prueba 5: Consolidado como suma de empresas seleccionadas...")
    # Consolidar Empresa A (12500) y Empresa B (30000) -> 42500.00
    cons_ab = calculate_corporate_consolidation(db, company_ids=[emp_a.id, emp_b.id], year=2027)
    assert Decimal(cons_ab["total_annual"]) == Decimal("42500.00"), f"Fallo P5: {cons_ab['total_annual']}"
    assert cons_ab["companies_count"] == 2

    # Consolidar Empresa A, B y C (12500 + 30000 + 6000) -> 48500.00
    cons_all = calculate_corporate_consolidation(db, company_ids=[emp_a.id, emp_b.id, emp_c.id], year=2027)
    assert Decimal(cons_all["total_annual"]) == Decimal("48500.00"), f"Fallo P5: {cons_all['total_annual']}"
    print("  [OK] Prueba 5 superada: El consolidado es exactamente la suma matemática.")

    # -------------------------------------------------------------
    # PRUEBA 6: Usuario sin acceso a Empresa A intenta consultar -> 403
    # -------------------------------------------------------------
    print("Ejecutando Prueba 6: Acceso denegado a usuario no autorizado...")
    # Crear usuario sin acceso
    user_no_access = User(username="unauthorized_user", email="no_access@corp.com", is_superuser=False)
    db.add(user_no_access)
    db.commit()

    response = client.get(f"/api/budget-summary?company_id={emp_a.id}&year=2027", headers={"X-User": "unauthorized_user"})
    assert response.status_code == 403, f"Fallo P6: Status esperado 403, recibido {response.status_code}"
    print("  [OK] Prueba 6 superada: Usuario no autorizado recibe HTTP 403 Forbidden.")

    # -------------------------------------------------------------
    # PRUEBA 7: Usuario con acceso a Empresa A y B puede alternar
    # -------------------------------------------------------------
    print("Ejecutando Prueba 7: Alternancia de contexto para usuario multiempresa...")
    res_a = client.get(f"/api/budget-summary?company_id={emp_a.id}&year=2027", headers={"X-User": "user_corporate"})
    assert res_a.status_code == 200
    assert res_a.json()["company_code"] == "EDIMCA"
    assert res_a.json()["general_annual_total"] == "12500.00"

    res_b = client.get(f"/api/budget-summary?company_id={emp_b.id}&year=2027", headers={"X-User": "user_corporate"})
    assert res_b.status_code == 200
    assert res_b.json()["company_code"] == "PANELAT"
    assert res_b.json()["general_annual_total"] == "30000.00"
    print("  [OK] Prueba 7 superada: Usuario multiempresa alterna libremente entre empresas autorizadas.")

    # -------------------------------------------------------------
    # PRUEBA 8: Usuario con solo Empresa A no puede saltar a Empresa B vía API
    # -------------------------------------------------------------
    print("Ejecutando Prueba 8: Prevención de escalamiento horizontal de parámetros...")
    res_tamper = client.get(f"/api/budget-summary?company_id={emp_b.id}&year=2027", headers={"X-User": "user_edimca"})
    assert res_tamper.status_code == 403, f"Fallo P8: Debe bloquear petición manipulada, status: {res_tamper.status_code}"
    print("  [OK] Prueba 8 superada: Manipulación de company_id en la API bloqueada con 403.")

    # -------------------------------------------------------------
    # PRUEBA 9: Suma mensual consolidada coincide con suma de empresas
    # -------------------------------------------------------------
    print("Ejecutando Prueba 9: Coherencia mensual de la consolidación...")
    # Enero: A(1000) + B(2500) + C(500) = 4000.00
    assert cons_all["consolidated_monthly_totals"][1] == "4000.00"
    # Diciembre: A(1500) + B(2500) + C(500) = 4500.00
    assert cons_all["consolidated_monthly_totals"][12] == "4500.00"

    for m in range(1, 13):
        expected_m = Decimal(summary_a["general_monthly_totals"][m]) if m != 12 else Decimal("1500.00")
        expected_m += Decimal(summary_b_after["general_monthly_totals"][m])
        expected_m += Decimal("500.00")
        assert Decimal(cons_all["consolidated_monthly_totals"][m]) == expected_m, f"Fallo P9 en mes {m}"
    print("  [OK] Prueba 9 superada: Los 12 meses consolidados coinciden con la suma de meses individuales.")

    # -------------------------------------------------------------
    # PRUEBA 10: Suma anual consolidada y cuadre cruzado
    # -------------------------------------------------------------
    print("Ejecutando Prueba 10: Cuadre cruzado anual y vertical del consolidado...")
    sum_12_cons = sum(Decimal(cons_all["consolidated_monthly_totals"][m]) for m in range(1, 13))
    total_cons = Decimal(cons_all["total_annual"])
    assert sum_12_cons == total_cons, f"Fallo P10: {sum_12_cons} != {total_cons}"
    assert cons_all["is_balanced"] is True, "Fallo P10: is_balanced debe ser True"
    print("  [OK] Prueba 10 superada: Cuadre horizontal vs vertical de consolidación perfecto.")

    # -------------------------------------------------------------
    # PRUEBA 11: Agregar empresa adicional en caliente y validar replicación base de EDIMCA (Base 0)
    # -------------------------------------------------------------
    print("Ejecutando Prueba 11: Creación de empresa adicional con replicación automática de estructura EDIMCA (Base 0)...")
    res_new_comp = client.post("/api/companies", json={
        "code": "NOVOPAN",
        "name": "Novopan del Ecuador S.A.",
        "trade_name": "NOVOPAN",
        "tax_id": "1790077889001",
        "status": "ACTIVO"
    }, headers={"X-User": "admin_sys"})
    assert res_new_comp.status_code == 201, f"Fallo P11: {res_new_comp.text}"
    new_comp_id = res_new_comp.json()["id"]

    # Verificar que hereda la estructura de EDIMCA y sus gastos inician estrictamente en Base 0 ($0.00)
    sum_new = calculate_budget_summary(db, company_id=new_comp_id, year=2027)
    assert len(sum_new["categories"]) == 1, "Fallo P11: Nueva empresa debe heredar la categoría de EDIMCA"
    assert sum_new["categories"][0]["name"] == "Tecnología"
    assert len(sum_new["categories"][0]["accounts"]) == 1
    assert sum_new["categories"][0]["accounts"][0]["name"] == "AWS Cloud Services"
    assert Decimal(sum_new["general_annual_total"]) == Decimal("0.00"), "Fallo P11: Total inicial debe ser 0.00 (Base 0)"

    # Verificar que aparece en el catálogo de empresas
    res_list = client.get("/api/companies", headers={"X-User": "admin_sys"})
    assert any(c["code"] == "NOVOPAN" for c in res_list.json())

    # Crear una categoría adicional específica para la nueva empresa
    cat_novo = Category(company_id=new_comp_id, code="IND", name="Operaciones Industriales")
    db.add(cat_novo)
    db.flush()
    acc_novo = Account(category_id=cat_novo.id, code="510200", name="Servidores Locales", provider="Dell EMC")
    db.add(acc_novo)
    db.flush()

    # Planificar 2027 para NOVOPAN ($2,000/mes -> $24,000 anual)
    for m in range(1, 13):
        db.add(MonthlyExpense(account_id=acc_novo.id, year=2027, month=m, amount=Decimal("2000.00")))
    db.commit()

    # Consolidado con la nueva empresa: A(12500) + B(30000) + C(6000) + NOVOPAN(24000) = 72500.00
    cons_with_novo = calculate_corporate_consolidation(db, company_ids=[emp_a.id, emp_b.id, emp_c.id, new_comp_id], year=2027)
    assert Decimal(cons_with_novo["total_annual"]) == Decimal("72500.00"), f"Fallo P11 en consolidado: {cons_with_novo['total_annual']}"
    assert cons_with_novo["companies_count"] == 4
    print("  [OK] Prueba 11 superada: Nueva empresa creada en caliente, heredó catálogo de EDIMCA en Base 0 y consolida con exactitud.")

    # -------------------------------------------------------------
    # PRUEBA 12: Endpoint de replicación de estructura EDIMCA a empresas existentes
    # -------------------------------------------------------------
    print("Ejecutando Prueba 12: Replicación de estructura EDIMCA a empresa existente (COTOPAXI)...")
    res_repl = client.post(f"/api/companies/{emp_c.id}/replicate-from-edimca", headers={"X-User": "admin_sys"})
    assert res_repl.status_code == 200, f"Fallo P12: {res_repl.text}"
    # COTOPAXI tenía 'Operaciones', ahora debe tener además 'Tecnología' y 'AWS Cloud Services'
    sum_c_after = calculate_budget_summary(db, company_id=emp_c.id, year=2027)
    cat_names_c = [c["name"] for c in sum_c_after["categories"]]
    assert "Tecnología" in cat_names_c, "Fallo P12: COTOPAXI debe tener ahora categoría 'Tecnología'"
    # El presupuesto previo de COTOPAXI se mantiene intacto ($6,000.00)
    assert Decimal(sum_c_after["general_annual_total"]) == Decimal("6000.00"), "Fallo P12: Presupuesto existente no debe verse alterado (Base 0 para cuentas nuevas)"
    print("  [OK] Prueba 12 superada: Replicación a empresa existente preserva presupuestos y añade catálogo faltante.")

    # -------------------------------------------------------------
    # PRUEBA 13: Modificar datos de la empresa y validar persistencia y auditoría
    # -------------------------------------------------------------
    print("Ejecutando Prueba 13: Modificación de datos de empresa y auditoría...")
    res_update_comp = client.put(f"/api/companies/{new_comp_id}", json={
        "code": "NOVOPAN-EC",
        "name": "Novopan del Ecuador Corporación S.A.",
        "trade_name": "NOVOPAN INDUSTRIAL",
        "tax_id": "1790077889002",
        "status": "ACTIVO"
    }, headers={"X-User": "admin_sys"})
    assert res_update_comp.status_code == 200, f"Fallo P12: {res_update_comp.text}"
    updated_data = res_update_comp.json()
    assert updated_data["code"] == "NOVOPAN-EC"
    assert updated_data["name"] == "Novopan del Ecuador Corporación S.A."
    assert updated_data["trade_name"] == "NOVOPAN INDUSTRIAL"

    # Verificar registro en auditoría
    res_audits = client.get(f"/api/audit-logs?company_id={new_comp_id}", headers={"X-User": "admin_sys"})
    assert any(a["action"] == "UPDATE_COMPANY" for a in res_audits.json())
    print("  [OK] Prueba 13 superada: Datos de la empresa modificados correctamente y auditados con éxito.")

    print("=" * 75)
    print("¡TODAS LAS PRUEBAS (13/13) DEL SPRINT PASARON EXITOSAMENTE!")
    print("=" * 75)
    db.close()

if __name__ == "__main__":
    run_multicompany_tests()
