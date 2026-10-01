from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.models.audit_log import BudgetAuditLog
from app.models.account import Account
from app.models.category import Category
from app.core.decimal_math import format_decimal

class AuditService:

    @staticmethod
    def get_audit_trail(
        db: Session,
        year: int,
        account_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        query = db.query(BudgetAuditLog).filter(BudgetAuditLog.year == year)

        if account_id:
            query = query.filter(BudgetAuditLog.account_id == account_id)

        total = query.count()
        logs = query.order_by(BudgetAuditLog.created_at.desc(), BudgetAuditLog.id.desc()).offset(offset).limit(limit).all()

        items = []
        for log in logs:
            acc = db.query(Account).filter(Account.id == log.account_id).first()
            acc_code = acc.code if acc else ""
            acc_name = acc.name if acc else f"Cuenta #{log.account_id}"
            cat_name = acc.category.name if (acc and acc.category) else ""

            items.append({
                "id": log.id,
                "year": log.year,
                "account_id": log.account_id,
                "account_code": acc_code,
                "account_name": acc_name,
                "category_name": cat_name,
                "month": log.month,
                "previous_amount": format_decimal(log.previous_amount),
                "new_amount": format_decimal(log.new_amount),
                "modified_by": log.modified_by,
                "reason": log.reason or "",
                "created_at": log.created_at
            })

        return {
            "total": total,
            "items": items
        }
