from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.engineering import Calculation
from app.schemas.engineering import CalculationCreate, CalculationOut, CalculationRunRequest
from app.services.audit import log_event
from app.services.calculation_engine import calculation_runner

router = APIRouter(prefix="/api", tags=["engineering"])


@router.post("/calculations", response_model=CalculationOut)
def create_calculation(payload: CalculationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    calc = Calculation(**payload.model_dump(), created_by=user.id)
    db.add(calc)
    db.commit()
    db.refresh(calc)
    log_event(db, user_id=user.id, action="CALCULATION_CREATED", object_type="CALCULATION", object_id=calc.id)
    return calc


@router.post("/calculations/{calculation_id}/run")
def run_calculation(calculation_id: str, payload: CalculationRunRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Calls the ONE gated Calculation Runner (see app/services/calculation_engine.py).
    For every real calculation_type today this returns outcome =
    REFUSED_NO_APPROVED_METHODOLOGY with the explicit insufficient-basis
    message -- never a plausible-looking fabricated result.
    """
    calc = db.get(Calculation, calculation_id)
    if not calc:
        raise HTTPException(404, "Calculation not found")

    cv = calculation_runner.run(db, calculation=calc, inputs=payload.inputs, user_id=user.id)
    import json
    return {
        "calculation_version_id": cv.id,
        "outcome": cv.outcome,
        "result": json.loads(cv.result) if cv.result else None,
        "warnings": json.loads(cv.warnings) if cv.warnings else [],
    }


@router.get("/calculations/{calculation_id}")
def get_calculation(calculation_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    calc = db.get(Calculation, calculation_id)
    if not calc:
        raise HTTPException(404, "Calculation not found")
    return calc
