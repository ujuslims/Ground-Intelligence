"""
Report Engine — assembles a DRAFT ENGINEERING SUMMARY from structured project
data (Tech Spec §41). This is the MVP reporting foundation, NOT a final
automated report generator (explicitly out of MVP scope).

Governance gate (Rev 2 §H, §C item 2): PIGL's actual report structure,
section wording, and branding are NOT invented here. Every section below is
built from real project data already in the database (or an explicit
"no data recorded" note) -- never placeholder engineering content dressed up
to look real. The output is always labelled:

    DRAFT — ENGINEER REVIEW REQUIRED

Full traceability chain preserved per Report Spec §9 / Tech Spec §42:
Report -> Section -> Table/Figure -> Engineering Result -> Calculation ->
Input -> Dataset -> Source File. Each section below records which project
records it was built from via `source_object_ids`, so that chain is walkable.
"""
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.investigation import Investigation, InvestigationLocation
from app.models.geotech import Borehole, CPT, GroundwaterObservation, LaboratoryResult
from app.models.geophysics import VES


def assemble_draft_engineering_summary(db: Session, *, project_id: str) -> dict:
    project = db.get(Project, project_id)
    if not project:
        return {"error": "not_found"}

    investigations = db.query(Investigation).filter_by(project_id=project_id).all()
    locations = db.query(InvestigationLocation).filter_by(project_id=project_id).all()
    location_ids = [l.id for l in locations]

    boreholes = db.query(Borehole).filter(Borehole.location_id.in_(location_ids)).all() if location_ids else []
    cpts = db.query(CPT).filter(CPT.location_id.in_(location_ids)).all() if location_ids else []
    groundwater = db.query(GroundwaterObservation).filter(GroundwaterObservation.location_id.in_(location_ids)).all() if location_ids else []
    ves_surveys = db.query(VES).filter(VES.location_id.in_(location_ids)).all() if location_ids else []

    sections = [
        {
            "section_type": "PROJECT_INFORMATION",
            "heading": "Project Information",
            "content": {"name": project.name, "project_code": project.project_code, "status": project.status},
            "source_object_ids": [project.id],
        },
        {
            "section_type": "INVESTIGATION_SUMMARY",
            "heading": "Investigation Summary",
            "content": {"investigation_count": len(investigations),
                        "investigations": [{"id": i.id, "name": i.name, "type": i.investigation_type} for i in investigations]},
            "source_object_ids": [i.id for i in investigations],
        },
        {
            "section_type": "INVESTIGATION_MAP",
            "heading": "Investigation Location Map",
            "content": {"location_count": len(locations),
                        "locations": [{"id": l.id, "type": l.location_type, "lat": l.latitude, "lon": l.longitude} for l in locations]},
            "source_object_ids": location_ids,
        },
        {
            "section_type": "BOREHOLE_SUMMARY",
            "heading": "Borehole Summary",
            "content": {"borehole_count": len(boreholes)} if boreholes else {"note": "No borehole records for this project."},
            "source_object_ids": [b.id for b in boreholes],
        },
        {
            "section_type": "CPT_SUMMARY",
            "heading": "CPT Summary",
            "content": {"cpt_count": len(cpts)} if cpts else {"note": "No CPT records for this project."},
            "source_object_ids": [c.id for c in cpts],
        },
        {
            "section_type": "GROUNDWATER_SUMMARY",
            "heading": "Groundwater Summary",
            "content": {"observation_count": len(groundwater)} if groundwater else {"note": "No groundwater observations for this project."},
            "source_object_ids": [g.id for g in groundwater],
        },
        {
            "section_type": "VES_SUMMARY",
            "heading": "Geophysical (VES) Summary",
            "content": {"ves_count": len(ves_surveys)} if ves_surveys else {"note": "No VES surveys for this project."},
            "source_object_ids": [v.id for v in ves_surveys],
        },
        {
            "section_type": "ENGINEERING_CALCULATION_SUMMARY",
            "heading": "Engineering Calculation Summary",
            "content": {"note": "No approved engineering methodology is available yet; no engineering "
                                 "calculation results can be included in this draft. See the Methodology "
                                 "Registry and Request/Add Methodology workflow."},
            "source_object_ids": [],
        },
    ]

    return {
        "project_id": project_id,
        "report_type": "DRAFT_ENGINEERING_SUMMARY",
        "label": "DRAFT — ENGINEER REVIEW REQUIRED",
        "sections": sections,
    }
