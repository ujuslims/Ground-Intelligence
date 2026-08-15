from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.projects.router import router as projects_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    # Must come before the routers are exercised (middleware order doesn't
    # depend on include_router() order, but added here for readability).
    # allow_credentials=True is required for the session cookie to be
    # sent/received cross-origin; per the CORS spec, that means
    # allow_origins cannot be "*" -- it must be the frontend's actual
    # origin(s), read from settings so this never needs a code change per
    # environment.
    origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(projects_router)
    app.include_router(admin_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
