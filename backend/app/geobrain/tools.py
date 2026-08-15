"""
GeoBrain controlled tool contract.

Authoritative 15-tool list per GeoBrain Specification §8, confirmed complete
by Controlled Clarification CC-GB-01, reconfirmed unchanged by Implementation
Design Rev 2 §G:

  get_project, get_investigation, get_location, get_borehole, get_cpt,
  get_lab_results, get_groundwater, get_ves, search_documents, query_map,
  get_methodology, run_engineering_calculation [CONDITIONAL/GOVERNED],
  get_calculation, generate_report, get_report_template [CONFIGURATION-DEPENDENT]

GeoBrain retrieves through these functions ONLY -- never direct/unrestricted
database manipulation (Architecture §18). GeoBrain never performs engineering
arithmetic itself: run_engineering_calculation forwards to the same
CalculationRunner gate used by the REST API and the (future) frontend
calculation screen, so GeoBrain is subject to exactly the same refusal
behaviour a human user gets (CC-GB-01 §5).

This module implements the tool FUNCTIONS with real DB-backed retrieval.
It does not implement an LLM orchestration/agentic loop around them -- that
is Phase 6 GeoBrain AI-integration work building on top of this contract,
using the configured Anthropic Claude Sonnet-class model behind the
provider-agnostic abstraction in app/geobrain/llm_provider.py. Wiring the
orchestration loop is intentionally left for the next iteration once PIGL
supplies the existing custom-GPT system-instruction material (Rev 2 §C
item 3) -- building it now with placeholder instructions risks the "do not
recreate the existing custom GPT from memory" gate (Build Prompt Controlled
Revision §6).
"""
import json

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.investigation import Investigation, InvestigationLocation
from app.models.geotech import Borehole, BoreholeStratum, SPT, CPT, CPTReading, LaboratoryResult, Sample, GroundwaterObservation
from app.models.geophysics import VES, VESLayer
from app.models.engineering import Methodology, MethodologyVersion, MethodologyRequest, MethodologyStatus, Calculation
from app.models.reporting import ReportTemplate
from app.services.calculation_engine import calculation_runner, INSUFFICIENT_BASIS_MESSAGE


def get_project(db: Session, project_id: str) -> dict:
    p = db.get(Project, project_id)
    if not p:
        return {"error": "not_found"}
    return {"id": p.id, "name": p.name, "status": p.status, "project_code": p.project_code}


def get_investigation(db: Session, investigation_id: str) -> dict:
    inv = db.get(Investigation, investigation_id)
    if not inv:
        return {"error": "not_found"}
    return {"id": inv.id, "name": inv.name, "investigation_type": inv.investigation_type, "status": inv.status}


def get_location(db: Session, location_id: str) -> dict:
    loc = db.get(InvestigationLocation, location_id)
    if not loc:
        return {"error": "not_found"}
    return {
        "id": loc.id, "location_code": loc.location_code, "location_type": loc.location_type,
        "latitude": loc.latitude, "longitude": loc.longitude, "elevation": loc.elevation,
        "source": loc.source, "status": loc.status, "version": loc.version,
    }


def get_borehole(db: Session, borehole_id: str) -> dict:
    bh = db.get(Borehole, borehole_id)
    if not bh:
        return {"error": "not_found"}
    strata = db.query(BoreholeStratum).filter_by(borehole_id=borehole_id).order_by(BoreholeStratum.depth_from).all()
    spt = db.query(SPT).filter_by(borehole_id=borehole_id).order_by(SPT.depth).all()
    return {
        "id": bh.id, "borehole_id_label": bh.borehole_id_label, "final_depth": bh.final_depth,
        "status": bh.status, "source": bh.source,
        "strata": [{"depth_from": s.depth_from, "depth_to": s.depth_to,
                     "observed_description": s.observed_description, "interpreted_unit": s.interpreted_unit} for s in strata],
        "spt": [{"depth": s.depth, "n_value": s.n_value} for s in spt],
    }


def get_cpt(db: Session, cpt_id: str) -> dict:
    cpt = db.get(CPT, cpt_id)
    if not cpt:
        return {"error": "not_found"}
    readings = db.query(CPTReading).filter_by(cpt_id=cpt_id).order_by(CPTReading.depth).all()
    return {
        "id": cpt.id, "cpt_id_label": cpt.cpt_id_label, "status": cpt.status, "source": cpt.source,
        "reading_count": len(readings),
        "readings": [{"depth": r.depth, "qc": r.qc, "fs": r.fs, "u2": r.u2} for r in readings],
    }


def get_lab_results(db: Session, sample_id: str) -> dict:
    sample = db.get(Sample, sample_id)
    if not sample:
        return {"error": "not_found"}
    results = db.query(LaboratoryResult).filter_by(sample_id=sample_id).all()
    return {
        "sample_id": sample_id, "sample_id_label": sample.sample_id_label,
        "results": [{"result_type": r.result_type, "value": r.value, "unit": r.unit,
                      "status": r.status, "source": r.source} for r in results],
    }


def get_groundwater(db: Session, location_id: str) -> dict:
    obs = db.query(GroundwaterObservation).filter_by(location_id=location_id).order_by(GroundwaterObservation.observation_date).all()
    return {"location_id": location_id, "observations": [
        {"date": str(o.observation_date), "depth_to_water": o.depth_to_water, "source": o.source} for o in obs
    ]}


def get_ves(db: Session, ves_id: str) -> dict:
    ves = db.get(VES, ves_id)
    if not ves:
        return {"error": "not_found"}
    layers = db.query(VESLayer).filter_by(ves_id=ves_id).order_by(VESLayer.layer_number).all()
    return {
        "id": ves.id, "ves_id_label": ves.ves_id_label, "interpretation_status": ves.interpretation_status,
        "layers": [{"layer_number": l.layer_number, "resistivity": l.resistivity, "thickness": l.thickness,
                     "interpretation": l.interpretation} for l in layers],
    }


def search_documents(db: Session, project_id: str, query: str) -> dict:
    """
    MVP document search is limited to supported file types/extraction
    capabilities (Tech Spec §49). Full-text indexing is not part of this
    scaffold; this stub returns an explicit "not yet available" condition
    rather than fabricating search results.
    """
    return {"query": query, "results": [], "note": "Document search indexing is not yet implemented in this build."}


def query_map(db: Session, project_id: str) -> dict:
    locations = db.query(InvestigationLocation).filter_by(project_id=project_id).all()
    return {"project_id": project_id, "locations": [
        {"id": l.id, "location_code": l.location_code, "location_type": l.location_type,
         "latitude": l.latitude, "longitude": l.longitude} for l in locations
    ]}


def get_methodology(db: Session, calculation_type: str) -> dict:
    """
    Surfaces APPROVED methodologies for a calculation type, AND, per Rev 2 §G,
    surfaces MethodologyRequest status where relevant -- so GeoBrain can say
    "that methodology has been requested and is under review" instead of only
    "not available." This is retrieval of existing governance state, not a
    new decision-making capability.
    """
    methodologies = db.query(Methodology).filter_by(engineering_domain=calculation_type).all()
    approved = []
    for m in methodologies:
        versions = db.query(MethodologyVersion).filter_by(methodology_id=m.id, status=MethodologyStatus.APPROVED.value).all()
        if versions:
            approved.append({"methodology_id": m.id, "name": m.name, "versions": [v.version for v in versions]})

    requests = db.query(MethodologyRequest).filter(
        MethodologyRequest.requested_name.ilike(f"%{calculation_type}%")
    ).all()

    if not approved:
        return {
            "calculation_type": calculation_type,
            "approved_methodologies": [],
            "available": False,
            "message": INSUFFICIENT_BASIS_MESSAGE,
            "related_requests": [{"id": r.id, "requested_name": r.requested_name, "status": r.status} for r in requests],
        }
    return {"calculation_type": calculation_type, "approved_methodologies": approved, "available": True}


def run_engineering_calculation(db: Session, *, calculation: Calculation, inputs: dict, user_id: str) -> dict:
    """
    CONDITIONAL / GOVERNED (CC-GB-01 §5). GeoBrain never performs arithmetic
    itself -- this forwards to the exact same CalculationRunner the REST API
    uses (app/services/calculation_engine.py). GeoBrain must not autonomously
    select a methodology on the engineer's behalf; `calculation` must already
    carry the engineer's methodology_id/methodology_version_id selection
    (Rev 2 §F.3) before this tool is called.
    """
    cv = calculation_runner.run(db, calculation=calculation, inputs=inputs, user_id=user_id)
    return {
        "outcome": cv.outcome,
        "result": json.loads(cv.result) if cv.result else None,
        "warnings": json.loads(cv.warnings) if cv.warnings else [],
    }


def get_calculation(db: Session, calculation_id: str) -> dict:
    calc = db.get(Calculation, calculation_id)
    if not calc:
        return {"error": "not_found"}
    return {"id": calc.id, "calculation_type": calc.calculation_type, "status": calc.status,
             "methodology_id": calc.methodology_id, "methodology_version_id": calc.methodology_version_id}


def generate_report(db: Session, project_id: str) -> dict:
    """Delegates to the Report Engine (app/services/report_engine.py) --
    always produces a DRAFT clearly labelled ENGINEER REVIEW REQUIRED."""
    from app.services.report_engine import assemble_draft_engineering_summary
    return assemble_draft_engineering_summary(db, project_id=project_id)


def get_report_template(db: Session, template_id: str | None = None) -> dict:
    """
    CONFIGURATION-DEPENDENT (CC-GB-01 §6). Retrieves configured template
    metadata only -- never fabricates PIGL content or branding where none has
    been supplied.
    """
    if template_id:
        t = db.get(ReportTemplate, template_id)
        if not t:
            return {"error": "not_found"}
        templates = [t]
    else:
        templates = db.query(ReportTemplate).all()

    if not templates:
        return {
            "available": False,
            "message": "No PIGL report template has been supplied yet. Using placeholder/configuration architecture only.",
        }
    return {"available": True, "templates": [{"id": t.id, "name": t.name, "version": t.version, "status": t.status} for t in templates]}


TOOL_REGISTRY = {
    "get_project": get_project,
    "get_investigation": get_investigation,
    "get_location": get_location,
    "get_borehole": get_borehole,
    "get_cpt": get_cpt,
    "get_lab_results": get_lab_results,
    "get_groundwater": get_groundwater,
    "get_ves": get_ves,
    "search_documents": search_documents,
    "query_map": query_map,
    "get_methodology": get_methodology,
    "run_engineering_calculation": run_engineering_calculation,
    "get_calculation": get_calculation,
    "generate_report": generate_report,
    "get_report_template": get_report_template,
}
