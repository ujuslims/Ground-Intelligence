"""
Report / ReportTemplate / ReportSection / Review.

Review is the SOLE approval-representing entity (Implementation Design Rev 2,
Amendment 3) — no separate Approval entity exists in this MVP schema, even
though the System Architecture document lists "Approval" as a distinct core
entity; that listing is treated as superseded for MVP purposes by the PIGL/
Product decision recorded in Rev 2 §A.2.

ReportTemplate content (branding, section wording, exact PIGL format) is a
PIGL deliverable and is NOT populated with invented content anywhere in this
codebase (Rev 2 §H, §C item 2).
"""
import enum
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import gen_uuid, utcnow


class ReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PRELIMINARY = "PRELIMINARY"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    FINAL = "FINAL"
    SUPERSEDED = "SUPERSEDED"


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    client: Mapped[str | None] = mapped_column(String(255), nullable=True)
    structure: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON — section list, placeholder until PIGL supplies content
    required_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_calculations: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_figures: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_structure: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLACEHOLDER_PENDING_PIGL_CONTENT")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    template_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("report_templates.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False, default="DRAFT_ENGINEERING_SUMMARY")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ReportStatus.DRAFT.value)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReportSection(Base):
    __tablename__ = "report_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    report_id: Mapped[str] = mapped_column(String(36), ForeignKey("reports.id"), nullable=False)
    section_type: Mapped[str] = mapped_column(String(128), nullable=False)
    heading: Mapped[str] = mapped_column(String(255), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_ref: Mapped[str | None] = mapped_column(Text, nullable=True)  # pointer to structured project data assembled into this section
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class Review(Base):
    """Sole approval-representing entity (see module docstring)."""
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    object_type: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "CALCULATION", "REPORT", "METHODOLOGY_REQUEST"
    object_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewer: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # COMMENT | ACCEPT | REJECT | REQUEST_REVISION | APPROVE
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
