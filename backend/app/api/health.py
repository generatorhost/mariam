from fastapi import APIRouter, Depends

from app.services.runtime import RuntimeRegistry
from app.dependencies import get_runtime_registry

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
def health(registry: RuntimeRegistry = Depends(get_runtime_registry)) -> dict:
    return {
        "status": "healthy",
        "services": [service.__dict__ for service in registry.health()],
    }

