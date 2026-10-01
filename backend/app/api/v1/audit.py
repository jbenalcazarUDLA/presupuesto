from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter()

@router.get("/budgets/{year}/audit", response_model=AuditLogResponse, summary="Consultar historial de cambios y auditoría para el año fiscal")
def get_audit_trail(
    year: int,
    account_id: Optional[int] = Query(None, description="Filtrar por ID de cuenta específica"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return AuditService.get_audit_trail(
        db=db,
        year=year,
        account_id=account_id,
        limit=limit,
        offset=offset
    )
