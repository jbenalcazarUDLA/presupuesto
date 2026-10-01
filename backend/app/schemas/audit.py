from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class AuditLogItem(BaseModel):
    id: int
    year: int
    account_id: int
    account_code: str
    account_name: str
    category_name: str
    month: int
    previous_amount: str
    new_amount: str
    modified_by: str
    reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    total: int
    items: List[AuditLogItem]
