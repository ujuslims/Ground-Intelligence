"""
Investigation / InvestigationLocation — the common spatial entity shared across
disciplines (Architecture §6, §7 in the Readiness Assessment): rather than a
separate location model per discipline, Borehole / CPT / VES / Groundwater
point / Trial pit / Offshore borehole / Offshore CPT all reference one
InvestigationLocation row.

Investigation types fixed by MVP Data Model §20 — MVP-relevant subset here;
OFFSHORE_* values are retained in the enum for forward-compatibility (per
Data Model Controlled Revision: "do not add offshore-specific MVP entities
merely because offshore is future scope" — the enum values existing does not
mean offshore workflows are implemented).
"""
import enum
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import gen_uuid, utcnow, ProvenanceMixin


class InvestigationType(str, enum.Enum):
    GEOTECHNICAL = "GEOTECHNICAL"
    LABORATORY = "LABORATORY"
    GEOPHYSICAL = "GEOPHYSICAL"
    HYDROGEOLOGICAL = "HYDROGEOLOGICAL"
    SURVEY = "SURVEY"
    OFFSHORE_GEOTECHNICAL = "OFFSHORE_GEOTECHNICAL"
    OFFSHORE_GEOPHYSICAL = "OFFSHORE_GEOPHYSICAL"


class LocationType(str, enum.Enum):
    BOREHOLE = "BOREHOLE"
    CPT = "CPT"
    VES = "VES"
    GROUNDWATER_POINT = "GROUNDWATER_POINT"
    TRIAL_PIT = "TRIAL_PIT"
    OFFSHORE_BOREHOLE = "OFFSHORE_BOREHOLE"
    OFFSHORE_CPT = "OFFSHORE_CPT"


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    investigation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class InvestigationLocation(Base, ProvenanceMixin):
    __tablename__ = "investigation_locations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=False)
    location_code: Mapped[str] = mapped_column(String(64), nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    elevation: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Offshore-only attribute; NULL for onshore locations. Present for schema
    # forward-compatibility only — no offshore workflow is implemented in MVP.
    water_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
