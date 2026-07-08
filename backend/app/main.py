from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    artifacts,
    audit,
    auth,
    ai_resources,
    health,
    missions,
    plugins,
    runtime,
    runtime_objects,
    seed_imports,
    terminology,
)
from app.core.config import get_settings
from app.core.errors import http_exception_handler, validation_exception_handler


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Mariam AI Enterprise OS API", version="0.1.0")
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    origins = [origin.strip() for origin in settings.api_cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(audit.router)
    app.include_router(artifacts.router)
    app.include_router(ai_resources.router)
    app.include_router(missions.router)
    app.include_router(plugins.router)
    app.include_router(runtime.router)
    app.include_router(runtime_objects.router)
    app.include_router(seed_imports.router)
    app.include_router(terminology.router)

    @app.get("/")
    def root() -> dict:
        return {
            "name": "Mariam AI Enterprise OS",
            "status": "documentation-driven rebuild",
            "architecture_library": "https://github.com/generatorhost/Mariam-Architecture-Library",
        }

    return app


app = create_app()
