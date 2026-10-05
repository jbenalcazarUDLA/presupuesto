import os
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint, create_engine, text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "presupuesto.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# =========================================================================
# MODELOS DE BASE DE DATOS — SPRINT MULTIEMPRESA & CORPORATIVO
# =========================================================================

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(150), nullable=False)
    trade_name = Column(String(150), default="", nullable=True)
    tax_id = Column(String(20), unique=True, nullable=True)
    status = Column(String(20), default="ACTIVO", nullable=False)  # ACTIVO / INACTIVO
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    categories = relationship("Category", back_populates="company", cascade="all, delete-orphan", order_by="Category.id")
    user_roles = relationship("UserCompanyRole", back_populates="company", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="company")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), default="", nullable=True)
    name = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_company_category_name"),
    )

    company = relationship("Company", back_populates="categories")
    accounts = relationship("Account", back_populates="category", cascade="all, delete-orphan", order_by="Account.name")

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), default="", nullable=True)
    name = Column(String(150), nullable=False)
    provider = Column(String(150), default="", nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    category = relationship("Category", back_populates="accounts")
    monthly_expenses = relationship("MonthlyExpense", back_populates="account", cascade="all, delete-orphan")

class MonthlyExpense(Base):
    __tablename__ = "monthly_expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False, default=2026, index=True)
    month = Column(Integer, nullable=False)  # 1 al 12
    amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    __table_args__ = (
        UniqueConstraint("account_id", "year", "month", name="uq_account_year_month"),
        CheckConstraint("month >= 1 AND month <= 12", name="check_month_range"),
        CheckConstraint("amount >= 0.00", name="check_amount_non_negative"),
    )

    account = relationship("Account", back_populates="monthly_expenses")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(150), default="", nullable=True)
    is_superuser = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    roles = relationship("UserCompanyRole", back_populates="user", cascade="all, delete-orphan")

class UserCompanyRole(Base):
    __tablename__ = "user_company_roles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(30), default="PLANIFICADOR", nullable=False)  # ADMINISTRADOR, PLANIFICADOR, CONSULTA

    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company_role"),
    )

    user = relationship("User", back_populates="roles")
    company = relationship("Company", back_populates="user_roles")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(50), default="system", nullable=False)
    action = Column(String(50), default="UPDATE", nullable=False)
    year = Column(Integer, nullable=False)
    category_name = Column(String(100), default="", nullable=True)
    account_id = Column(Integer, nullable=True)
    account_name = Column(String(150), default="", nullable=True)
    month = Column(Integer, nullable=True)
    old_amount = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    new_amount = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    company = relationship("Company", back_populates="audit_logs")

# =========================================================================
# MIGRACIÓN DEFENSIVA Y SEMILLAS
# =========================================================================

def init_db():
    Base.metadata.create_all(bind=engine)

    with engine.connect() as conn:
        # 1. Asegurar catálogo inicial de empresas si está vacío
        try:
            res_comp = conn.execute(text("SELECT COUNT(*) FROM companies")).scalar()
            if res_comp == 0:
                print("[MIGRACIÓN] Creando empresas corporativas iniciales...")
                conn.execute(text("""
                    INSERT INTO companies (code, name, trade_name, tax_id, status, created_at, updated_at)
                    VALUES 
                    ('EDIMCA', 'EDIMCA S.A.', 'EDIMCA', '1790012345001', 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('PANELAT', 'PANELAT S.A.', 'PANELAT', '1790098765001', 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                    ('COTOPAXI', 'Aglomerados Cotopaxi S.A.', 'COTOPAXI', '1790055544001', 'ACTIVO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """))
                conn.commit()
                print("[MIGRACIÓN] Empresas iniciales creadas.")
        except Exception as e:
            print(f"[MIGRACIÓN INFO] {e}")

        # Obtener el ID de EDIMCA para asociar datos huérfanos preexistentes
        default_company_id = 1
        try:
            row = conn.execute(text("SELECT id FROM companies WHERE code = 'EDIMCA'")).fetchone()
            if row:
                default_company_id = row[0]
        except Exception:
            pass

        # 2. Migración defensiva de la tabla categories (agregar company_id si falta)
        try:
            result = conn.execute(text("PRAGMA table_info(categories)"))
            cols = [row[1] for row in result.fetchall()]
            if cols and "company_id" not in cols:
                print("[MIGRACIÓN] Migrando categories a estructura multiempresa...")
                conn.execute(text(f"""
                    CREATE TABLE categories_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id INTEGER NOT NULL DEFAULT {default_company_id} REFERENCES companies(id) ON DELETE CASCADE,
                        code VARCHAR(50) DEFAULT '',
                        name VARCHAR(100) NOT NULL,
                        CONSTRAINT uq_company_category_name UNIQUE (company_id, name)
                    )
                """))
                conn.execute(text(f"""
                    INSERT INTO categories_temp (id, company_id, code, name)
                    SELECT id, {default_company_id}, '', name FROM categories
                """))
                conn.execute(text("DROP TABLE categories"))
                conn.execute(text("ALTER TABLE categories_temp RENAME TO categories"))
                conn.commit()
                print("[MIGRACIÓN] Tabla categories actualizada con éxito.")
        except Exception as e:
            print(f"[MIGRACIÓN INFO] {e}")

        # 3. Migración defensiva de accounts: proveedor y código
        try:
            result = conn.execute(text("PRAGMA table_info(accounts)"))
            cols = [row[1] for row in result.fetchall()]
            if cols and "provider" not in cols:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN provider VARCHAR(150) DEFAULT ''"))
                conn.commit()
            if cols and "code" not in cols:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN code VARCHAR(50) DEFAULT ''"))
                conn.commit()
            if cols and "is_active" not in cols:
                conn.execute(text("ALTER TABLE accounts ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                conn.commit()
        except Exception as e:
            print(f"[MIGRACIÓN INFO] {e}")

        # 4. Migración defensiva de monthly_expenses: soporte multianual ('year')
        try:
            result = conn.execute(text("PRAGMA table_info(monthly_expenses)"))
            cols = [row[1] for row in result.fetchall()]
            if cols and "year" not in cols:
                print("[MIGRACIÓN] Migrando monthly_expenses a soporte multianual...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS monthly_expenses_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                        year INTEGER NOT NULL DEFAULT 2026,
                        month INTEGER NOT NULL,
                        amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
                        CONSTRAINT uq_account_year_month UNIQUE (account_id, year, month),
                        CONSTRAINT check_month_range CHECK (month >= 1 AND month <= 12),
                        CONSTRAINT check_amount_non_negative CHECK (amount >= 0.00)
                    )
                """))
                conn.execute(text("""
                    INSERT INTO monthly_expenses_temp (id, account_id, year, month, amount)
                    SELECT id, account_id, 2026, month, amount FROM monthly_expenses
                """))
                conn.execute(text("DROP TABLE monthly_expenses"))
                conn.execute(text("ALTER TABLE monthly_expenses_temp RENAME TO monthly_expenses"))
                conn.commit()
                print("[MIGRACIÓN] Tabla monthly_expenses migrada exitosamente.")
        except Exception as e:
            print(f"[MIGRACIÓN INFO] {e}")

        # 5. Usuarios iniciales para control de acceso y pruebas
        try:
            res_users = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            if res_users == 0:
                print("[MIGRACIÓN] Creando usuarios y roles iniciales...")
                conn.execute(text("""
                    INSERT INTO users (username, email, full_name, is_superuser, is_active, created_at)
                    VALUES 
                    ('admin', 'admin@corporativo.com', 'Administrador General', 1, 1, CURRENT_TIMESTAMP),
                    ('jhon', 'jhon@edimca.com', 'Jhon Planificador EDIMCA', 0, 1, CURRENT_TIMESTAMP),
                    ('mariana', 'mariana@corporativo.com', 'Mariana Multiempresa', 0, 1, CURRENT_TIMESTAMP)
                """))
                conn.commit()

                # Asignar roles:
                # admin tiene acceso total por is_superuser
                # jhon -> PLANIFICADOR en EDIMCA (id 1)
                # mariana -> CONSULTA en EDIMCA (id 1), PLANIFICADOR en PANELAT (id 2)
                conn.execute(text(f"""
                    INSERT INTO user_company_roles (user_id, company_id, role)
                    VALUES 
                    (2, {default_company_id}, 'PLANIFICADOR'),
                    (3, {default_company_id}, 'CONSULTA'),
                    (3, 2, 'PLANIFICADOR')
                """))
                conn.commit()
                print("[MIGRACIÓN] Usuarios y roles configurados.")
        except Exception as e:
            print(f"[MIGRACIÓN INFO] {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
