from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.audit import AuditEvent
from app.routers import (
    auth, projects, investigations, geotech, geophysics, files,
    methodologies, calculations, reports, admin, geobrain, ingestion,
)

settings = get_settings()

app = FastAPI(title="Ground Intelligence API", version="0.1.0-mvp")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(investigations.router)
app.include_router(geotech.router)
app.include_router(geophysics.router)
app.include_router(files.router)
app.include_router(methodologies.router)
app.include_router(calculations.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(geobrain.router)
app.include_router(ingestion.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}


@app.get("/api/projects/{project_id}/audit-events")
def list_audit_events(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Not project-scoped at the DB level yet (AuditEvent has no project_id
    column in the MVP data model as specified) -- returns recent events with
    the requested object_type filters left to the caller. Included as a
    starting point for Phase 1's audit-infrastructure requirement."""
    events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(200).all()
    return [{"action": e.action, "object_type": e.object_type, "object_id": e.object_id,
             "user_id": e.user_id, "timestamp": e.timestamp.isoformat()} for e in events]
