from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    plugin_id: str = Field(min_length=3)
    name: str = Field(min_length=3)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    dashboard_route: str
    settings_schema: dict
    api_prefix: str
    data_boundary: str
    permissions: list[str]
    produced_events: list[str]
    consumed_events: list[str]
    chief_agent_role: str
    swarm_roles: list[str]
    workflows: list[str]
    provider_dependencies: list[str] = []
    connector_dependencies: list[str] = []
    runtime_dependencies: list[str] = []
    tests: list[str]
    acceptance_criteria: list[str]
    rollback_plan: str


def validate_manifest(manifest: PluginManifest) -> PluginManifest:
    if not manifest.dashboard_route.startswith("/plugins/"):
        raise ValueError("dashboard_route must start with /plugins/")
    if not manifest.api_prefix.startswith("/api/plugins/"):
        raise ValueError("api_prefix must start with /api/plugins/")
    if not manifest.permissions:
        raise ValueError("plugin must declare permissions")
    if not manifest.tests:
        raise ValueError("plugin must declare tests")
    return manifest

