from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai_resources, health, missions, plugins, runtime, terminology
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Mariam AI Enterprise OS API", version="0.1.0")
    origins = [origin.strip() for origin in settings.api_cors_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(ai_resources.router)
    app.include_router(missions.router)
    app.include_router(plugins.router)
    app.include_router(runtime.router)
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
