from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    code = Column(String(50), default="", nullable=False)
    name = Column(String(255), nullable=False)
    responsible = Column(String(100), default="", nullable=False)
    provider = Column(String(150), default="", nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    category = relationship("Category", back_populates="accounts")
    projections = relationship("BudgetMonthlyProjection", back_populates="account", cascade="all, delete-orphan")
    audit_logs = relationship("BudgetAuditLog", back_populates="account")
