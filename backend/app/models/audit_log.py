from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base

class BudgetAuditLog(Base):
    __tablename__ = "budget_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    year = Column(Integer, ForeignKey("budget_years.year", ondelete="RESTRICT"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    month = Column(Integer, nullable=False)
    previous_amount = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    new_amount = Column(Numeric(15, 2), nullable=False)
    modified_by = Column(String(100), nullable=False, default="Usuario")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("month >= 1 AND month <= 12", name="check_audit_valid_month"),
        CheckConstraint("new_amount >= 0.00", name="check_audit_non_negative_amount"),
    )

    budget_year = relationship("BudgetYear", back_populates="audit_logs")
    account = relationship("Account", back_populates="audit_logs")
