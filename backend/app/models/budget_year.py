from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base

class BudgetYear(Base):
    __tablename__ = "budget_years"

    year = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), nullable=False, default="DRAFT")  # DRAFT, APPROVED, CLOSED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    projections = relationship("BudgetMonthlyProjection", back_populates="budget_year", cascade="all, delete-orphan")
    audit_logs = relationship("BudgetAuditLog", back_populates="budget_year", cascade="all, delete-orphan")
