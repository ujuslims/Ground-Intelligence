"""
Thin REST wrapper exposing the GeoBrain controlled tools for direct testing
ahead of the full orchestration loop (Phase 6). Each endpoint calls exactly
one function from app.geobrain.tools.TOOL_REGISTRY -- this router is not an
alternate, less-governed path to any tool; run_engineering_calculation here
goes through the identical CalculationRunner gate as /api/calculations/{id}/run.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.engineering import Calculation
from app.geobrain import tools as gb_tools

router = APIRouter(prefix="/api/geobrain", tags=["geobrain"])


@router.get("/tools")
def list_tools(user: User = Depends(get_current_user)):
    return {"tools": sorted(gb_tools.TOOL_REGISTRY.keys())}


@router.get("/tools/get_project/{project_id}")
def tool_get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return gb_tools.get_project(db, project_id)


@router.get("/tools/get_methodology")
def tool_get_methodology(calculation_type: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return gb_tools.get_methodology(db, calculation_type)


@router.get("/tools/query_map/{project_id}")
def tool_query_map(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return gb_tools.query_map(db, project_id)


@router.get("/tools/get_report_template")
def tool_get_report_template(template_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return gb_tools.get_report_template(db, template_id)


@router.post("/tools/run_engineering_calculation/{calculation_id}")
def tool_run_engineering_calculation(calculation_id: str, inputs: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    calc = db.get(Calculation, calculation_id)
    if not calc:
        raise HTTPException(404, "Calculation not found")
    return gb_tools.run_engineering_calculation(db, calculation=calc, inputs=inputs, user_id=user.id)
