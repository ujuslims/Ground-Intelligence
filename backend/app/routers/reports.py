from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.reporting import Report, ReportSection
from app.services.audit import log_event
from app.services.report_engine import assemble_draft_engineering_summary

router = APIRouter(prefix="/api", tags=["reports"])


@router.post("/projects/{project_id}/reports/draft-summary")
def create_draft_summary(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Assembles and persists a DRAFT — ENGINEER REVIEW REQUIRED report from
    structured project data (Tech Spec §41)."""
    summary = assemble_draft_engineering_summary(db, project_id=project_id)
    if "error" in summary:
        return summary

    report = Report(project_id=project_id, title=f"Draft Engineering Summary — {project_id}",
                     report_type="DRAFT_ENGINEERING_SUMMARY", status="DRAFT", created_by=user.id)
    db.add(report)
    db.flush()

    for i, section in enumerate(summary["sections"]):
        db.add(ReportSection(
            report_id=report.id, section_type=section["section_type"], heading=section["heading"],
            order=i, content_ref=str(section["source_object_ids"]), status="DRAFT",
        ))
    db.commit()
    db.refresh(report)

    log_event(db, user_id=user.id, action="REPORT_GENERATED", object_type="REPORT", object_id=report.id)
    return {"report_id": report.id, "label": summary["label"], "sections": summary["sections"]}


@router.get("/reports/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report:
        return {"error": "not_found"}
    sections = db.query(ReportSection).filter_by(report_id=report_id).order_by(ReportSection.order).all()
    return {
        "id": report.id, "title": report.title, "status": report.status, "report_type": report.report_type,
        "sections": [{"heading": s.heading, "section_type": s.section_type, "status": s.status} for s in sections],
    }
