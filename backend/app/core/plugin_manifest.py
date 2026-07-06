from datetime import datetime

from pydantic import BaseModel, Field


class PluginStateChangeRequest(BaseModel):
    actor_id: str = Field(default="plugin-governance", min_length=2)
    reason: str = Field(default="Governed plugin state change.", min_length=5)
    evidence: dict = Field(default_factory=dict)


class PluginImpactRequest(PluginStateChangeRequest):
    intended_action: str = Field(default="disable", min_length=2)


class PluginApprovalRequest(PluginStateChangeRequest):
    intended_action: str = Field(default="disable", min_length=2)


class PluginManifest(BaseModel):
    plugin_id: str = Field(min_length=3)
    name: str = Field(min_length=3)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    status: str = "registered"
    validation: dict = Field(default_factory=dict)
    impact_analysis: dict = Field(default_factory=dict)
    change_approval: dict = Field(default_factory=dict)
    rollback_stack: list[dict] = Field(default_factory=list)
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


class PluginValidationReport(BaseModel):
    validation_id: str
    plugin_id: str
    status: str
    passed: bool
    checks: list[dict]
    validated_at: datetime
    data_platform: str = "DB MARIAM"


class PluginImpactReport(BaseModel):
    impact_id: str
    plugin_id: str
    intended_action: str
    risk_level: str
    affected_workflows: list[str]
    affected_permissions: list[str]
    affected_dependencies: list[str]
    governance_notes: list[str]
    analyzed_at: datetime
    data_platform: str = "DB MARIAM"


class PluginApprovalReport(BaseModel):
    approval_id: str
    plugin_id: str
    intended_action: str
    impact_id: str
    approved_at: datetime
    data_platform: str = "DB MARIAM"


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
