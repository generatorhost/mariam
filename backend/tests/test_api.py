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


def test_plugin_list_reads_saved_plugin_registry() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    register_response = client.post("/api/plugins", json=manifest)
    plugin_id = register_response.json()["plugin"]["plugin_id"]

    list_response = client.get("/api/plugins")

    assert plugin_id in [plugin["plugin_id"] for plugin in list_response.json()["plugins"]]
    plugin = next(plugin for plugin in list_response.json()["plugins"] if plugin["plugin_id"] == plugin_id)
    assert plugin["data_boundary"] == "private-plugin-tables"
    assert plugin["chief_agent_role"] == "CRM Chief Agent"


def test_runtime_object_registration_is_executable_and_auditable() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Ollama Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime", "local": True},
        },
    )
    assert response.status_code == 200
    runtime_object = response.json()["runtime_object"]
    assert runtime_object["object_id"]
    assert runtime_object["object_type"] == "provider"
    assert runtime_object["status"] == "enabled"
    assert runtime_object["data_platform"] == "DB MARIAM"

    list_response = client.get("/api/runtime-objects")
    event_response = client.get("/api/runtime/events")
    audit_response = client.get("/api/audit")

    assert runtime_object["object_id"] in [
        item["object_id"] for item in list_response.json()["runtime_objects"]
    ]
    assert runtime_object["object_id"] in [
        event["payload"].get("object_id")
        for event in event_response.json()["events"]
        if event["name"] == "runtime_object.registered"
    ]
    assert runtime_object["object_id"] in [
        record["target_id"] for record in audit_response.json()["audit_records"]
    ]


def test_runtime_object_can_be_disabled_and_enabled_with_audit() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Toggle Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime"},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]

    disable_response = client.post(
        f"/api/runtime-objects/{object_id}/disable",
        json={
            "actor_id": "runtime-governance",
            "reason": "Disable for compatibility review.",
            "evidence": {"review": "compatibility-check"},
        },
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["runtime_object"]["status"] == "disabled"

    enable_response = client.post(
        f"/api/runtime-objects/{object_id}/enable",
        json={
            "actor_id": "runtime-governance",
            "reason": "Compatibility review passed.",
            "evidence": {"review": "passed"},
        },
    )
    assert enable_response.status_code == 200
    assert enable_response.json()["runtime_object"]["status"] == "enabled"

    list_response = client.get("/api/runtime-objects")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    runtime_object = next(
        item for item in list_response.json()["runtime_objects"] if item["object_id"] == object_id
    )
    assert runtime_object["status"] == "enabled"
    assert object_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] in {"runtime_object.disable", "runtime_object.enable"}
    ]
    assert object_id in [
        event["payload"].get("object_id")
        for event in event_response.json()["events"]
        if event["name"] in {"runtime_object.disable", "runtime_object.enable"}
    ]


def test_runtime_object_can_be_soft_deleted_and_restored_with_audit() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Soft Delete Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime"},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]

    delete_response = client.post(
        f"/api/runtime-objects/{object_id}/delete",
        json={
            "actor_id": "runtime-governance",
            "reason": "Soft delete before replacement.",
            "evidence": {"replacement": "pending"},
        },
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["runtime_object"]["status"] == "deleted"

    restore_response = client.post(
        f"/api/runtime-objects/{object_id}/restore",
        json={
            "actor_id": "runtime-governance",
            "reason": "Restore for compatibility review.",
            "evidence": {"review": "required-before-enable"},
        },
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["runtime_object"]["status"] == "disabled"

    list_response = client.get("/api/runtime-objects")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    runtime_object = next(
        item for item in list_response.json()["runtime_objects"] if item["object_id"] == object_id
    )
    assert runtime_object["status"] == "disabled"
    assert object_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] in {"runtime_object.soft_delete", "runtime_object.restore"}
    ]
    assert object_id in [
        event["payload"].get("object_id")
        for event in event_response.json()["events"]
        if event["name"] in {"runtime_object.soft_delete", "runtime_object.restore"}
    ]


def test_runtime_object_can_be_patched_with_audit() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Patch Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime", "local": True},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]

    patch_response = client.patch(
        f"/api/runtime-objects/{object_id}",
        json={
            "actor_id": "runtime-governance",
            "reason": "Upgrade provider metadata.",
            "name": "Patch Provider Upgraded",
            "version": "0.2.0",
            "manifest_updates": {"context_window": 8192, "benchmark": "passed"},
            "evidence": {"compatibility": "passed"},
        },
    )

    assert patch_response.status_code == 200
    runtime_object = patch_response.json()["runtime_object"]
    assert runtime_object["name"] == "Patch Provider Upgraded"
    assert runtime_object["version"] == "0.2.0"
    assert runtime_object["manifest"]["provider_type"] == "model_runtime"
    assert runtime_object["manifest"]["context_window"] == 8192

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert object_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "runtime_object.patch"
    ]
    assert object_id in [
        event["payload"].get("object_id")
        for event in event_response.json()["events"]
        if event["name"] == "runtime_object.patch"
    ]


def test_runtime_object_patch_can_be_rolled_back_with_audit() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Rollback Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime", "local": True},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]
    client.patch(
        f"/api/runtime-objects/{object_id}",
        json={
            "actor_id": "runtime-governance",
            "reason": "Upgrade before rollback.",
            "version": "0.2.0",
            "manifest_updates": {"benchmark": "passed"},
            "evidence": {"compatibility": "passed"},
        },
    )

    rollback_response = client.post(
        f"/api/runtime-objects/{object_id}/rollback",
        json={
            "actor_id": "runtime-governance",
            "reason": "Rollback failed compatibility review.",
            "evidence": {"compatibility": "failed-after-upgrade"},
        },
    )

    assert rollback_response.status_code == 200
    runtime_object = rollback_response.json()["runtime_object"]
    assert runtime_object["version"] == "0.1.0"
    assert runtime_object["manifest"]["provider_type"] == "model_runtime"
    assert "benchmark" not in runtime_object["manifest"]

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert object_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "runtime_object.rollback"
    ]
    assert object_id in [
        event["payload"].get("object_id")
        for event in event_response.json()["events"]
        if event["name"] == "runtime_object.rollback"
    ]


def test_runtime_object_can_be_exported_as_dna_with_audit() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "DNA Export Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime", "local": True},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]
    client.patch(
        f"/api/runtime-objects/{object_id}",
        json={
            "actor_id": "runtime-governance",
            "reason": "Prepare export metadata.",
            "version": "0.2.0",
            "manifest_updates": {"benchmark": "passed"},
            "evidence": {"compatibility": "passed"},
        },
    )

    export_response = client.post(
        f"/api/runtime-objects/{object_id}/export-dna",
        json={
            "actor_id": "runtime-governance",
            "reason": "Export provider as DNA.",
            "evidence": {"export_review": "passed"},
        },
    )

    assert export_response.status_code == 200
    dna_package = export_response.json()["dna_package"]
    assert dna_package["dna_package_id"].startswith("dna-")
    assert dna_package["source_object_id"] == object_id
    assert dna_package["payload"]["schema"] == "mariam.runtime_object.dna.v1"
    assert dna_package["payload"]["manifest"]["benchmark"] == "passed"
    assert "_rollback_stack" not in dna_package["payload"]["manifest"]

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert object_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "runtime_object.export_dna"
    ]
    assert dna_package["dna_package_id"] in [
        event["payload"].get("dna_package_id")
        for event in event_response.json()["events"]
        if event["name"] == "runtime_object.export_dna"
    ]


def test_runtime_object_dna_can_be_imported_disabled_with_audit() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "DNA Import Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime", "local": True},
        },
    )
    source_object_id = create_response.json()["runtime_object"]["object_id"]
    export_response = client.post(
        f"/api/runtime-objects/{source_object_id}/export-dna",
        json={
            "actor_id": "runtime-governance",
            "reason": "Export before import test.",
            "evidence": {"export_review": "passed"},
        },
    )
    dna_package = export_response.json()["dna_package"]

    import_response = client.post(
        "/api/runtime-objects/import-dna",
        json={
            "actor_id": "runtime-governance",
            "reason": "Import DNA package for review.",
            "dna_package": dna_package,
            "evidence": {"import_review": "requires-enable-approval"},
        },
    )

    assert import_response.status_code == 200
    imported = import_response.json()["runtime_object"]
    assert imported["object_id"] != source_object_id
    assert imported["name"] == "DNA Import Provider Imported"
    assert imported["status"] == "disabled"
    assert imported["manifest"]["dna_import"]["source_dna_package_id"] == dna_package["dna_package_id"]
    assert imported["manifest"]["dna_import"]["requires_governance_review_before_enable"] is True

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert imported["object_id"] in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "runtime_object.import_dna"
    ]
    assert imported["object_id"] in [
        event["payload"].get("object_id")
        for event in event_response.json()["events"]
        if event["name"] == "runtime_object.import_dna"
    ]


def test_runtime_object_validation_passes_and_records_audit() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Validation Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime", "local": True},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]

    validate_response = client.post(
        f"/api/runtime-objects/{object_id}/validate",
        json={
            "actor_id": "runtime-governance",
            "reason": "Validate before activation.",
            "evidence": {"review": "pre-enable"},
        },
    )

    assert validate_response.status_code == 200
    report = validate_response.json()["validation_report"]
    assert report["object_id"] == object_id
    assert report["passed"] is True
    assert all(check["passed"] for check in report["checks"])

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert object_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "runtime_object.validate" and record["decision"] == "approved"
    ]
    assert report["validation_id"] in [
        event["payload"].get("validation_id")
        for event in event_response.json()["events"]
        if event["name"] == "runtime_object.validate"
    ]


def test_runtime_object_validation_rejects_invalid_provider_manifest() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Invalid Validation Provider",
            "version": "0.1.0",
            "manifest": {"local": True},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]

    validate_response = client.post(
        f"/api/runtime-objects/{object_id}/validate",
        json={
            "actor_id": "runtime-governance",
            "reason": "Validate before activation.",
            "evidence": {"review": "pre-enable"},
        },
    )

    assert validate_response.status_code == 200
    report = validate_response.json()["validation_report"]
    assert report["passed"] is False
    assert any(check["name"] == "provider_type_present" and not check["passed"] for check in report["checks"])

    audit_response = client.get("/api/audit")
    assert object_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "runtime_object.validate" and record["decision"] == "rejected"
    ]


def test_audit_endpoint_records_governance_decision() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/audit",
        json={
            "actor_id": "governance-gate",
            "action": "artifact.approve",
            "target_type": "report",
            "target_id": "report-001",
            "decision": "approved",
            "evidence": {"data_platform": "DB MARIAM"},
        },
    )
    assert response.status_code == 200
    audit_record = response.json()["audit_record"]
    assert audit_record["audit_id"]
    assert audit_record["data_platform"] == "DB MARIAM"

    list_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert audit_record["audit_id"] in [
        record["audit_id"] for record in list_response.json()["audit_records"]
    ]
    assert audit_record["audit_id"] in [
        event["payload"].get("audit_id")
        for event in event_response.json()["events"]
        if event["name"] == "audit.recorded"
    ]


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


def test_mission_approval_updates_status_and_records_governance() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Approve a client delivery package",
            "requested_by": "operator",
        },
    )
    mission_id = create_response.json()["mission"]["mission_id"]

    approve_response = client.post(
        f"/api/missions/{mission_id}/approve",
        json={
            "approved_by": "governance-lead",
            "evidence": {"approval_reason": "review complete"},
        },
    )

    assert approve_response.status_code == 200
    approved = approve_response.json()["mission"]
    assert approved["mission_id"] == mission_id
    assert approved["status"] == "approved"

    list_response = client.get("/api/missions")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    mission = next(mission for mission in list_response.json()["missions"] if mission["mission_id"] == mission_id)
    assert mission["status"] == "approved"
    assert mission_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "mission.approve"
    ]
    assert mission_id in [
        event["payload"].get("mission_id")
        for event in event_response.json()["events"]
        if event["name"] == "mission.approved"
    ]


def test_mission_rejection_updates_status_and_records_governance() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Reject an incomplete client delivery package",
            "requested_by": "operator",
        },
    )
    mission_id = create_response.json()["mission"]["mission_id"]

    reject_response = client.post(
        f"/api/missions/{mission_id}/reject",
        json={
            "rejected_by": "governance-lead",
            "reason": "Delivery package is missing approval evidence.",
            "evidence": {"review": "missing evidence"},
        },
    )

    assert reject_response.status_code == 200
    rejected = reject_response.json()["mission"]
    assert rejected["mission_id"] == mission_id
    assert rejected["status"] == "rejected"

    list_response = client.get("/api/missions")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    mission = next(mission for mission in list_response.json()["missions"] if mission["mission_id"] == mission_id)
    assert mission["status"] == "rejected"
    assert mission_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "mission.reject"
    ]
    assert mission_id in [
        event["payload"].get("mission_id")
        for event in event_response.json()["events"]
        if event["name"] == "mission.rejected"
    ]


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


def test_runtime_summary_reports_command_center_counts() -> None:
    client = TestClient(create_app())
    client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Command Center Summary Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime"},
        },
    )
    client.post(
        "/api/audit",
        json={
            "actor_id": "command-center",
            "action": "runtime.summary.refresh",
            "target_type": "dashboard",
            "target_id": "command-center",
            "decision": "approved",
            "evidence": {"data_platform": "DB MARIAM"},
        },
    )

    response = client.get("/api/runtime/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["health"] == "healthy"
    assert body["runtime_objects"] >= 1
    assert body["audit_records"] >= 1
    assert isinstance(body["plugins"], int)
    assert isinstance(body["missions"], int)
    assert isinstance(body["ai_routes"], int)
    assert isinstance(body["runtime_events"], int)
    assert len(body["recent_events"]) <= 5
    assert body["recent_events"][0]["name"] == "audit.recorded"
    assert body["recent_events"][0]["source"] == "audit-service"


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


def test_plugin_manifest_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    migration = migration_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS plugin_manifests" in migration
    assert "manifest JSONB NOT NULL" in migration
    assert "status TEXT NOT NULL DEFAULT 'registered'" in migration


def test_runtime_object_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    migration = migration_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS runtime_objects" in migration
    assert "object_type TEXT NOT NULL" in migration
    assert "manifest JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "idx_runtime_objects_type_status" in migration


def test_audit_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    migration = migration_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS audit_log" in migration
    assert "decision TEXT NOT NULL" in migration
    assert "evidence JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
