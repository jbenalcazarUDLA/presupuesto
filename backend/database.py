import os
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint, CheckConstraint, create_engine, text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "presupuesto.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)

    accounts = relationship("Account", back_populates="category", cascade="all, delete-orphan", order_by="Account.id")

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    provider = Column(String(150), default="", nullable=True)

    category = relationship("Category", back_populates="accounts")
    monthly_expenses = relationship("MonthlyExpense", back_populates="account", cascade="all, delete-orphan")

class MonthlyExpense(Base):
    __tablename__ = "monthly_expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    month = Column(Integer, nullable=False)  # 1 al 12
    amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    __table_args__ = (
        UniqueConstraint("account_id", "month", name="uq_account_month"),
        CheckConstraint("month >= 1 AND month <= 12", name="check_month_range"),
        CheckConstraint("amount >= 0.00", name="check_amount_non_negative"),
    )

    account = relationship("Account", back_populates="monthly_expenses")

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Auto-migración defensiva: asegurar que exista la columna 'provider' en la tabla 'accounts'
    # en caso de que la base de datos se haya creado antes de agregar este campo.
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(accounts)"))
            cols = [row[1] for row in result.fetchall()]
            if cols and "provider" not in cols:
                print("[MIGRACIÓN] Agregando columna 'provider' a la tabla accounts...")
                conn.execute(text("ALTER TABLE accounts ADD COLUMN provider VARCHAR(150) DEFAULT ''"))
                conn.commit()
                print("[MIGRACIÓN] Columna 'provider' agregada con éxito.")
        except Exception as e:
            print(f"[MIGRACIÓN INFO] {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
