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


def test_runtime_event_endpoint_reads_saved_event_history() -> None:
    client = TestClient(create_app())
    publish_response = client.post(
        "/api/runtime/events",
        json={
            "name": "runtime.audit.test",
            "source": "test-suite",
            "payload": {"data_platform": "DB MARIAM"},
        },
    )
    event_id = publish_response.json()["event"]["event_id"]

    list_response = client.get("/api/runtime/events")

    assert event_id in [event["event_id"] for event in list_response.json()["events"]]
    event = next(event for event in list_response.json()["events"] if event["event_id"] == event_id)
    assert event["payload"]["data_platform"] == "DB MARIAM"


def test_mission_list_reads_saved_mission_history() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Prepare a renewal plan",
            "requested_by": "operator",
        },
    )
    mission_id = create_response.json()["mission"]["mission_id"]

    list_response = client.get("/api/missions")

    assert mission_id in [mission["mission_id"] for mission in list_response.json()["missions"]]
    mission = next(mission for mission in list_response.json()["missions"] if mission["mission_id"] == mission_id)
    assert mission["data_platform"] == "DB MARIAM"
    assert len(mission["steps"]) == 4


def test_ai_resource_manager_lists_ollama_as_provider_not_core() -> None:
    client = TestClient(create_app())
    response = client.get("/api/ai-resources/providers")
    assert response.status_code == 200
    providers = response.json()["providers"]
    ollama = next(provider for provider in providers if provider["provider_id"] == "ollama")
    assert ollama["provider_type"] == "model_runtime"
    assert ollama["local"] is True


def test_ai_resource_manager_routes_capability_to_local_provider() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/ai-resources/route",
        json={
            "capability": "chat",
            "privacy_preference": "local_first",
            "requested_by": "crm-chief",
        },
    )
    assert response.status_code == 200
    decision = response.json()["decision"]
    assert decision["route_id"]
    assert decision["created_at"]
    assert decision["requested_by"] == "crm-chief"
    assert decision["data_platform"] == "DB MARIAM"
    assert decision["selected_provider"]["provider_id"] == "ollama"
    assert decision["policy"] == "chief_requests_capability_ai_resource_manager_selects_provider"


def test_ai_resource_route_is_auditable_from_runtime_history() -> None:
    client = TestClient(create_app())
    route_response = client.post(
        "/api/ai-resources/route",
        json={
            "capability": "chat",
            "privacy_preference": "local_first",
            "requested_by": "crm-chief",
        },
    )
    route_id = route_response.json()["decision"]["route_id"]

    routes_response = client.get("/api/ai-resources/routes")
    event_response = client.get("/api/runtime/events")

    assert route_id in [route["route_id"] for route in routes_response.json()["routes"]]
    route = next(route for route in routes_response.json()["routes"] if route["route_id"] == route_id)
    assert route["requested_by"] == "crm-chief"
    assert route["data_platform"] == "DB MARIAM"
    assert route_id in [
        event["payload"].get("route_id")
        for event in event_response.json()["events"]
        if event["name"] == "ai_resource.route.selected"
    ]


def test_ai_resource_route_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    upgrade_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0002_ai_resource_route_storage.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    upgrade = upgrade_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS ai_resource_routes" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "fallback_provider_ids TEXT[]" in migration
    assert "ADD COLUMN IF NOT EXISTS data_platform" in upgrade
    assert "ADD COLUMN IF NOT EXISTS fallback_provider_ids" in upgrade


def test_mission_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    step_order_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0003_mission_step_order.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    step_order = step_order_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS missions" in migration
    assert "CREATE TABLE IF NOT EXISTS mission_steps" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "mission_id UUID NOT NULL REFERENCES missions" in migration
    assert "step_order INTEGER NOT NULL" in migration
    assert "ADD COLUMN IF NOT EXISTS step_order" in step_order


def test_runtime_event_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    migration = migration_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS runtime_events" in migration
    assert "payload JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "idx_runtime_events_name_created" in migration
