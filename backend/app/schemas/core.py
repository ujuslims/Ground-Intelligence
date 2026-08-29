"""Pydantic schemas for the Phase 1/2 entities. Kept intentionally close to
the SQLAlchemy models -- this is a data-management platform, not a place for
clever DTO layering that could drift from the controlled data model."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Project ----
class ProjectCreate(BaseModel):
    # Optional: almost every user belongs to exactly one organization, so the
    # backend defaults this to the creating user's own organization_id when
    # omitted (see routers/projects.py). Only needed if a user somehow spans
    # more than one organization -- not a normal MVP case.
    organization_id: str | None = None
    client_id: str | None = None
    name: str
    project_code: str | None = None
    description: str | None = None


class ProjectOut(ORMModel):
    id: str
    organization_id: str
    client_id: str | None
    name: str
    project_code: str | None
    description: str | None
    status: str
    created_by: str
    created_at: datetime


# ---- Investigation ----
class InvestigationCreate(BaseModel):
    project_id: str
    name: str
    investigation_type: str
    description: str | None = None


class InvestigationOut(ORMModel):
    id: str
    project_id: str
    name: str
    investigation_type: str
    description: str | None
    status: str
    created_at: datetime


# ---- InvestigationLocation ----
class LocationCreate(BaseModel):
    project_id: str
    investigation_id: str
    location_code: str
    location_type: str
    latitude: float
    longitude: float
    elevation: float | None = None
    water_depth: float | None = None
    source: str
    status: str = "RAW"


class LocationOut(ORMModel):
    id: str
    project_id: str
    investigation_id: str
    location_code: str
    location_type: str
    latitude: float
    longitude: float
    elevation: float | None
    water_depth: float | None
    source: str
    version: int
    status: str
    created_at: datetime


# ---- Borehole ----
class BoreholeCreate(BaseModel):
    location_id: str
    borehole_id_label: str
    drilling_date: date | None = None
    drilling_method: str | None = None
    final_depth: float | None = None
    remarks: str | None = None
    source: str
    status: str = "RAW"


class BoreholeOut(ORMModel):
    id: str
    location_id: str
    borehole_id_label: str
    drilling_date: date | None
    drilling_method: str | None
    final_depth: float | None
    remarks: str | None
    source: str
    version: int
    status: str


class StratumCreate(BaseModel):
    borehole_id: str
    depth_from: float
    depth_to: float
    observed_description: str
    interpreted_unit: str | None = None
    source: str
    status: str = "RAW"


class StratumOut(ORMModel):
    id: str
    borehole_id: str
    depth_from: float
    depth_to: float
    observed_description: str
    interpreted_unit: str | None
    status: str


class SPTCreate(BaseModel):
    borehole_id: str
    depth: float
    n_value: int
    source: str
    status: str = "RAW"


class SPTOut(ORMModel):
    id: str
    borehole_id: str
    depth: float
    n_value: int
    status: str


# ---- CPT ----
class CPTCreate(BaseModel):
    location_id: str
    cpt_id_label: str
    cone_type: str | None = None
    test_date: date | None = None
    source: str
    status: str = "RAW"


class CPTOut(ORMModel):
    id: str
    location_id: str
    cpt_id_label: str
    cone_type: str | None
    test_date: date | None
    dataset_id: str | None
    source: str
    version: int
    status: str


class CPTReadingIn(BaseModel):
    depth: float
    qc: float | None = None
    fs: float | None = None
    u2: float | None = None


class CPTReadingOut(ORMModel):
    id: str
    cpt_id: str
    depth: float
    qc: float | None
    fs: float | None
    u2: float | None


class CPTImportRequest(BaseModel):
    readings: list[CPTReadingIn]


# ---- Groundwater ----
class GroundwaterCreate(BaseModel):
    location_id: str
    observation_date: date
    depth_to_water: float
    elevation: float | None = None
    measurement_method: str | None = None
    source: str
    status: str = "RAW"


class GroundwaterOut(ORMModel):
    id: str
    location_id: str
    observation_date: date
    depth_to_water: float
    elevation: float | None
    measurement_method: str | None
    status: str


# ---- Laboratory ----
class SampleCreate(BaseModel):
    borehole_id: str | None = None
    sample_id_label: str
    depth_from: float | None = None
    depth_to: float | None = None
    sample_type: str | None = None
    source: str
    status: str = "RAW"


class SampleOut(ORMModel):
    id: str
    borehole_id: str | None
    sample_id_label: str
    depth_from: float | None
    depth_to: float | None
    sample_type: str | None
    status: str


class LabResultCreate(BaseModel):
    sample_id: str
    result_type: str
    value: float | None = None
    unit: str | None = None
    result_payload: str | None = None
    source: str
    status: str = "IMPORTED"


class LabResultOut(ORMModel):
    id: str
    sample_id: str
    result_type: str
    value: float | None
    unit: str | None
    status: str
    source: str


# ---- VES ----
class VESCreate(BaseModel):
    location_id: str
    ves_id_label: str
    array_type: str | None = None
    survey_date: date | None = None
    source: str
    status: str = "RAW"


class VESOut(ORMModel):
    id: str
    location_id: str
    ves_id_label: str
    array_type: str | None
    survey_date: date | None
    interpretation_status: str
    status: str


class VESReadingIn(BaseModel):
    electrode_spacing: float
    apparent_resistivity: float


class VESLayerCreate(BaseModel):
    ves_id: str
    layer_number: int
    resistivity: float
    thickness: float | None = None
    interpretation: str | None = None
    source: str
    status: str = "INTERPRETED"


class VESLayerOut(ORMModel):
    id: str
    ves_id: str
    layer_number: int
    resistivity: float
    thickness: float | None
    interpretation: str | None
    status: str
