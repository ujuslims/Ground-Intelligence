"""
Borehole / CPT / Groundwater / Laboratory entities.

CPT elevation is inherited from InvestigationLocation, not stored again on CPT
(Implementation Design Rev 2, Amendment 9 — confirms Rev 1 §1.3 unchanged).
cone_type remains directly on CPT (Data Model Controlled Revision §1).

SPT is observational-only for MVP (Rev 2 Amendment 1): borehole_id, depth,
n_value, source, version — NO correction fields (energy ratio, overburden
correction, rod correction). Do not add these without separate PIGL
Engineering approval.

Stratigraphy preserves the distinction between the observed material
description and the interpreted geological/engineering unit (Tech Spec §15) —
two separate columns, never merged.
"""
from datetime import datetime, date

from sqlalchemy import String, ForeignKey, DateTime, Float, Date, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import gen_uuid, utcnow, ProvenanceMixin


class Borehole(Base, ProvenanceMixin):
    __tablename__ = "boreholes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    location_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigation_locations.id"), nullable=False)
    borehole_id_label: Mapped[str] = mapped_column(String(64), nullable=False)
    drilling_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    drilling_method: Mapped[str | None] = mapped_column(String(128), nullable=True)
    final_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)


class BoreholeStratum(Base, ProvenanceMixin):
    __tablename__ = "borehole_strata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    borehole_id: Mapped[str] = mapped_column(String(36), ForeignKey("boreholes.id"), nullable=False)
    depth_from: Mapped[float] = mapped_column(Float, nullable=False)
    depth_to: Mapped[float] = mapped_column(Float, nullable=False)
    observed_description: Mapped[str] = mapped_column(Text, nullable=False)
    interpreted_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SPT(Base, ProvenanceMixin):
    """Observational only — see module docstring. No correction fields."""
    __tablename__ = "spt_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    borehole_id: Mapped[str] = mapped_column(String(36), ForeignKey("boreholes.id"), nullable=False)
    depth: Mapped[float] = mapped_column(Float, nullable=False)
    n_value: Mapped[int] = mapped_column(nullable=False)


class CPT(Base, ProvenanceMixin):
    __tablename__ = "cpts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    location_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigation_locations.id"), nullable=False)
    cpt_id_label: Mapped[str] = mapped_column(String(64), nullable=False)
    cone_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    test_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    dataset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=True)


class CPTReading(Base):
    __tablename__ = "cpt_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    cpt_id: Mapped[str] = mapped_column(String(36), ForeignKey("cpts.id"), nullable=False)
    depth: Mapped[float] = mapped_column(Float, nullable=False)
    qc: Mapped[float | None] = mapped_column(Float, nullable=True)
    fs: Mapped[float | None] = mapped_column(Float, nullable=True)
    u2: Mapped[float | None] = mapped_column(Float, nullable=True)


class Sample(Base, ProvenanceMixin):
    __tablename__ = "samples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    borehole_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("boreholes.id"), nullable=True)
    sample_id_label: Mapped[str] = mapped_column(String(64), nullable=False)
    depth_from: Mapped[float | None] = mapped_column(Float, nullable=True)
    depth_to: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_type: Mapped[str | None] = mapped_column(String(64), nullable=True)


class LaboratoryResult(Base, ProvenanceMixin):
    """
    MVP result types (Tech Spec §21): moisture content, liquid limit, plastic
    limit, plasticity index, particle-size distribution, CBR.

    Import pathway is Path B (externally processed laboratory summary import)
    per PRD §8-9 — results imported this way must be labelled IMPORTED, never
    implied as calculated by Ground Intelligence (Tech Spec §22).
    """
    __tablename__ = "laboratory_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    sample_id: Mapped[str] = mapped_column(String(36), ForeignKey("samples.id"), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=True)
    result_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. MOISTURE_CONTENT, LIQUID_LIMIT...
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    result_payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON for multi-value results (e.g. PSD curve)


class GroundwaterObservation(Base, ProvenanceMixin):
    """Groundwater levels must never be inferred if not supplied (Tech Spec §23)."""
    __tablename__ = "groundwater_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    location_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigation_locations.id"), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    depth_to_water: Mapped[float] = mapped_column(Float, nullable=False)
    elevation: Mapped[float | None] = mapped_column(Float, nullable=True)
    measurement_method: Mapped[str | None] = mapped_column(String(128), nullable=True)
