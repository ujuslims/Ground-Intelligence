from datetime import date

from sqlalchemy import String, ForeignKey, Float, Date, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import gen_uuid, ProvenanceMixin


class VES(Base, ProvenanceMixin):
    __tablename__ = "ves_surveys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    location_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigation_locations.id"), nullable=False)
    ves_id_label: Mapped[str] = mapped_column(String(64), nullable=False)
    array_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    survey_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    interpretation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="RAW")
    dataset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("datasets.id"), nullable=True)


class VESReading(Base):
    __tablename__ = "ves_readings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    ves_id: Mapped[str] = mapped_column(String(36), ForeignKey("ves_surveys.id"), nullable=False)
    electrode_spacing: Mapped[float] = mapped_column(Float, nullable=False)
    apparent_resistivity: Mapped[float] = mapped_column(Float, nullable=False)


class VESLayer(Base, ProvenanceMixin):
    """Interpreted layers — distinct from raw VESReading rows; interpretation
    status is tracked separately (Tech Spec §24)."""
    __tablename__ = "ves_layers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    ves_id: Mapped[str] = mapped_column(String(36), ForeignKey("ves_surveys.id"), nullable=False)
    layer_number: Mapped[int] = mapped_column(nullable=False)
    resistivity: Mapped[float] = mapped_column(Float, nullable=False)
    thickness: Mapped[float | None] = mapped_column(Float, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
