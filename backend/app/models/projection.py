from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base

class BudgetMonthlyProjection(Base):
    __tablename__ = "budget_monthly_projections"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    year = Column(Integer, ForeignKey("budget_years.year", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    month = Column(Integer, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("year", "account_id", "month", name="uq_year_account_month"),
        CheckConstraint("month >= 1 AND month <= 12", name="check_valid_month"),
        CheckConstraint("amount >= 0.00", name="check_non_negative_amount"),
    )

    budget_year = relationship("BudgetYear", back_populates="projections")
    account = relationship("Account", back_populates="projections")
