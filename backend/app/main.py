from fastapi import FastAPI

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.projects.router import router as projects_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(admin_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
