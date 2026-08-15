import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class Project(UUIDPKMixin, TimestampMixin, Base):
    """
    Central project object (Implementation Design Rev 1 §1.1, Data Model §2).

    Only the fields needed for Phase 1 (project management + RBAC scoping)
    are populated here. Fields tied to later phases are NOT added
    speculatively -- e.g. no investigation/report counts, no GIS bounding
    box -- those belong to the dashboard aggregation built in Phase 2+.
    """
    __tablename__ = "projects"

    project_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"), nullable=False)
    project_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    client: Mapped["Client"] = relationship(back_populates="projects")
