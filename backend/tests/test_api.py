from fastapi.testclient import TestClient
import json
from pathlib import Path

from app.main import create_app


def test_root_points_to_architecture_library() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["architecture_library"].endswith("Mariam-Architecture-Library")


def test_health_reports_runtime_services() -> None:
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert {service["name"] for service in body["services"]} >= {"api", "event_bus", "plugin_registry"}


def test_plugin_manifest_contract_is_executable() -> None:
    client = TestClient(create_app())
    manifest = {
        "plugin_id": "crm",
        "name": "CRM Workspace",
        "version": "0.1.0",
        "dashboard_route": "/plugins/crm",
        "settings_schema": {"type": "object"},
        "api_prefix": "/api/plugins/crm",
        "data_boundary": "private-plugin-tables",
        "permissions": ["crm.read", "crm.write"],
        "produced_events": ["crm.lead.created"],
        "consumed_events": ["communication.message.received"],
        "chief_agent_role": "CRM Chief Agent",
        "swarm_roles": ["Lead Reviewer", "Pipeline Planner"],
        "workflows": ["lead-intake", "proposal-review"],
        "provider_dependencies": [],
        "connector_dependencies": [],
        "runtime_dependencies": ["event_bus"],
        "tests": ["api", "runtime", "permissions"],
        "acceptance_criteria": ["registers successfully", "declares data boundary"],
        "rollback_plan": "disable plugin and keep data read-only",
    }
    response = client.post("/api/plugins", json=manifest)
    assert response.status_code == 200
    assert response.json()["plugin"]["plugin_id"] == "crm"


def test_repository_plugin_manifest_matches_runtime_contract() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    response = client.post("/api/plugins", json=manifest)
    assert response.status_code == 200
    assert response.json()["plugin"]["dashboard_route"] == "/plugins/crm"


def test_official_terminology_endpoint_exposes_required_terms() -> None:
    client = TestClient(create_app())
    response = client.get("/api/terminology")
    assert response.status_code == 200
    body = response.json()
    term_names = {term["name"] for term in body["terms"]}
    assert "Mariam Living Enterprise OS Core" in term_names
    assert "Mariam Data Platform" in term_names
    assert "Plugin Business Unit" in term_names
    assert "Business DB" in body["forbidden_aliases"]
    assert "AI Kernel" in body["forbidden_aliases"]


def test_create_mission_returns_button_to_result_flow() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Create a follow-up plan for a qualified lead",
            "requested_by": "operator",
        },
    )
    assert response.status_code == 200
    mission = response.json()["mission"]
    assert mission["plugin_id"] == "crm"
    assert mission["status"] == "awaiting_approval"
    assert mission["data_platform"] == "DB MARIAM"
    assert [step["name"] for step in mission["steps"]] == [
        "permission_check",
        "chief_planning",
        "runtime_scheduling",
        "approval_gate",
    ]


def test_mission_creation_emits_runtime_event() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/missions",
        json={"plugin_id": "crm", "user_request": "Prepare a client report"},
    )
    response = client.get("/api/runtime/events")
    names = [event["name"] for event in response.json()["events"]]
    assert "mission.created" in names
