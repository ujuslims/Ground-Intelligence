"""Import every model module so Alembic / Base.metadata sees all tables."""
from app.models import (  # noqa: F401
    identity,
    project,
    investigation,
    geotech,
    geophysics,
    files,
    engineering,
    reporting,
    audit,
)
