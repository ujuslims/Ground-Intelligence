"""
Engineering calculation framework — Methodology / MethodologyVersion /
MethodologyRequest / Calculation / CalculationVersion.

*** GOVERNANCE GATE — READ BEFORE MODIFYING THIS FILE ***
No engineering methodology, formula, factor, or soil model is selected or
implied anywhere in this module. It defines the CONTAINER for a methodology,
not any methodology's content. Only a MethodologyVersion with
status == APPROVED may ever be used to activate a production calculation —
this is enforced in app/services/calculation_engine.py, not here, but the
status vocabulary that makes that enforcement possible is defined here.

See: Ground Intelligence Controlled Specification Register §10-11,
MVP Implementation Design Rev 2 §F, §J, §K.
"""
import enum
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import gen_uuid, utcnow


class MethodologyStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"       # the ONLY status usable for a production calculation
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"


class CalculationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class Methodology(Base):
    __tablename__ = "methodologies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    engineering_domain: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. SHALLOW_FOUNDATION_BEARING_CAPACITY
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    applicability: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=MethodologyStatus.DRAFT.value)


class MethodologyVersion(Base):
    __tablename__ = "methodology_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    methodology_id: Mapped[str] = mapped_column(String(36), ForeignKey("methodologies.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    specification: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_cases: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=MethodologyStatus.DRAFT.value)
    # Engineer-facing controlled alternatives (design approach, load combination,
    # drainage condition, etc.) — JSON array. Populated only by the approved
    # methodology content itself; never invented by the UI or GeoBrain
    # (Implementation Design Rev 2 §F.3).
    configuration_options: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_inputs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON


class MethodologyRequest(Base):
    """Request/Add Methodology governed intake pathway (Rev 2 §F.2). A request
    is DATA, never an authorization to use the requested methodology."""
    __tablename__ = "methodology_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    requested_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_document_file_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("files.id"), nullable=True)
    applicability: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_configuration: Mapped[str | None] = mapped_column(Text, nullable=True)
    supporting_file_ids: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of file ids
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=MethodologyStatus.REQUESTED.value)
    linked_methodology_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("methodologies.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Calculation(Base):
    __tablename__ = "calculations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    calculation_type: Mapped[str] = mapped_column(String(128), nullable=False)
    methodology_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("methodologies.id"), nullable=True)
    methodology_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("methodology_versions.id"), nullable=True)
    selected_configuration: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=CalculationStatus.DRAFT.value)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CalculationVersion(Base):
    __tablename__ = "calculation_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    calculation_id: Mapped[str] = mapped_column(String(36), ForeignKey("calculations.id"), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    inputs: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON — classified MEASURED/IMPORTED/DERIVED/USER-DEFINED/ASSUMED
    result: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON — null when the calculation was refused
    warnings: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)   # "REFUSED_NO_APPROVED_METHODOLOGY" | "COMPLETED" | "FRAMEWORK_TEST_MOCK"
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
