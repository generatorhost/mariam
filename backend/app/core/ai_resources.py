from datetime import datetime

from pydantic import BaseModel, Field


class ModelProvider(BaseModel):
    provider_id: str
    name: str
    provider_type: str
    capabilities: list[str]
    local: bool
    status: str = "available"


class ResourceRouteRequest(BaseModel):
    capability: str = Field(min_length=2)
    privacy_preference: str = "local_first"
    max_cost: str = "low"
    requested_by: str = "local-user"


class ResourceRouteDecision(BaseModel):
    route_id: str
    capability: str
    selected_provider: ModelProvider
    reason: str
    policy: str
    requested_by: str
    data_platform: str = "DB MARIAM"
    fallback_provider_ids: list[str]
    created_at: datetime


PROVIDERS = [
    ModelProvider(
        provider_id="ollama",
        name="Ollama Provider",
        provider_type="model_runtime",
        capabilities=["chat", "local_inference", "embeddings"],
        local=True,
    ),
    ModelProvider(
        provider_id="openai",
        name="OpenAI Provider",
        provider_type="model_api",
        capabilities=["chat", "tool_calling", "vision", "embeddings"],
        local=False,
    ),
    ModelProvider(
        provider_id="llamacpp",
        name="llama.cpp Provider",
        provider_type="model_runtime",
        capabilities=["chat", "local_inference", "gguf"],
        local=True,
    ),
]
