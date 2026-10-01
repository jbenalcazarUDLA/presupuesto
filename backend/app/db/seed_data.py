from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.budget_year import BudgetYear
from app.models.category import Category
from app.models.account import Account
from app.models.projection import BudgetMonthlyProjection
from app.core.decimal_math import to_decimal

# Catálogo estructurado de Tecnología EDIMCA
INITIAL_CATALOG = [
    {
        "code": "CAT-ALQ-EQUIP",
        "name": "Alquiler de equipos de computación",
        "display_order": 1,
        "accounts": [
            {"code": "00282239-1", "name": "Impresoras, Contrato de Outsourcing Ecuador - KM", "responsible": "amoreno", "provider": "KMSolutions", "display_order": 1},
            {"code": "00282239-2", "name": "Ciberseguridad: Backups Acronis / Nakivo", "responsible": "amoreno", "provider": "Megasetec", "display_order": 2},
            {"code": "00282239-3", "name": "Servidores Nube Cirion / Lumen (incluye SQL)", "responsible": "amoreno", "provider": "Cirion", "display_order": 3},
            {"code": "00282239-4", "name": "Incremento de recursos servidores Data Analytics", "responsible": "amoreno", "provider": "Cirion", "display_order": 4},
            {"code": "00282239-5", "name": "Contrato Outsourcing Impresoras Nuevas Tiendas", "responsible": "amoreno", "provider": "KMSolutions", "display_order": 5},
            {"code": "00282239-6", "name": "Servidor Hosting Olbitre", "responsible": "amoreno", "provider": "Hernández Trávez", "display_order": 6},
            {"code": "00282239-7", "name": "Incremento memoria BD Oracle 40GB", "responsible": "kjimenez", "provider": "Cirion", "display_order": 7},
            {"code": "00282239-8", "name": "Incremento storage BD Oracle 200GB", "responsible": "kjimenez", "provider": "Cirion", "display_order": 8}
        ]
    },
    {
        "code": "CAT-ALQ-SOFT",
        "name": "Alquiler software",
        "display_order": 2,
        "accounts": [
            {"code": "00306193-1", "name": "Cuenta ZOOM webinar (500 part) + meetings", "responsible": "amoreno", "provider": "ZOOM", "display_order": 1},
            {"code": "00306193-2", "name": "Licencias Kitchen Draw contratadas", "responsible": "henry", "provider": "Metalword", "display_order": 2},
            {"code": "00306193-3", "name": "Proyecto WhatsApp departamento de retail", "responsible": "amoreno", "provider": "Syscommservice", "display_order": 3},
            {"code": "00306193-4", "name": "Licencias Microsoft M365 contratadas", "responsible": "amoreno", "provider": "Innova", "display_order": 4},
            {"code": "00306193-5", "name": "Licencia SketchUp Pro", "responsible": "jguaman", "provider": "Innova", "display_order": 5},
            {"code": "00306193-6", "name": "Licencia Lumion", "responsible": "jguaman", "provider": "Innova", "display_order": 6},
            {"code": "00306193-7", "name": "Licencias proyecto RPA Finanzas", "responsible": "cotopaxi", "provider": "Microsoft", "display_order": 7},
            {"code": "00306193-8", "name": "Licencias PURVIEW (Clasificación de Información)", "responsible": "amoreno", "provider": "Innova", "display_order": 8}
        ]
    },
    {
        "code": "CAT-COM",
        "name": "Comunicaciones",
        "display_order": 3,
        "accounts": [
            {"code": "00271699-1", "name": "Matriz Eloy Alfaro Quito (80MB) e Internet", "responsible": "amoreno", "provider": "Cirion", "display_order": 1},
            {"code": "00271699-2", "name": "Internet para servidores en nube Cirion", "responsible": "amoreno", "provider": "Cirion", "display_order": 2},
            {"code": "00271699-3", "name": "Enlace Datos Sucursal Cotocollao", "responsible": "amoreno", "provider": "Cirion", "display_order": 3},
            {"code": "00271699-4", "name": "Enlace Datos Sucursal San Rafael", "responsible": "amoreno", "provider": "Cirion", "display_order": 4},
            {"code": "00271699-5", "name": "Enlace Datos Sucursal San Bartolo Sur", "responsible": "amoreno", "provider": "Cirion", "display_order": 5},
            {"code": "00271699-6", "name": "Enlace Datos Sucursal Mariscal Sucre", "responsible": "amoreno", "provider": "Cirion", "display_order": 6},
            {"code": "00271699-7", "name": "Enlace Datos Sucursal Tumbaco", "responsible": "amoreno", "provider": "Cirion", "display_order": 7},
            {"code": "00271699-8", "name": "Enlace Datos Sucursal Ibarra", "responsible": "amoreno", "provider": "Cirion", "display_order": 8},
            {"code": "00271699-9", "name": "Enlace Datos Sucursal Ambato", "responsible": "amoreno", "provider": "Cirion", "display_order": 9},
            {"code": "00271699-10", "name": "Enlace Corporativo 194 (10 MB)", "responsible": "amoreno", "provider": "Cirion", "display_order": 10},
            {"code": "00271699-11", "name": "Nuevas Sucursales Red SDWAN", "responsible": "amoreno", "provider": "Cirion", "display_order": 11}
        ]
    },
    {
        "code": "CAT-INT",
        "name": "Internet",
        "display_order": 4,
        "accounts": [
            {"code": "00271698-1", "name": "Internet Pymes Celerity Guamaní y Mariscal", "responsible": "henriquez", "provider": "Celerity", "display_order": 1},
            {"code": "00271698-2", "name": "Tarjetas BAM Claro", "responsible": "amoreno", "provider": "Conecel", "display_order": 2},
            {"code": "00271698-3", "name": "Renovación Dominios (edimca, inspire, gemcorp)", "responsible": "jguaman", "provider": "Varios", "display_order": 3}
        ]
    },
    {
        "code": "CAT-MNT-EQUIP",
        "name": "Mantenimiento equipos de cómputo",
        "display_order": 5,
        "accounts": [
            {"code": "00276190-1", "name": "Servidores IBM (Active Directory, Backup)", "responsible": "amoreno", "provider": "Megasetec", "display_order": 1},
            {"code": "00276190-2", "name": "Servidor HP (Cubos OLAP)", "responsible": "amoreno", "provider": "Megasetec", "display_order": 2},
            {"code": "00276190-3", "name": "Mantenimiento Data Center e Inclusión UPS", "responsible": "amoreno", "provider": "Surge", "display_order": 3},
            {"code": "00276190-4", "name": "Redes y comunicaciones (Cableado bajo demanda)", "responsible": "amoreno", "provider": "Surge", "display_order": 4},
            {"code": "00276190-5", "name": "Servicios de soporte técnico externo", "responsible": "amoreno", "provider": "Externo", "display_order": 5},
            {"code": "00276190-6", "name": "Cambio de baterías UPS en puntos de venta", "responsible": "amoreno", "provider": "Varios", "display_order": 6},
            {"code": "00276190-7", "name": "Mantenimiento preventivo Racks tiendas", "responsible": "amoreno", "provider": "Varios", "display_order": 7},
            {"code": "00276190-8", "name": "Mantenimiento Servidor DHCP Guayaquil", "responsible": "amoreno", "provider": "Megasetec", "display_order": 8}
        ]
    },
    {
        "code": "CAT-MNT-SOFT",
        "name": "Mantenimiento software",
        "display_order": 6,
        "accounts": [
            {"code": "00313131-1", "name": "Base de Datos Oracle (Servicios Técnicos)", "responsible": "kjimenez", "provider": "ITCabarique", "display_order": 1},
            {"code": "00313131-2", "name": "Base de Datos Postgres: Tuning y Fixing", "responsible": "gbrito", "provider": "Lumen", "display_order": 2},
            {"code": "00313131-3", "name": "Mantenimiento Software y MAE", "responsible": "amoreno", "provider": "Genasys", "display_order": 3},
            {"code": "00313131-4", "name": "JDE Servicios Técnicos", "responsible": "kjimenez", "provider": "MAUSS", "display_order": 4}
        ]
    },
    {
        "code": "CAT-SOP-LIC",
        "name": "Renovación soporte licencias",
        "display_order": 7,
        "accounts": [
            {"code": "00334985-1", "name": "JDEdwards (Soporte Anual ERP Oracle)", "responsible": "kjimenez", "provider": "Nexsys", "display_order": 1},
            {"code": "00334985-2", "name": "AutoCAD / ZWCAD Licencias", "responsible": "jguaman", "provider": "Vera Quintana", "display_order": 2},
            {"code": "00334985-3", "name": "Adobe Creative Cloud", "responsible": "jguaman", "provider": "Vera Quintana", "display_order": 3},
            {"code": "00334985-4", "name": "Lepton Soporte Anual", "responsible": "gbrito", "provider": "Lepton", "display_order": 4},
            {"code": "00334985-5", "name": "Virtualizador VMware Soporte", "responsible": "amoreno", "provider": "Megasetec", "display_order": 5},
            {"code": "00334985-6", "name": "Renovación Licencias AP HP Aruba", "responsible": "amoreno", "provider": "Aruba", "display_order": 6}
        ]
    },
    {
        "code": "CAT-UTILES",
        "name": "Útiles de computación",
        "display_order": 8,
        "accounts": [
            {"code": "00271770-1", "name": "Mouse y teclados", "responsible": "amoreno", "provider": "Varios", "display_order": 1},
            {"code": "00271770-2", "name": "Pilas y baterías laptops", "responsible": "amoreno", "provider": "Varios", "display_order": 2},
            {"code": "00271770-3", "name": "Cargadores de poder laptops", "responsible": "amoreno", "provider": "Varios", "display_order": 3},
            {"code": "00271770-4", "name": "Mochilas y maletines", "responsible": "amoreno", "provider": "Varios", "display_order": 4},
            {"code": "00271770-5", "name": "Memorias RAM", "responsible": "amoreno", "provider": "Varios", "display_order": 5},
            {"code": "00271770-6", "name": "Fuentes de poder CPU", "responsible": "amoreno", "provider": "Varios", "display_order": 6},
            {"code": "00271770-7", "name": "Tinta y consumibles", "responsible": "amoreno", "provider": "Varios", "display_order": 7}
        ]
    },
    {
        "code": "CAT-CIBERSEG",
        "name": "Ciberseguridad",
        "display_order": 9,
        "accounts": [
            {"code": "CIB-01", "name": "CISO Externo", "responsible": "amoreno", "provider": "Externo", "display_order": 1},
            {"code": "CIB-02", "name": "Anti-malware y anti-spam SOPHOS", "responsible": "amoreno", "provider": "GMS", "display_order": 2},
            {"code": "CIB-03", "name": "Security Rating", "responsible": "amoreno", "provider": "GMS", "display_order": 3},
            {"code": "CIB-04", "name": "Solución EDR/XDR contra Ransomware", "responsible": "amoreno", "provider": "InforC", "display_order": 4},
            {"code": "CIB-05", "name": "Doble Factor de Autenticación 2FA Active Directory", "responsible": "amoreno", "provider": "InforC", "display_order": 5},
            {"code": "CIB-06", "name": "Certificados Digitales (JDE, POS, MAE)", "responsible": "kjimenez", "provider": "InforC", "display_order": 6}
        ]
    },
    {
        "code": "CAT-VIATICOS",
        "name": "Viáticos",
        "display_order": 10,
        "accounts": [
            {"code": "00361703", "name": "Viáticos: Alimentación", "responsible": "tecnologia", "provider": "Varios", "display_order": 1},
            {"code": "00361702", "name": "Viáticos: Hospedaje", "responsible": "tecnologia", "provider": "Varios", "display_order": 2},
            {"code": "00361704", "name": "Viáticos: Movilización", "responsible": "tecnologia", "provider": "Varios", "display_order": 3},
            {"code": "00361705", "name": "Viáticos: Pasajes aéreos", "responsible": "tecnologia", "provider": "Varios", "display_order": 4}
        ]
    },
    {
        "code": "CAT-ERGONOMIA",
        "name": "Equipos ergonómicos",
        "display_order": 11,
        "accounts": [
            {"code": "ERG-01", "name": "Elevadores y soportes ergonómicos", "responsible": "amoreno", "provider": "Varios", "display_order": 1},
            {"code": "ERG-02", "name": "Mouse y teclados ergonómicos", "responsible": "amoreno", "provider": "Varios", "display_order": 2}
        ]
    }
]

def seed_database(db: Session):
    """
    Carga el catálogo maestro y datos iniciales reales de los presupuestos 2024, 2025 y 2026.
    """
    # 1. Crear años presupuestarios
    years = [2024, 2025, 2026]
    for y in years:
        existing = db.query(BudgetYear).filter(BudgetYear.year == y).first()
        if not existing:
            by = BudgetYear(
                year=y,
                status="DRAFT" if y == 2026 else "APPROVED",
                notes=f"Presupuesto de Tecnología {y} - EDIMCA"
            )
            db.add(by)
    db.commit()

    # 2. Crear categorías y cuentas
    account_lookup = {}
    for cat_data in INITIAL_CATALOG:
        cat = db.query(Category).filter(Category.code == cat_data["code"]).first()
        if not cat:
            cat = Category(
                code=cat_data["code"],
                name=cat_data["name"],
                display_order=cat_data["display_order"],
                is_active=True
            )
            db.add(cat)
            db.flush()

        for acc_data in cat_data["accounts"]:
            acc = db.query(Account).filter(Account.category_id == cat.id, Account.name == acc_data["name"]).first()
            if not acc:
                acc = Account(
                    category_id=cat.id,
                    code=acc_data["code"],
                    name=acc_data["name"],
                    responsible=acc_data["responsible"],
                    provider=acc_data["provider"],
                    display_order=acc_data["display_order"],
                    is_active=True
                )
                db.add(acc)
                db.flush()
            account_lookup[(cat.code, acc.name)] = acc.id
    db.commit()

    # 3. Precargar algunas proyecciones de ejemplo basadas en los datos reales del archivo adjunto
    # Ejemplo para 2026:
    seed_2026_values = [
        # Impresoras KM
        (("CAT-ALQ-EQUIP", "Impresoras, Contrato de Outsourcing Ecuador - KM"), [Decimal("4100.00")] * 12),
        # Backups Nakivo
        (("CAT-ALQ-EQUIP", "Ciberseguridad: Backups Acronis / Nakivo"), [Decimal("274.00")] * 12),
        # Servidores Nube Cirion
        (("CAT-ALQ-EQUIP", "Servidores Nube Cirion / Lumen (incluye SQL)"), [Decimal("9907.00")] * 12),
        # Zoom
        (("CAT-ALQ-SOFT", "Cuenta ZOOM webinar (500 part) + meetings"), [Decimal("78.23")] * 12),
        # KitchenDraw
        (("CAT-ALQ-SOFT", "Licencias Kitchen Draw contratadas"), [Decimal("3167.50")] * 12),
        # WhatsApp retail
        (("CAT-ALQ-SOFT", "Proyecto WhatsApp departamento de retail"), [Decimal("400.00")] * 12),
        # Microsoft M365
        (("CAT-ALQ-SOFT", "Licencias Microsoft M365 contratadas"), [Decimal("3652.00")] * 12),
        # Matriz Quito
        (("CAT-COM", "Matriz Eloy Alfaro Quito (80MB) e Internet"), [Decimal("462.00")] * 12),
        # Enlace Cotocollao
        (("CAT-COM", "Enlace Datos Sucursal Cotocollao"), [Decimal("142.00")] * 12),
        # Celerity
        (("CAT-INT", "Internet Pymes Celerity Guamaní y Mariscal"), [Decimal("85.22")] * 12),
        # Mantenimiento Servidor IBM
        (("CAT-MNT-EQUIP", "Servidores IBM (Active Directory, Backup)"), [Decimal("65.00")] * 12),
        # Mantenimiento Servidor HP
        (("CAT-MNT-EQUIP", "Servidor HP (Cubos OLAP)"), [Decimal("56.25")] * 12),
        # Soporte ERP JDE
        (("CAT-SOP-LIC", "JDEdwards (Soporte Anual ERP Oracle)"), [Decimal("1541.79")] * 12),
        # Soporte Lepton
        (("CAT-SOP-LIC", "Lepton Soporte Anual"), [Decimal("3990.00")] * 12),
        # Útiles
        (("CAT-UTILES", "Mouse y teclados"), [Decimal("30.00")] * 12),
        (("CAT-UTILES", "Pilas y baterías laptops"), [Decimal("165.00")] * 12),
        (("CAT-UTILES", "Cargadores de poder laptops"), [Decimal("140.00")] * 12),
        # Ciberseguridad CISO
        (("CAT-CIBERSEG", "CISO Externo"), [Decimal("700.00")] * 12),
        (("CAT-CIBERSEG", "Anti-malware y anti-spam SOPHOS"), [Decimal("275.00")] * 12),
        # Viáticos
        (("CAT-VIATICOS", "Viáticos: Movilización"), [Decimal("118.00")] * 12),
        # Ergonómicos
        (("CAT-ERGONOMIA", "Mouse y teclados ergonómicos"), [Decimal("150.00")] * 12),
    ]

    for (cat_code, acc_name), monthly_amts in seed_2026_values:
        acc_id = account_lookup.get((cat_code, acc_name))
        if not acc_id:
            continue
        for month_idx, amt in enumerate(monthly_amts, start=1):
            existing_proj = db.query(BudgetMonthlyProjection).filter(
                BudgetMonthlyProjection.year == 2026,
                BudgetMonthlyProjection.account_id == acc_id,
                BudgetMonthlyProjection.month == month_idx
            ).first()
            if not existing_proj:
                proj = BudgetMonthlyProjection(
                    year=2026,
                    account_id=acc_id,
                    month=month_idx,
                    amount=amt
                )
                db.add(proj)

    db.commit()
