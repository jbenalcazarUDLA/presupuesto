from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.budget_year import BudgetYear
from app.schemas.budget import BudgetMatrixResponse, BudgetUpdateRequest
from app.services.budget_calculator import BudgetCalculatorService

router = APIRouter()

@router.get("/budgets/{year}/matrix", response_model=BudgetMatrixResponse, summary="Obtener la matriz jerárquica con los 12 meses y todos los totales calculados")
def get_matrix(year: int, db: Session = Depends(get_db)):
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Año fiscal inválido")
    matrix = BudgetCalculatorService.get_budget_matrix(db, year)
    return matrix

@router.put("/budgets/{year}/projections", response_model=BudgetMatrixResponse, summary="Guardar o actualizar proyecciones mensuales con registro de auditoría")
def update_projections(year: int, payload: BudgetUpdateRequest, db: Session = Depends(get_db)):
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Año fiscal inválido")
    
    try:
        updated_matrix = BudgetCalculatorService.update_projections(db, year, payload)
        return updated_matrix
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar proyecciones: {str(e)}")

@router.put("/budgets/{year}/status", summary="Cambiar estado del año presupuestario (DRAFT, APPROVED, CLOSED)")
def update_status(year: int, new_status: str, db: Session = Depends(get_db)):
    valid_statuses = ["DRAFT", "APPROVED", "CLOSED"]
    new_status = new_status.upper().strip()
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Opciones: {valid_statuses}")
    
    by = db.query(BudgetYear).filter(BudgetYear.year == year).first()
    if not by:
        raise HTTPException(status_code=404, detail=f"Año fiscal {year} no encontrado")
    
    by.status = new_status
    db.commit()
    db.refresh(by)
    return {"year": by.year, "status": by.status, "message": f"Estado actualizado a {by.status}"}
