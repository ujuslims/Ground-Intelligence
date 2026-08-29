"""
Project-level authorization helpers.

Every piece of investigation/engineering data in Ground Intelligence
ultimately belongs to exactly one Project, and a Project belongs to exactly
one Organization (app/models/project.py). ProjectMembership is what actually
grants a user access to a project's data (Tech Spec §8) -- NOT organization_id
membership alone, and NOT simply "the user is logged in."

Before this module existed, most routers trusted whatever id was in the URL
path (location_id, borehole_id, cpt_id, ...) without checking that the
requesting user has a ProjectMembership on the project that id belongs to.
In a single-firm deployment that was a real but contained risk (any PIGL
user could read any other PIGL project). Once Ground Intelligence serves
more than one organization, the same gap becomes a cross-tenant data leak --
one firm's confidential ground investigation data readable by another firm's
staff -- which is why this is being closed now, ahead of onboarding a second
organization.

Usage: call `require_project_access(db, user, project_id)` with a project_id
you already have, or one of the `resolve_*_project_id` helpers first when the
route only has a child id (e.g. a borehole_id) and needs to walk up to the
owning project before it can check membership.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.models.identity import User, ProjectMembership
from app.models.project import Project


def require_project_access(db: DBSession, user: User, project_id: str | None) -> Project:
    """Raise 404 if the project doesn't exist, 403 if the user has no
    ProjectMembership on it. Returns the Project row on success."""
    if not project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    membership = (
        db.query(ProjectMembership)
        .filter_by(project_id=project_id, user_id=user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No membership on this project")
    return project


def resolve_location_project_id(db: DBSession, location_id: str) -> str | None:
    from app.models.investigation import InvestigationLocation
    loc = db.get(InvestigationLocation, location_id)
    return loc.project_id if loc else None


def resolve_borehole_project_id(db: DBSession, borehole_id: str) -> str | None:
    from app.models.geotech import Borehole
    bh = db.get(Borehole, borehole_id)
    if not bh:
        return None
    return resolve_location_project_id(db, bh.location_id)


def resolve_cpt_project_id(db: DBSession, cpt_id: str) -> str | None:
    from app.models.geotech import CPT
    cpt = db.get(CPT, cpt_id)
    if not cpt:
        return None
    return resolve_location_project_id(db, cpt.location_id)


def resolve_ves_project_id(db: DBSession, ves_id: str) -> str | None:
    from app.models.geophysics import VES
    ves = db.get(VES, ves_id)
    if not ves:
        return None
    return resolve_location_project_id(db, ves.location_id)


def resolve_calculation_project_id(db: DBSession, calculation_id: str) -> str | None:
    from app.models.engineering import Calculation
    calc = db.get(Calculation, calculation_id)
    return calc.project_id if calc else None
