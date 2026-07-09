from fastapi.testclient import TestClient
import json
from pathlib import Path
from zipfile import ZipFile

from app.core.auth import UserSession
from app.dependencies import get_auth_service
from app.main import create_app
from app.services.auth import AuthService


def analyze_runtime_object_impact(client: TestClient, object_id: str, intended_action: str) -> None:
    response = client.post(
        f"/api/runtime-objects/{object_id}/impact-analysis",
        json={
            "actor_id": "runtime-governance",
            "reason": f"Analyze before {intended_action}.",
            "intended_action": intended_action,
            "evidence": {"review": f"pre-{intended_action}"},
        },
    )
    assert response.status_code == 200


def approve_runtime_object_change(client: TestClient, object_id: str, intended_action: str) -> None:
    response = client.post(
        f"/api/runtime-objects/{object_id}/approve-change",
        json={
            "actor_id": "runtime-governance",
            "reason": f"Approve {intended_action}.",
            "intended_action": intended_action,
            "evidence": {"review": f"approved-{intended_action}"},
        },
    )
    assert response.status_code == 200


def validate_and_enable_plugin(client: TestClient, plugin_id: str) -> None:
    validate_response = client.post(
        f"/api/plugins/{plugin_id}/validate",
        json={
            "actor_id": "plugin-governance",
            "reason": "Validate before enable.",
            "evidence": {"review": "passed"},
        },
    )
    assert validate_response.status_code == 200
    enable_response = client.post(
        f"/api/plugins/{plugin_id}/enable",
        json={
            "actor_id": "plugin-governance",
            "reason": "Enable after validation.",
            "evidence": {"review": "passed"},
        },
    )
    assert enable_response.status_code == 200


def test_remote_execution_commander_manifest_and_dry_run() -> None:
    client = TestClient(create_app())

    manifest_response = client.get("/api/plugins/remote-execution-commander/manifest")
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["plugin_id"] == "remote-execution-commander"
    assert manifest["chief_agent_role"] == "Remote Execution Chief Agent"
    assert "remote_execution_commander_jobs" in manifest["private_tables"]
    assert "dry-run by default" in manifest["governance_gates"]

    dry_run_response = client.post(
        "/api/plugins/remote-execution-commander/commands",
        json={
            "command": "Get-ChildItem",
            "working_directory": ".",
            "dry_run": True,
            "actor_id": "command-center-operator",
            "reason": "Preview safe repository listing before execution.",
            "evidence": {"test": "dry_run"},
        },
    )
    assert dry_run_response.status_code == 200
    dry_run_job = dry_run_response.json()
    assert dry_run_job["status"] == "dry_run"
    assert dry_run_job["allowed"] is True
    assert dry_run_job["stdout"] == "Dry run accepted. Command was not executed."
    assert dry_run_job["data_platform"] == "DB MARIAM"


def test_remote_execution_commander_blocks_unsafe_commands() -> None:
    client = TestClient(create_app())

    blocked_response = client.post(
        "/api/plugins/remote-execution-commander/commands",
        json={
            "command": "Remove-Item .\\README.md",
            "working_directory": ".",
            "dry_run": False,
            "approval_token": "LOCAL_OPERATOR_APPROVED",
            "actor_id": "command-center-operator",
            "reason": "Unsafe command should be rejected.",
            "evidence": {"test": "blocked_term"},
        },
    )
    assert blocked_response.status_code == 200
    blocked_job = blocked_response.json()
    assert blocked_job["status"] == "blocked"
    assert blocked_job["allowed"] is False
    assert "blocked command term detected" in blocked_job["safety_notes"][0]


def test_remote_execution_commander_executes_approved_readonly_command() -> None:
    client = TestClient(create_app())

    run_response = client.post(
        "/api/plugins/remote-execution-commander/commands",
        json={
            "command": "Get-ChildItem README.md",
            "working_directory": ".",
            "dry_run": False,
            "approval_token": "LOCAL_OPERATOR_APPROVED",
            "actor_id": "command-center-operator",
            "reason": "Run approved read-only repository inspection.",
            "evidence": {"test": "approved_readonly"},
        },
    )
    assert run_response.status_code == 200
    job = run_response.json()
    assert job["allowed"] is True
    assert job["status"] == "succeeded"
    assert job["exit_code"] == 0
    assert "README.md" in job["stdout"]

    jobs_response = client.get("/api/plugins/remote-execution-commander/jobs")
    assert jobs_response.status_code == 200
    assert any(item["job_id"] == job["job_id"] for item in jobs_response.json())


def test_mayou_seed_import_extracts_living_plugin_candidates() -> None:
    source_path = Path(r"C:\1\mayou-1001")
    assert source_path.exists()
    client = TestClient(create_app())

    response = client.post(
        "/api/seed-imports/inspect",
        json={
            "source_path": str(source_path),
            "actor_id": "seed-import-chief",
            "reason": "Extract mayou-1001 as living DNA plugin candidates.",
            "evidence": {"mode": "living_seed_to_plugin_runtime"},
        },
    )

    assert response.status_code == 200
    seed_import = response.json()["seed_import"]
    assert seed_import["data_platform"] == "DB MARIAM"
    assert seed_import["coverage"]["files_scanned"] == 3054052
    assert seed_import["plugin_candidates"]
    assert seed_import["dna_objects"]
    assert seed_import["dna_object_counts"]["Chief"] == 1
    assert seed_import["dna_object_counts"]["Agent"] == 1
    assert seed_import["dna_object_counts"]["MCP Server"] == 1
    assert seed_import["dna_object_counts"]["Vector Index"] == 1

    candidates = {candidate["plugin_id"]: candidate for candidate in seed_import["plugin_candidates"]}
    assert "plugin_mcp_runtime_manager" in candidates
    assert "mcp" in candidates["plugin_mcp_runtime_manager"]["source_domains"]
    assert candidates["plugin_mcp_runtime_manager"]["governance_gate"] == "seed_review_before_activation"

    source_id = seed_import["source_id"]
    promote_response = client.post(
        f"/api/seed-imports/{source_id}/plugin-candidates/plugin_mcp_runtime_manager/promote",
        json={
            "actor_id": "seed-import-chief",
            "reason": "Promote MCP candidate as disabled plugin for governance review.",
            "evidence": {"dedupe_rule": "merge_repeated_mcp_features"},
        },
    )

    assert promote_response.status_code == 200
    promoted = promote_response.json()
    assert promoted["plugin_id"] == "plugin_mcp_runtime_manager"
    assert promoted["status"] == "disabled"

    load_response = client.post(
        f"/api/seed-imports/{source_id}/load-runtime-objects",
        json={
            "actor_id": "seed-runtime-chief",
            "reason": "Load extracted mayou DNA objects into DB MARIAM runtime store.",
            "evidence": {"mode": "living_seed_runtime_load"},
        },
    )
    assert load_response.status_code == 200
    loaded = load_response.json()
    assert loaded["runtime_store"] == "runtime_objects"
    assert loaded["loaded_counts"]["Chief"] == 1
    assert len(loaded["loaded_runtime_object_ids"]) == len(seed_import["dna_objects"])

    runtime_objects_response = client.get("/api/runtime-objects")
    assert runtime_objects_response.status_code == 200
    runtime_objects = runtime_objects_response.json()["runtime_objects"]
    assert any(item["object_type"] == "MCP Server" for item in runtime_objects)

    plugin_response = client.get("/api/plugins/plugin_mcp_runtime_manager/workspace")
    assert plugin_response.status_code == 200
    workspace = plugin_response.json()
    assert workspace["data_boundary"]["private_tables"] == [
        "plugin_mcp_runtime_manager_settings",
        "plugin_mcp_runtime_manager_workflows",
        "plugin_mcp_runtime_manager_artifacts",
    ]


def test_seed_import_accepts_zip_package_path(tmp_path) -> None:
    seed_root = tmp_path / "seed-package"
    registry = seed_root / "registry" / "mcp"
    registry.mkdir(parents=True)
    (seed_root / "SOURCE_COVERAGE.json").write_text(
        json.dumps(
            {
                "eligible_files_discovered": 3,
                "files_scanned": 3,
                "files_failed": 0,
                "source_coverage_pct": 100,
            }
        ),
        encoding="utf-8",
    )
    (registry / "SUMMARY.json").write_text(
        json.dumps(
            {
                "runtime_readiness": "high",
                "total_matching_assets": 2,
                "total_matching_terms": 4,
                "top_source_projects": [{"name": "zip-seed", "count": 2}],
                "top_source_categories": [{"name": "mcp", "count": 2}],
            }
        ),
        encoding="utf-8",
    )
    zip_path = tmp_path / "seed-package.zip"
    with ZipFile(zip_path, "w") as archive:
        for path in seed_root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(tmp_path))

    client = TestClient(create_app())
    response = client.post(
        "/api/seed-imports/inspect",
        json={
            "source_path": str(zip_path),
            "actor_id": "seed-import-chief",
            "reason": "Extract uploaded ZIP package as living DNA.",
            "evidence": {"mode": "zip_seed_package"},
        },
    )

    assert response.status_code == 200
    seed_import = response.json()["seed_import"]
    assert seed_import["source_name"] == "seed-package.zip"
    assert seed_import["coverage"]["files_scanned"] == 3
    candidates = {candidate["plugin_id"]: candidate for candidate in seed_import["plugin_candidates"]}
    assert "plugin_mcp_runtime_manager" in candidates
    assert seed_import["dna_object_counts"]["MCP Server"] == 1


def test_seed_import_accepts_generic_project_folder_without_registry(tmp_path) -> None:
    project_root = tmp_path / "raw-project"
    project_root.mkdir()
    (project_root / "README.md").write_text(
        "Chief agent workflow knowledge vector model provider api governance docker crm video gguf",
        encoding="utf-8",
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/seed-imports/inspect",
        json={
            "source_path": str(project_root),
            "actor_id": "seed-import-chief",
            "reason": "Extract raw project folder as generic living DNA.",
            "evidence": {"mode": "generic_folder_dna"},
        },
    )

    assert response.status_code == 200
    seed_import = response.json()["seed_import"]
    assert seed_import["coverage"]["extraction_mode"] == "generic_folder_dna"
    assert seed_import["domain_evidence"]
    assert seed_import["plugin_candidates"]
    assert seed_import["dna_objects"]
    assert {"Chief", "Agent", "Workflow", "Model", "Provider"}.issubset(seed_import["dna_object_counts"])
    agent_object = next(item for item in seed_import["dna_objects"] if item["object_type"] == "Agent")
    assert agent_object["extraction_evidence"]
    assert agent_object["extraction_evidence"][0]["file"] == "README.md"
    assert "chief agent workflow" in agent_object["extraction_evidence"][0]["snippet"]


def test_seed_pipeline_full_mode_extracts_loads_and_promotes_plugins(tmp_path) -> None:
    project_root = tmp_path / "full-pipeline-project"
    project_root.mkdir()
    (project_root / "README.md").write_text(
        "Chief agent workflow knowledge vector model provider api governance docker crm freelancer remote work",
        encoding="utf-8",
    )

    client = TestClient(create_app())
    response = client.post(
        "/api/seed-imports/pipeline",
        json={
            "source_path": str(project_root),
            "activation_mode": "full",
            "actor_id": "seed-import-chief",
            "reason": "Extract, load, and promote plugin candidates from one operator action.",
            "evidence": {"mode": "full_pipeline_test"},
        },
    )

    assert response.status_code == 200
    pipeline = response.json()
    assert pipeline["activation_mode"] == "full"
    assert pipeline["seed_import"]["dna_objects"]
    assert pipeline["runtime_load"]["loaded_runtime_object_ids"]
    assert pipeline["promoted_plugins"]
    assert all(plugin["status"] == "disabled" for plugin in pipeline["promoted_plugins"])
    assert any(
        table.endswith("_settings")
        for plugin in pipeline["promoted_plugins"]
        for table in plugin["private_tables"]
    )

    runtime_response = client.get("/api/runtime-objects")
    assert runtime_response.status_code == 200
    runtime_objects = runtime_response.json()["runtime_objects"]
    assert len(runtime_objects) >= len(pipeline["runtime_load"]["loaded_runtime_object_ids"])
    loaded_ids = set(pipeline["runtime_load"]["loaded_runtime_object_ids"])
    loaded_object = next(item for item in runtime_objects if item["object_id"] in loaded_ids)
    assert loaded_object["manifest"]["extraction_evidence"]


def test_external_seed_sources_prepare_moneyprinter_and_gguf_dna_candidates() -> None:
    client = TestClient(create_app())

    source_response = client.get("/api/seed-imports/external-sources")
    assert source_response.status_code == 200
    source_keys = {
        source["source_key"]
        for source in source_response.json()["external_sources"]
    }
    assert {"moneyprinterturbo", "huggingface-gguf"}.issubset(source_keys)

    moneyprinter_response = client.post(
        "/api/seed-imports/external-sources/moneyprinterturbo/prepare",
        json={
            "source_path": "https://github.com/harry0703/MoneyPrinterTurbo",
            "actor_id": "seed-import-chief",
            "reason": "Prepare MoneyPrinterTurbo as video generation DNA.",
            "evidence": {"mode": "external_repository_dna"},
        },
    )
    assert moneyprinter_response.status_code == 200
    moneyprinter_import = moneyprinter_response.json()["seed_import"]
    moneyprinter_candidates = {
        candidate["plugin_id"]: candidate
        for candidate in moneyprinter_import["plugin_candidates"]
    }
    assert "plugin_video_generation_manager" in moneyprinter_candidates
    assert "video_generation" in moneyprinter_candidates["plugin_video_generation_manager"]["source_domains"]
    assert moneyprinter_import["dna_object_counts"]["Workflow"] == 1
    assert moneyprinter_import["dna_object_counts"]["Provider"] == 1

    gguf_response = client.post(
        "/api/seed-imports/external-sources/huggingface-gguf/prepare",
        json={
            "source_path": "https://huggingface.co/models?library=gguf",
            "actor_id": "seed-import-chief",
            "reason": "Prepare HuggingFace GGUF catalog as model provider DNA.",
            "evidence": {"mode": "external_model_catalog_dna"},
        },
    )
    assert gguf_response.status_code == 200
    gguf_import = gguf_response.json()["seed_import"]
    gguf_candidates = {
        candidate["plugin_id"]: candidate
        for candidate in gguf_import["plugin_candidates"]
    }
    assert "plugin_gguf_model_catalog_manager" in gguf_candidates
    assert gguf_import["dna_object_counts"]["Model"] == 1
    assert gguf_import["dna_object_counts"]["Provider"] == 1
    assert gguf_candidates["plugin_gguf_model_catalog_manager"]["governance_gate"] == (
        "external_seed_review_before_activation"
    )


def test_postgres_plugin_repository_recovers_minimal_legacy_manifest() -> None:
    from app.repositories.plugins import PostgresPluginRepository

    repository = PostgresPluginRepository("postgresql://unused")
    manifest = repository._row_to_manifest(
        {
            "plugin_id": "repository-smoke-example",
            "name": "DB MARIAM Repository Smoke Plugin",
            "version": "0.1.0",
            "dashboard_route": "/plugins/repository-smoke-example",
            "api_prefix": "/api/plugins/repository-smoke-example",
            "data_boundary": "repository-smoke-example",
            "status": "registered",
            "manifest": {
                "plugin_id": "repository-smoke-example",
                "verification": "repository-write-smoke",
                "data_platform": "DB MARIAM",
            },
        }
    )

    assert manifest.name == "DB MARIAM Repository Smoke Plugin"
    assert manifest.permissions == ["repository-smoke-example.read"]
    assert manifest.chief_agent_role == "DB MARIAM Repository Smoke Plugin Chief Agent"


def test_postgres_ai_route_repository_recovers_unknown_provider() -> None:
    from datetime import datetime, timezone

    from app.repositories.ai_resource_routes import PostgresAIResourceRouteRepository

    repository = PostgresAIResourceRouteRepository("postgresql://unused")
    decision = repository._row_to_decision(
        {
            "route_id": "route-unknown-provider",
            "capability": "local-coding",
            "selected_provider_id": "deepseek-coder-local",
            "policy": "local_first",
            "reason": "Legacy DB MARIAM route references a provider not in the current catalog.",
            "requested_by": "test-user",
            "data_platform": "DB MARIAM",
            "fallback_provider_ids": ["ollama"],
            "created_at": datetime.now(timezone.utc),
        }
    )

    assert decision.selected_provider.provider_id == "deepseek-coder-local"
    assert decision.selected_provider.status == "unknown"
    assert decision.fallback_provider_ids == ["ollama"]


def test_postgres_agent_runtime_repository_converts_uuid_rows_to_strings() -> None:
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.repositories.agents import PostgresAgentRuntimeRepository

    repository = PostgresAgentRuntimeRepository("postgresql://unused")
    society_id = uuid4()
    execution_id = uuid4()
    society = repository._row_to_society(
        {
            "society_id": society_id,
            "plugin_id": "crm",
            "business_unit_name": "CRM Business Unit",
            "chief_node_id": "crm_chief",
            "nodes": [
                {
                    "node_id": "crm_chief",
                    "plugin_id": "crm",
                    "role": "chief",
                    "title": "CRM Chief Agent",
                    "reports_to": "mariam_enterprise_chief",
                    "skills": ["planning"],
                    "capabilities": ["crm_execution"],
                    "permissions": ["crm.mission.plan"],
                    "status": "active",
                    "data_boundary": "crm_agent_runtime",
                }
            ],
            "data_platform": "DB MARIAM",
            "created_at": datetime.now(timezone.utc),
        }
    )
    execution = repository._row_to_execution(
        {
            "execution_id": execution_id,
            "plugin_id": "crm",
            "user_request": "Plan a follow-up.",
            "requested_by": "test",
            "chief_node_id": "crm_chief",
            "tasks": [],
            "communication_channels": ["chief_chat"],
            "review_gates": ["human_approval"],
            "status": "planned",
            "data_platform": "DB MARIAM",
            "created_at": datetime.now(timezone.utc),
        }
    )

    assert society.society_id == str(society_id)
    assert execution.execution_id == str(execution_id)


def test_huggingface_non_gguf_model_url_extracts_model_provider_without_gguf_candidate() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/seed-imports/inspect",
        json={
            "source_path": "https://huggingface.co/Qwen/Qwen2-Audio-7B-Instruct",
            "actor_id": "seed-import-chief",
            "reason": "Extract Qwen audio model as model/provider DNA.",
            "evidence": {"mode": "huggingface_model_dna"},
        },
    )

    assert response.status_code == 200
    seed_import = response.json()["seed_import"]
    assert seed_import["coverage"]["extraction_mode"] == "huggingface_model_dna"
    assert seed_import["dna_object_counts"]["Model"] == 1
    assert seed_import["dna_object_counts"]["Provider"] == 1
    assert seed_import["dna_object_counts"]["Capability"] == 1
    candidates = {candidate["plugin_id"] for candidate in seed_import["plugin_candidates"]}
    assert "plugin_model_provider_manager" in candidates
    assert "plugin_gguf_model_catalog_manager" not in candidates


def test_agent_runtime_builds_plugin_society_and_execution_plan() -> None:
    client = TestClient(create_app())

    society_response = client.post(
        "/api/agents/societies",
        json={
            "plugin_id": "plugin_video_generation_manager",
            "business_unit_name": "Video Generation Business Unit",
            "requested_by": "enterprise-chief",
            "team_domains": ["requirements", "generation", "review"],
            "skills": ["script_planning", "media_selection"],
            "capabilities": ["client_video_delivery"],
        },
    )

    assert society_response.status_code == 200
    society = society_response.json()["agent_society"]
    assert society["data_platform"] == "DB MARIAM"
    assert society["chief_node_id"] == "plugin_video_generation_manager_chief"
    roles = {node["role"] for node in society["nodes"]}
    assert {"chief", "team_leader", "agent", "reviewer"}.issubset(roles)
    assert all(node["data_boundary"] == "plugin_video_generation_manager_agent_runtime" for node in society["nodes"])

    plan_response = client.post(
        "/api/agents/executions/plan",
        json={
            "plugin_id": "plugin_video_generation_manager",
            "user_request": "Create a short product video for client review.",
            "requested_by": "local-user",
            "priority": "normal",
        },
    )

    assert plan_response.status_code == 200
    execution = plan_response.json()["agent_execution"]
    assert execution["data_platform"] == "DB MARIAM"
    assert execution["chief_node_id"] == society["chief_node_id"]
    assert execution["status"] == "planned"
    assert len(execution["tasks"]) == 4
    assert "human_approval" in execution["review_gates"]
    assert execution["tasks"][-1]["governance_gate"] == "human_approval_before_delivery"


def test_workflow_engine_defines_and_runs_governed_steps() -> None:
    client = TestClient(create_app())

    workflow_response = client.post(
        "/api/workflows",
        json={
            "plugin_id": "plugin_video_generation_manager",
            "name": "Client video delivery workflow",
            "requested_by": "workflow-governance",
            "permissions": ["plugin_video_generation_manager.workflow.run"],
            "steps": [
                {
                    "step_key": "intake",
                    "title": "Analyze client request",
                    "agent_role": "chief",
                    "action": "extract_requirements",
                    "requires_approval": False,
                },
                {
                    "step_key": "generate",
                    "title": "Generate delivery draft",
                    "agent_role": "agent",
                    "action": "produce_artifact",
                    "requires_approval": False,
                },
                {
                    "step_key": "approve",
                    "title": "Approve before delivery",
                    "agent_role": "reviewer",
                    "action": "human_review",
                    "requires_approval": True,
                },
            ],
        },
    )

    assert workflow_response.status_code == 200
    workflow = workflow_response.json()["workflow"]
    assert workflow["data_platform"] == "DB MARIAM"
    assert workflow["plugin_id"] == "plugin_video_generation_manager"
    assert len(workflow["steps"]) == 3

    run_response = client.post(
        "/api/workflows/runs",
        json={
            "workflow_id": workflow["workflow_id"],
            "requested_by": "command-center-user",
            "input_payload": {"client_request": "Produce video proposal"},
        },
    )

    assert run_response.status_code == 200
    workflow_run = run_response.json()["workflow_run"]
    assert workflow_run["data_platform"] == "DB MARIAM"
    assert workflow_run["status"] == "awaiting_approval"
    assert len(workflow_run["step_runs"]) == 3
    assert workflow_run["step_runs"][-1]["requires_approval"] is True
    assert workflow_run["step_runs"][-1]["status"] == "awaiting_approval"


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


def test_api_error_contract_is_exposed_for_governed_endpoints() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/api-error-contract")

    assert response.status_code == 200
    contract = response.json()
    assert contract["title"] == "Mariam Structured API Error Response Contract"
    assert contract["status"] == "ready"
    assert contract["data_platform"] == "DB MARIAM"
    assert "error.request_id" in contract["required_fields"]
    assert "governed_endpoints" in contract["applies_to"]
    assert set(contract["openapi_response_examples"].keys()) == {"403", "404", "422"}
    assert (
        contract["openapi_response_examples"]["403"]["content"]["application/json"]["example"]["error"]["data_platform"]
        == "DB MARIAM"
    )


def test_openapi_documents_structured_api_error_examples() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/runtime/api-error-contract"]["get"]
    for status_code in ["403", "404", "422"]:
        example = operation["responses"][status_code]["content"]["application/json"]["example"]
        assert example["error"]["status_code"] == int(status_code)
        assert example["error"]["request_id"] == "openapi-example-request"
        assert example["error"]["data_platform"] == "DB MARIAM"
        assert example["error"]["traceability"]["contract_version"] == "v1"


def test_api_not_found_errors_follow_structured_contract() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/runtime/not-found-for-error-contract",
        headers={"x-mariam-request-id": "error-contract-404"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "Not Found"
    assert body["error"]["code"] == "http_404"
    assert body["error"]["status_code"] == 404
    assert body["error"]["path"] == "/api/runtime/not-found-for-error-contract"
    assert body["error"]["request_id"] == "error-contract-404"
    assert body["error"]["data_platform"] == "DB MARIAM"
    assert body["error"]["traceability"]["governed"] is True


def test_auth_session_exposes_roles_and_permissions() -> None:
    client = TestClient(create_app())

    response = client.get("/api/auth/session")

    assert response.status_code == 200
    session = response.json()["session"]
    assert session["user_id"] == "command-center-operator"
    assert "governance-reviewer" in session["roles"]
    assert "artifact.approve" in session["permissions"]
    assert session["data_platform"] == "DB MARIAM"


def test_auth_request_context_uses_session_default_actor() -> None:
    client = TestClient(create_app())

    response = client.get("/api/auth/request-context")

    assert response.status_code == 200
    context = response.json()["request_context"]
    assert context["request_id"] == "local-command-center-request"
    assert context["actor_id"] == "command-center-operator"
    assert context["actor_matches_session"] is True
    assert context["propagation_mode"] == "session-default"
    assert context["headers_used"] == []
    assert context["data_platform"] == "DB MARIAM"


def test_auth_request_context_reads_actor_headers() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/auth/request-context",
        headers={
            "x-mariam-request-id": "request-123",
            "x-mariam-actor-id": "command-center-operator",
        },
    )

    assert response.status_code == 200
    context = response.json()["request_context"]
    assert context["request_id"] == "request-123"
    assert context["actor_id"] == "command-center-operator"
    assert context["actor_matches_session"] is True
    assert context["propagation_mode"] == "headers"
    assert set(context["headers_used"]) == {"x-mariam-request-id", "x-mariam-actor-id"}


def test_auth_permission_check_reports_allowed_permission() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/auth/permissions/check",
        json={
            "actor_id": "command-center-operator",
            "permission": "governance.assign_approval",
        },
    )

    assert response.status_code == 200
    permission_check = response.json()["permission_check"]
    assert permission_check["allowed"] is True
    assert permission_check["permission"] == "governance.assign_approval"
    assert "operator" in permission_check["roles"]


def test_auth_permission_check_rejects_unknown_permission() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/auth/permissions/check",
        json={
            "actor_id": "command-center-operator",
            "permission": "system.destroy",
        },
    )

    assert response.status_code == 200
    assert response.json()["permission_check"]["allowed"] is False


def test_auth_permission_enforcement_allows_known_permission() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/auth/permissions/enforce",
        json={
            "actor_id": "command-center-operator",
            "permission": "governance.assign_approval",
            "target_type": "artifact",
            "target_id": "artifact-review-target",
            "reason": "Enforce before assigning approval.",
            "evidence": {"source": "test"},
        },
    )

    assert response.status_code == 200
    enforcement = response.json()["permission_enforcement"]
    assert enforcement["allowed"] is True
    assert enforcement["enforcement"] == "granted"
    assert enforcement["target_type"] == "artifact"
    assert enforcement["target_id"] == "artifact-review-target"
    assert enforcement["evidence"]["data_platform"] == "DB MARIAM"


def test_auth_permission_enforcement_blocks_unknown_permission() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/auth/permissions/enforce",
        json={
            "actor_id": "command-center-operator",
            "permission": "system.destroy",
            "target_type": "system",
            "target_id": "core",
            "reason": "Attempt blocked permission.",
            "evidence": {"source": "test"},
        },
    )

    assert response.status_code == 403
    assert "Permission system.destroy denied" in response.json()["detail"]


def test_request_scoped_permission_dependency_blocks_mutating_endpoint() -> None:
    class ReadOnlyAuthService(AuthService):
        def current_session(self) -> UserSession:
            return UserSession(
                session_id="read-only-session",
                user_id="read-only-operator",
                display_name="Read Only Operator",
                roles=["viewer"],
                permissions=["runtime.read"],
            )

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: ReadOnlyAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "This mission should be blocked before creation.",
            "requested_by": "read-only-operator",
        },
    )

    assert response.status_code == 403
    assert "Permission mission.create denied" in response.json()["detail"]


def test_request_scoped_permission_dependency_records_granted_audit_evidence() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/missions",
        headers={"x-mariam-request-id": "audit-granted-request"},
        json={
            "plugin_id": "crm",
            "user_request": "Create a mission that records endpoint authorization evidence.",
            "requested_by": "command-center-operator",
        },
    )

    assert response.status_code == 200
    audit_records = client.get("/api/audit").json()["audit_records"]
    authorization_records = [
        record
        for record in audit_records
        if record["action"] == "authorization.permission_enforced"
        and record["target_type"] == "mission"
        and record["target_id"] == "/api/missions"
    ]
    assert authorization_records
    record = authorization_records[-1]
    assert record["decision"] == "granted"
    assert record["actor_id"] == "command-center-operator"
    assert record["evidence"]["permission"] == "mission.create"
    assert record["evidence"]["method"] == "POST"
    assert record["evidence"]["path"] == "/api/missions"
    assert record["evidence"]["request_id"] == "audit-granted-request"
    assert record["evidence"]["authorization_dependency"] is True
    assert record["evidence"]["data_platform"] == "DB MARIAM"


def test_request_scoped_permission_dependency_records_denied_audit_evidence() -> None:
    class ReadOnlyAuthService(AuthService):
        def current_session(self) -> UserSession:
            return UserSession(
                session_id="read-only-session",
                user_id="read-only-operator",
                display_name="Read Only Operator",
                roles=["viewer"],
                permissions=["runtime.read"],
            )

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: ReadOnlyAuthService()
    client = TestClient(app)

    response = client.post(
        "/api/missions",
        headers={
            "x-mariam-request-id": "audit-denied-request",
            "x-mariam-actor-id": "read-only-operator",
        },
        json={
            "plugin_id": "crm",
            "user_request": "This denied mission should still record authorization evidence.",
            "requested_by": "read-only-operator",
        },
    )

    assert response.status_code == 403
    audit_records = client.get("/api/audit").json()["audit_records"]
    authorization_records = [
        record
        for record in audit_records
        if record["action"] == "authorization.permission_enforced"
        and record["decision"] == "denied"
    ]
    assert authorization_records
    record = authorization_records[-1]
    assert record["actor_id"] == "read-only-operator"
    assert record["target_type"] == "mission"
    assert record["evidence"]["permission"] == "mission.create"
    assert record["evidence"]["request_id"] == "audit-denied-request"
    assert record["evidence"]["authorization_dependency"] is True
    assert "Permission mission.create denied" in record["evidence"]["error"]


def test_auth_human_identity_enforcement_allows_current_session_user() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/auth/human-identity/enforce",
        json={
            "actor_id": "command-center-operator",
            "claimed_user_id": "command-center-operator",
            "target_type": "artifact",
            "target_id": "artifact-review-target",
            "reason": "Verify human operator before governance approval.",
            "evidence": {"source": "test"},
        },
    )

    assert response.status_code == 200
    identity = response.json()["human_identity"]
    assert identity["verified"] is True
    assert identity["enforcement"] == "verified"
    assert identity["display_name"] == "Command Center Operator"
    assert "governance-reviewer" in identity["roles"]
    assert identity["data_platform"] == "DB MARIAM"


def test_auth_human_identity_enforcement_blocks_mismatched_user() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/auth/human-identity/enforce",
        json={
            "actor_id": "command-center-operator",
            "claimed_user_id": "unknown-human",
            "target_type": "artifact",
            "target_id": "artifact-review-target",
            "reason": "Reject mismatched human identity.",
            "evidence": {"source": "test"},
        },
    )

    assert response.status_code == 403
    assert "Human identity unknown-human denied" in response.json()["detail"]


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
    assert response.json()["plugin"]["status"] == "registered"


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
    assert plugin["status"] == "registered"


def test_plugin_can_be_enabled_and_disabled_with_audit() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    validate_response = client.post(
        f"/api/plugins/{plugin_id}/validate",
        json={
            "actor_id": "plugin-governance",
            "reason": "Validate CRM plugin before enable.",
            "evidence": {"review": "validation-passed"},
        },
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["validation_report"]["passed"] is True

    enable_response = client.post(
        f"/api/plugins/{plugin_id}/enable",
        json={
            "actor_id": "plugin-governance",
            "reason": "Enable CRM plugin after manifest review.",
            "evidence": {"review": "passed"},
        },
    )
    assert enable_response.status_code == 200
    assert enable_response.json()["plugin"]["status"] == "enabled"

    impact_response = client.post(
        f"/api/plugins/{plugin_id}/impact-analysis",
        json={
            "actor_id": "plugin-governance",
            "reason": "Analyze plugin impact before disable.",
            "intended_action": "disable",
            "evidence": {"review": "impact-analyzed"},
        },
    )
    assert impact_response.status_code == 200
    assert impact_response.json()["impact_report"]["risk_level"] == "high"

    approval_response = client.post(
        f"/api/plugins/{plugin_id}/approve-change",
        json={
            "actor_id": "plugin-governance",
            "reason": "Approve high-risk plugin disable.",
            "intended_action": "disable",
            "evidence": {"approval": "granted"},
        },
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["approval_report"]["impact_id"] == impact_response.json()["impact_report"]["impact_id"]

    disable_response = client.post(
        f"/api/plugins/{plugin_id}/disable",
        json={
            "actor_id": "plugin-governance",
            "reason": "Disable CRM plugin for maintenance.",
            "evidence": {"maintenance": "scheduled"},
        },
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["plugin"]["status"] == "disabled"

    list_response = client.get("/api/plugins")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    plugin = next(plugin for plugin in list_response.json()["plugins"] if plugin["plugin_id"] == plugin_id)
    assert plugin["status"] == "disabled"
    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] in {"plugin.enable", "plugin.disable"}
    ]
    assert plugin_id in [
        event["payload"].get("plugin_id")
        for event in event_response.json()["events"]
        if event["name"] in {"plugin.enable", "plugin.disable"}
    ]


def test_plugin_disable_requires_impact_analysis() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    validate_and_enable_plugin(client, plugin_id)

    disable_response = client.post(
        f"/api/plugins/{plugin_id}/disable",
        json={
            "actor_id": "plugin-governance",
            "reason": "Attempt disable without impact analysis.",
            "evidence": {"review": "missing-impact-analysis"},
        },
    )

    assert disable_response.status_code == 400
    assert "requires impact analysis" in disable_response.json()["detail"]


def test_high_risk_plugin_disable_requires_change_approval() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    validate_and_enable_plugin(client, plugin_id)
    impact_response = client.post(
        f"/api/plugins/{plugin_id}/impact-analysis",
        json={
            "actor_id": "plugin-governance",
            "reason": "Analyze high-risk plugin disable.",
            "intended_action": "disable",
            "evidence": {"review": "impact-analyzed"},
        },
    )
    assert impact_response.status_code == 200
    assert impact_response.json()["impact_report"]["risk_level"] == "high"

    disable_response = client.post(
        f"/api/plugins/{plugin_id}/disable",
        json={
            "actor_id": "plugin-governance",
            "reason": "Attempt disable without approval.",
            "evidence": {"review": "missing-approval"},
        },
    )

    assert disable_response.status_code == 400
    assert "requires approval" in disable_response.json()["detail"]


def test_plugin_change_approval_records_audit_event_and_stamp() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    impact_response = client.post(
        f"/api/plugins/{plugin_id}/impact-analysis",
        json={
            "actor_id": "plugin-governance",
            "reason": "Analyze before approval.",
            "intended_action": "disable",
            "evidence": {"review": "impact-analyzed"},
        },
    )
    impact_id = impact_response.json()["impact_report"]["impact_id"]

    approval_response = client.post(
        f"/api/plugins/{plugin_id}/approve-change",
        json={
            "actor_id": "plugin-governance",
            "reason": "Approve plugin disable.",
            "intended_action": "disable",
            "evidence": {"approval": "granted"},
        },
    )

    assert approval_response.status_code == 200
    report = approval_response.json()["approval_report"]
    assert report["approval_id"].startswith("plugin-approval-")
    assert report["impact_id"] == impact_id
    assert report["intended_action"] == "disable"

    list_response = client.get("/api/plugins")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")
    plugin = next(plugin for plugin in list_response.json()["plugins"] if plugin["plugin_id"] == plugin_id)

    assert plugin["change_approval"]["approval_id"] == report["approval_id"]
    assert plugin["change_approval"]["impact_id"] == impact_id
    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "plugin.approve_change"
    ]
    assert report["approval_id"] in [
        event["payload"].get("approval_id")
        for event in event_response.json()["events"]
        if event["name"] == "plugin.approve_change"
    ]


def test_plugin_rollback_requires_rollback_point() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    rollback_response = client.post(
        f"/api/plugins/{plugin_id}/rollback",
        json={
            "actor_id": "plugin-governance",
            "reason": "Attempt rollback without lifecycle history.",
            "evidence": {"review": "missing-rollback-point"},
        },
    )

    assert rollback_response.status_code == 400
    assert "has no rollback point" in rollback_response.json()["detail"]


def test_plugin_state_change_can_be_rolled_back_with_audit() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    validate_and_enable_plugin(client, plugin_id)

    rollback_response = client.post(
        f"/api/plugins/{plugin_id}/rollback",
        json={
            "actor_id": "plugin-governance",
            "reason": "Rollback enabled plugin to previous registered state.",
            "evidence": {"review": "rollback-approved"},
        },
    )

    assert rollback_response.status_code == 200
    plugin = rollback_response.json()["plugin"]
    assert plugin["status"] == "registered"
    assert plugin["rollback_stack"] == []

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "plugin.rollback"
    ]
    assert plugin_id in [
        event["payload"].get("plugin_id")
        for event in event_response.json()["events"]
        if event["name"] == "plugin.rollback"
    ]


def test_plugin_soft_delete_requires_impact_analysis() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    delete_response = client.post(
        f"/api/plugins/{plugin_id}/delete",
        json={
            "actor_id": "plugin-governance",
            "reason": "Attempt soft delete without impact analysis.",
            "evidence": {"review": "missing-impact-analysis"},
        },
    )

    assert delete_response.status_code == 400
    assert "requires impact analysis" in delete_response.json()["detail"]


def test_high_risk_plugin_soft_delete_requires_change_approval() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    validate_and_enable_plugin(client, plugin_id)
    impact_response = client.post(
        f"/api/plugins/{plugin_id}/impact-analysis",
        json={
            "actor_id": "plugin-governance",
            "reason": "Analyze high-risk plugin delete.",
            "intended_action": "delete",
            "evidence": {"review": "impact-analyzed"},
        },
    )
    assert impact_response.status_code == 200
    assert impact_response.json()["impact_report"]["risk_level"] == "high"

    delete_response = client.post(
        f"/api/plugins/{plugin_id}/delete",
        json={
            "actor_id": "plugin-governance",
            "reason": "Attempt high-risk soft delete without approval.",
            "evidence": {"review": "missing-approval"},
        },
    )

    assert delete_response.status_code == 400
    assert "requires approval" in delete_response.json()["detail"]


def test_plugin_can_be_soft_deleted_and_restored_with_audit() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    validate_and_enable_plugin(client, plugin_id)
    impact_response = client.post(
        f"/api/plugins/{plugin_id}/impact-analysis",
        json={
            "actor_id": "plugin-governance",
            "reason": "Analyze before soft delete.",
            "intended_action": "delete",
            "evidence": {"review": "impact-analyzed"},
        },
    )
    impact_id = impact_response.json()["impact_report"]["impact_id"]
    approval_response = client.post(
        f"/api/plugins/{plugin_id}/approve-change",
        json={
            "actor_id": "plugin-governance",
            "reason": "Approve high-risk soft delete.",
            "intended_action": "delete",
            "evidence": {"approval": "granted"},
        },
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["approval_report"]["impact_id"] == impact_id

    delete_response = client.post(
        f"/api/plugins/{plugin_id}/delete",
        json={
            "actor_id": "plugin-governance",
            "reason": "Soft delete plugin while retaining audit history.",
            "evidence": {"review": "approved-delete"},
        },
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["plugin"]["status"] == "deleted"

    restore_response = client.post(
        f"/api/plugins/{plugin_id}/restore",
        json={
            "actor_id": "plugin-governance",
            "reason": "Restore plugin for disabled review state.",
            "evidence": {"review": "restore-approved"},
        },
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["plugin"]["status"] == "disabled"

    list_response = client.get("/api/plugins")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")
    plugin = next(plugin for plugin in list_response.json()["plugins"] if plugin["plugin_id"] == plugin_id)

    assert plugin["status"] == "disabled"
    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] in {"plugin.soft_delete", "plugin.restore"}
    ]
    assert plugin_id in [
        event["payload"].get("plugin_id")
        for event in event_response.json()["events"]
        if event["name"] in {"plugin.soft_delete", "plugin.restore"}
    ]


def test_plugin_impact_analysis_records_audit_event_and_stamp() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    impact_response = client.post(
        f"/api/plugins/{plugin_id}/impact-analysis",
        json={
            "actor_id": "plugin-governance",
            "reason": "Analyze plugin disable impact.",
            "intended_action": "disable",
            "evidence": {"review": "pre-disable"},
        },
    )

    assert impact_response.status_code == 200
    report = impact_response.json()["impact_report"]
    assert report["impact_id"].startswith("plugin-impact-")
    assert report["intended_action"] == "disable"
    assert "lead-intake" in report["affected_workflows"]
    assert "crm.read" in report["affected_permissions"]
    assert "event_bus" in report["affected_dependencies"]

    list_response = client.get("/api/plugins")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")
    plugin = next(plugin for plugin in list_response.json()["plugins"] if plugin["plugin_id"] == plugin_id)

    assert plugin["impact_analysis"]["impact_id"] == report["impact_id"]
    assert plugin["impact_analysis"]["intended_action"] == "disable"
    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "plugin.impact_analysis"
    ]
    assert report["impact_id"] in [
        event["payload"].get("impact_id")
        for event in event_response.json()["events"]
        if event["name"] == "plugin.impact_analysis"
    ]


def test_plugin_enable_requires_successful_validation() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    enable_response = client.post(
        f"/api/plugins/{plugin_id}/enable",
        json={
            "actor_id": "plugin-governance",
            "reason": "Attempt enable without plugin validation.",
            "evidence": {"review": "missing-validation"},
        },
    )

    assert enable_response.status_code == 400
    assert "must pass validation" in enable_response.json()["detail"]


def test_plugin_can_be_patched_with_audit_and_revalidation_required() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    client.post(
        f"/api/plugins/{plugin_id}/validate",
        json={
            "actor_id": "plugin-governance",
            "reason": "Validate before patch.",
            "evidence": {"review": "passed"},
        },
    )

    patch_response = client.patch(
        f"/api/plugins/{plugin_id}",
        json={
            "actor_id": "plugin-governance",
            "reason": "Upgrade CRM plugin manifest.",
            "version": "0.2.0",
            "permissions": ["crm.read", "crm.write", "crm.approve", "crm.export"],
            "workflows": ["lead-intake", "pipeline-review", "client-follow-up", "crm-export"],
            "tests": ["api", "runtime", "permissions", "data-boundary", "upgrade"],
            "acceptance_criteria": [
                "registers successfully",
                "declares data boundary",
                "requires revalidation after upgrade",
            ],
            "evidence": {"upgrade": "minor-version"},
        },
    )

    assert patch_response.status_code == 200
    plugin = patch_response.json()["plugin"]
    assert plugin["version"] == "0.2.0"
    assert "crm.export" in plugin["permissions"]
    assert "crm-export" in plugin["workflows"]
    assert plugin["validation"] == {}
    assert len(plugin["rollback_stack"]) == 1

    enable_response = client.post(
        f"/api/plugins/{plugin_id}/enable",
        json={
            "actor_id": "plugin-governance",
            "reason": "Attempt enable after patch without revalidation.",
            "evidence": {"review": "missing-revalidation"},
        },
    )
    assert enable_response.status_code == 400
    assert "must pass validation" in enable_response.json()["detail"]

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "plugin.patch"
    ]
    assert plugin_id in [
        event["payload"].get("plugin_id")
        for event in event_response.json()["events"]
        if event["name"] == "plugin.patch"
    ]


def test_plugin_patch_can_be_rolled_back_to_previous_manifest() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    patch_response = client.patch(
        f"/api/plugins/{plugin_id}",
        json={
            "actor_id": "plugin-governance",
            "reason": "Patch before rollback.",
            "version": "0.2.0",
            "workflows": ["lead-intake", "pipeline-review", "client-follow-up", "crm-export"],
            "evidence": {"upgrade": "rollback-test"},
        },
    )
    assert patch_response.status_code == 200

    rollback_response = client.post(
        f"/api/plugins/{plugin_id}/rollback",
        json={
            "actor_id": "plugin-governance",
            "reason": "Rollback failed plugin upgrade.",
            "evidence": {"review": "rollback-approved"},
        },
    )

    assert rollback_response.status_code == 200
    plugin = rollback_response.json()["plugin"]
    assert plugin["version"] == "0.1.0"
    assert "crm-export" not in plugin["workflows"]
    assert plugin["rollback_stack"] == []


def test_plugin_can_be_exported_as_dna_with_audit() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    client.patch(
        f"/api/plugins/{plugin_id}",
        json={
            "actor_id": "plugin-governance",
            "reason": "Prepare plugin DNA export.",
            "version": "0.2.0",
            "workflows": ["lead-intake", "pipeline-review", "client-follow-up", "crm-export"],
            "evidence": {"review": "export-ready"},
        },
    )

    export_response = client.post(
        f"/api/plugins/{plugin_id}/export-dna",
        json={
            "actor_id": "plugin-governance",
            "reason": "Export CRM plugin as DNA.",
            "evidence": {"export": "approved"},
        },
    )

    assert export_response.status_code == 200
    dna_package = export_response.json()["dna_package"]
    assert dna_package["dna_package_id"].startswith("plugin-dna-")
    assert dna_package["payload"]["schema"] == "mariam.plugin.dna.v1"
    assert dna_package["payload"]["plugin"]["plugin_id"] == plugin_id
    assert dna_package["payload"]["plugin"]["version"] == "0.2.0"
    assert "rollback_stack" not in dna_package["payload"]["plugin"]
    assert "validation" not in dna_package["payload"]["plugin"]
    assert "impact_analysis" not in dna_package["payload"]["plugin"]
    assert "change_approval" not in dna_package["payload"]["plugin"]

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "plugin.export_dna"
    ]
    assert dna_package["dna_package_id"] in [
        event["payload"].get("dna_package_id")
        for event in event_response.json()["events"]
        if event["name"] == "plugin.export_dna"
    ]


def test_plugin_dna_can_be_imported_as_disabled_plugin_for_review() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    dna_package = client.post(
        f"/api/plugins/{plugin_id}/export-dna",
        json={
            "actor_id": "plugin-governance",
            "reason": "Export before import test.",
            "evidence": {"export": "approved"},
        },
    ).json()["dna_package"]

    import_response = client.post(
        "/api/plugins/import-dna",
        json={
            "actor_id": "plugin-governance",
            "reason": "Import CRM plugin DNA for review.",
            "dna_package": dna_package,
            "evidence": {"import": "review-required"},
        },
    )

    assert import_response.status_code == 200
    imported = import_response.json()["plugin"]
    assert imported["plugin_id"] == "crm-imported"
    assert imported["name"] == "CRM Workspace Imported"
    assert imported["status"] == "disabled"
    assert imported["validation"] == {}

    enable_response = client.post(
        f"/api/plugins/{imported['plugin_id']}/enable",
        json={
            "actor_id": "plugin-governance",
            "reason": "Attempt enable imported plugin without validation.",
            "evidence": {"review": "missing-validation"},
        },
    )
    assert enable_response.status_code == 400
    assert "must pass validation" in enable_response.json()["detail"]

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert imported["plugin_id"] in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "plugin.import_dna"
    ]
    assert imported["plugin_id"] in [
        event["payload"].get("plugin_id")
        for event in event_response.json()["events"]
        if event["name"] == "plugin.import_dna"
    ]


def test_plugin_timeline_reads_plugin_audit_and_events() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    client.post(
        f"/api/plugins/{plugin_id}/validate",
        json={
            "actor_id": "plugin-governance",
            "reason": "Validate before timeline review.",
            "evidence": {"review": "passed"},
        },
    )
    client.post(
        f"/api/plugins/{plugin_id}/export-dna",
        json={
            "actor_id": "plugin-governance",
            "reason": "Export before timeline review.",
            "evidence": {"export": "approved"},
        },
    )

    timeline_response = client.get(f"/api/plugins/{plugin_id}/timeline")

    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert timeline["plugin"]["plugin_id"] == plugin_id
    assert timeline["summary"]["audit_records"] >= 3
    assert timeline["summary"]["events"] >= 3
    assert {"plugin.register", "plugin.validate", "plugin.export_dna"} <= {
        record["action"] for record in timeline["audit_records"]
    }
    assert {"plugin.registered", "plugin.validate", "plugin.export_dna"} <= {
        event["name"] for event in timeline["events"]
    }


def test_plugin_settings_can_be_read_and_updated_with_audit() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    settings_response = client.get(f"/api/plugins/{plugin_id}/settings")
    assert settings_response.status_code == 200
    assert settings_response.json()["settings_values"] == {}
    assert "pipelineStages" in settings_response.json()["settings_schema"]["properties"]

    update_response = client.patch(
        f"/api/plugins/{plugin_id}/settings",
        json={
            "actor_id": "plugin-governance",
            "reason": "Configure CRM pipeline stages.",
            "settings": {"pipelineStages": ["new", "qualified", "proposal", "won"]},
            "evidence": {"review": "settings-approved"},
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["settings_values"]["pipelineStages"] == [
        "new",
        "qualified",
        "proposal",
        "won",
    ]
    assert update_response.json()["data_platform"] == "DB MARIAM"

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "plugin.settings_update"
    ]
    assert plugin_id in [
        event["payload"].get("plugin_id")
        for event in event_response.json()["events"]
        if event["name"] == "plugin.settings_update"
    ]


def test_plugin_settings_reject_unknown_schema_keys() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    update_response = client.patch(
        f"/api/plugins/{plugin_id}/settings",
        json={
            "actor_id": "plugin-governance",
            "reason": "Attempt invalid settings update.",
            "settings": {"unknownSetting": True},
            "evidence": {"review": "invalid-key"},
        },
    )

    assert update_response.status_code == 400
    assert "unknown keys" in update_response.json()["detail"]


def test_plugin_dashboard_returns_runtime_view_model() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    client.patch(
        f"/api/plugins/{plugin_id}/settings",
        json={
            "actor_id": "plugin-governance",
            "reason": "Configure before dashboard review.",
            "settings": {"pipelineStages": ["new", "qualified", "proposal", "won"]},
            "evidence": {"review": "settings-approved"},
        },
    )
    client.post(
        f"/api/plugins/{plugin_id}/validate",
        json={
            "actor_id": "plugin-governance",
            "reason": "Validate before dashboard review.",
            "evidence": {"review": "passed"},
        },
    )

    dashboard_response = client.get(f"/api/plugins/{plugin_id}/dashboard")

    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["plugin_id"] == plugin_id
    assert dashboard["dashboard_route"] == "/plugins/crm"
    assert dashboard["data_boundary"] == "private-plugin-tables"
    assert dashboard["chief_agent_role"] == "CRM Chief Agent"
    assert dashboard["settings_values"]["pipelineStages"] == ["new", "qualified", "proposal", "won"]
    assert dashboard["lifecycle"]["validation_passed"] is True
    assert dashboard["activity"]["audit_records"] >= 3
    assert dashboard["data_platform"] == "DB MARIAM"


def test_plugin_workspace_returns_dashboard_settings_chief_swarm_and_data_boundary() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    workspace_response = client.get(f"/api/plugins/{plugin_id}/workspace")

    assert workspace_response.status_code == 200
    workspace = workspace_response.json()
    assert workspace["title"] == "CRM Workspace"
    assert workspace["dashboard"]["dashboard_route"] == "/plugins/crm"
    assert workspace["settings"]["plugin_id"] == plugin_id
    assert workspace["chief_agent"]["role"] == "CRM Chief Agent"
    assert "Lead Qualifier" in [agent["role"] for agent in workspace["swarm"]]
    assert workspace["data_boundary"]["platform"] == "DB MARIAM"
    assert f"{plugin_id}_settings" in workspace["data_boundary"]["private_tables"]
    assert len(workspace["workspace_actions"]) == 4
    assert workspace["data_platform"] == "DB MARIAM"


def test_plugin_chat_request_creates_governed_mission() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    chat_response = client.post(
        f"/api/plugins/{plugin_id}/chat",
        json={
            "requested_by": "command-center-user",
            "user_request": "Prepare a follow-up plan for the Acme lead.",
            "evidence": {"source": "plugin-chat"},
        },
    )

    assert chat_response.status_code == 200
    body = chat_response.json()
    assert body["chat"]["plugin_id"] == plugin_id
    assert body["chat"]["chief_agent_role"] == "CRM Chief Agent"
    assert body["chat"]["status"] == "awaiting_approval"
    assert body["chat"]["data_platform"] == "DB MARIAM"
    mission_id = body["chat"]["mission_id"]

    mission_response = client.get("/api/missions")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert mission_id in [mission["mission_id"] for mission in mission_response.json()["missions"]]
    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "plugin.chat_request"
    ]
    assert mission_id in [
        event["payload"].get("mission_id")
        for event in event_response.json()["events"]
        if event["name"] in {"mission.created", "plugin.chat_request"}
    ]


def test_plugin_chat_rejects_deleted_plugin() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]
    impact_response = client.post(
        f"/api/plugins/{plugin_id}/impact-analysis",
        json={
            "actor_id": "plugin-governance",
            "reason": "Analyze before chat delete rejection.",
            "intended_action": "delete",
            "evidence": {"review": "impact-analyzed"},
        },
    )
    if impact_response.json()["impact_report"]["risk_level"] == "high":
        client.post(
            f"/api/plugins/{plugin_id}/approve-change",
            json={
                "actor_id": "plugin-governance",
                "reason": "Approve delete before chat rejection.",
                "intended_action": "delete",
                "evidence": {"approval": "granted"},
            },
        )
    client.post(
        f"/api/plugins/{plugin_id}/delete",
        json={
            "actor_id": "plugin-governance",
            "reason": "Soft delete before chat rejection.",
            "evidence": {"review": "approved-delete"},
        },
    )

    chat_response = client.post(
        f"/api/plugins/{plugin_id}/chat",
        json={
            "requested_by": "command-center-user",
            "user_request": "Prepare a follow-up plan.",
            "evidence": {"source": "plugin-chat"},
        },
    )

    assert chat_response.status_code == 400
    assert "must be restored" in chat_response.json()["detail"]


def test_artifact_can_be_generated_from_mission_and_approved() -> None:
    client = TestClient(create_app())
    mission_response = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Prepare a proposal follow-up artifact.",
            "requested_by": "command-center-user",
        },
    )
    mission_id = mission_response.json()["mission"]["mission_id"]

    artifact_response = client.post(f"/api/artifacts/from-mission/{mission_id}")

    assert artifact_response.status_code == 200
    artifact = artifact_response.json()["artifact"]
    assert artifact["mission_id"] == mission_id
    assert artifact["plugin_id"] == "crm"
    assert artifact["status"] == "awaiting_approval"
    assert artifact["data_platform"] == "DB MARIAM"

    approve_response = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/approve",
        json={
            "approved_by": "artifact-governance",
            "evidence": {"review": "artifact-approved"},
        },
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["artifact"]["status"] == "approved"

    list_response = client.get("/api/artifacts")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert artifact["artifact_id"] in [
        item["artifact_id"] for item in list_response.json()["artifacts"]
    ]
    assert artifact["artifact_id"] in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "artifact.approve"
    ]
    assert artifact["artifact_id"] in [
        event["payload"].get("artifact_id")
        for event in event_response.json()["events"]
        if event["name"] in {"artifact.generated", "artifact.approved"}
    ]


def test_artifact_delivery_requires_approval() -> None:
    client = TestClient(create_app())
    mission_id = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Prepare an artifact before delivery gate.",
            "requested_by": "command-center-user",
        },
    ).json()["mission"]["mission_id"]
    artifact = client.post(f"/api/artifacts/from-mission/{mission_id}").json()["artifact"]

    delivery_response = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/package-delivery",
        json={
            "packaged_by": "delivery-governance",
            "destination": "client-review-channel",
            "evidence": {"review": "premature-delivery"},
        },
    )

    assert delivery_response.status_code == 400
    assert "must be approved" in delivery_response.json()["detail"]


def test_approved_artifact_can_be_packaged_for_delivery() -> None:
    client = TestClient(create_app())
    mission_id = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Prepare a delivery-ready artifact.",
            "requested_by": "command-center-user",
        },
    ).json()["mission"]["mission_id"]
    artifact = client.post(f"/api/artifacts/from-mission/{mission_id}").json()["artifact"]
    client.post(
        f"/api/artifacts/{artifact['artifact_id']}/approve",
        json={
            "approved_by": "artifact-governance",
            "evidence": {"review": "artifact-approved"},
        },
    )

    premature_delivery_response = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/package-delivery",
        json={
            "packaged_by": "delivery-governance",
            "destination": "client-review-channel",
            "evidence": {"delivery": "missing-quality-review"},
        },
    )
    assert premature_delivery_response.status_code == 400
    assert "must pass quality review" in premature_delivery_response.json()["detail"]

    quality_response = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/quality-review",
        json={
            "reviewed_by": "quality-governance",
            "evidence": {"quality": "passed"},
        },
    )
    assert quality_response.status_code == 200
    assert quality_response.json()["quality_review"]["passed"] is True

    delivery_response = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/package-delivery",
        json={
            "packaged_by": "delivery-governance",
            "destination": "client-review-channel",
            "evidence": {"delivery": "approved"},
        },
    )

    assert delivery_response.status_code == 200
    delivery_package = delivery_response.json()["delivery_package"]
    assert delivery_package["artifact_id"] == artifact["artifact_id"]
    assert delivery_package["mission_id"] == mission_id
    assert delivery_package["status"] == "ready_for_client_delivery"
    assert delivery_package["data_platform"] == "DB MARIAM"
    assert delivery_package["package_manifest"]["quality_score"] == 100
    assert delivery_package["package_manifest"]["evidence_signed"] is True
    assert delivery_package["package_manifest"]["evidence_signature_algorithm"] == "sha256"
    assert len(delivery_package["package_manifest"]["evidence_signature"]) == 64
    assert delivery_package["package_manifest"]["evidence_bundle"]["quality_review_id"] == (
        quality_response.json()["quality_review"]["review_id"]
    )

    quality_list_response = client.get("/api/artifacts/quality-reviews")
    delivery_list_response = client.get("/api/artifacts/deliveries")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert quality_response.json()["quality_review"]["review_id"] in [
        item["review_id"] for item in quality_list_response.json()["quality_reviews"]
    ]
    assert delivery_package["delivery_id"] in [
        item["delivery_id"] for item in delivery_list_response.json()["delivery_packages"]
    ]
    assert artifact["artifact_id"] in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "artifact.package_delivery"
    ]
    assert delivery_package["delivery_id"] in [
        event["payload"].get("delivery_id")
        for event in event_response.json()["events"]
        if event["name"] == "artifact.delivery_packaged"
    ]


def test_delivery_package_can_be_confirmed_to_client_with_audit() -> None:
    client = TestClient(create_app())
    mission_id = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Prepare a package that can be delivered to the client.",
            "requested_by": "command-center-user",
        },
    ).json()["mission"]["mission_id"]
    artifact = client.post(f"/api/artifacts/from-mission/{mission_id}").json()["artifact"]
    client.post(
        f"/api/artifacts/{artifact['artifact_id']}/approve",
        json={
            "approved_by": "artifact-governance",
            "evidence": {"review": "artifact-approved"},
        },
    )
    client.post(
        f"/api/artifacts/{artifact['artifact_id']}/quality-review",
        json={
            "reviewed_by": "quality-governance",
            "evidence": {"quality": "passed"},
        },
    )
    delivery_package = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/package-delivery",
        json={
            "packaged_by": "delivery-governance",
            "destination": "client-review-channel",
            "evidence": {"delivery": "approved"},
        },
    ).json()["delivery_package"]

    confirm_response = client.post(
        f"/api/artifacts/deliveries/{delivery_package['delivery_id']}/confirm",
        json={
            "delivered_by": "delivery-governance",
            "client_reference": "client-confirmation-001",
            "evidence": {"client_receipt": "confirmed"},
        },
    )

    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()["delivery_package"]
    assert confirmed["delivery_id"] == delivery_package["delivery_id"]
    assert confirmed["status"] == "delivered_to_client"
    assert confirmed["package_manifest"]["client_reference"] == "client-confirmation-001"
    assert confirmed["package_manifest"]["delivery_confirmed"] is True
    assert confirmed["package_manifest"]["delivery_confirmation_requires_signature"] is True
    assert confirmed["package_manifest"]["evidence_signed"] is True
    assert len(confirmed["package_manifest"]["evidence_signature"]) == 64

    list_response = client.get("/api/artifacts/deliveries")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    listed = next(
        item
        for item in list_response.json()["delivery_packages"]
        if item["delivery_id"] == confirmed["delivery_id"]
    )
    assert listed["status"] == "delivered_to_client"
    assert confirmed["delivery_id"] in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "artifact.confirm_delivery"
    ]
    confirm_record = next(
        record
        for record in audit_response.json()["audit_records"]
        if record["action"] == "artifact.confirm_delivery"
        and record["target_id"] == confirmed["delivery_id"]
    )
    assert confirm_record["evidence"]["evidence_signature"] == confirmed["package_manifest"]["evidence_signature"]
    assert confirmed["delivery_id"] in [
        event["payload"].get("delivery_id")
        for event in event_response.json()["events"]
        if event["name"] == "artifact.delivery_confirmed"
    ]
    evidence_report_response = client.get("/api/runtime/delivery-evidence-report")
    assert evidence_report_response.status_code == 200
    evidence_report = evidence_report_response.json()
    assert evidence_report["title"] == "Mariam Delivery Evidence Bundle Verification Report"
    assert evidence_report["status"] == "ready"
    assert evidence_report["data_platform"] == "DB MARIAM"
    assert evidence_report["sla_minutes"] == 240
    assert evidence_report["escalation_after_minutes"] == 480
    assert evidence_report["sla_status"] in {"ready", "escalation_required"}
    assert evidence_report["signed_bundle_count"] >= 1
    assert evidence_report["confirmed_delivery_count"] >= 1
    assert evidence_report["invalid_signature_count"] == 0
    evidence_item = next(
        item for item in evidence_report["evidence_items"]
        if item["delivery_id"] == confirmed["delivery_id"]
    )
    assert evidence_item["signature_valid"] is True
    assert evidence_item["delivery_confirmed"] is True
    assert evidence_item["client_reference"] == "client-confirmation-001"
    assert evidence_item["sla_state"] == "confirmed"
    assert evidence_item["escalation_required"] is False
    sla_item = next(
        item for item in evidence_report["sla_items"]
        if item["delivery_id"] == confirmed["delivery_id"]
    )
    assert sla_item["signature_valid"] is True
    assert sla_item["delivery_confirmed"] is True
    assert sla_item["sla_state"] == "confirmed"
    assert sla_item["governance_action"] == "confirm_traceability_complete"
    assert evidence_report["sla_drilldown_summary"]["title"] == "Signed Delivery SLA Drill-down"
    assert evidence_report["sla_drilldown_summary"]["signed_item_count"] >= 1
    assert evidence_report["sla_drilldown_summary"]["reviewer_queue_counts"]["delivery-evidence"] >= 1
    assert "confirmed" in evidence_report["sla_filters"]["sla_state_options"]
    assert "delivery-evidence" in evidence_report["sla_filters"]["reviewer_queue_options"]
    assert evidence_report["sla_filters"]["default_sla_state"] == "all"
    assert evidence_report["sla_filters"]["default_reviewer_queue"] == "all"
    assert evidence_report["filtered_sla_drilldown_items"]
    assert "signed_delivery_sla_filters_ready" in [
        check["name"] for check in evidence_report["checks"]
    ]
    export_response = client.post("/api/runtime/delivery-evidence-report/export")
    assert export_response.status_code == 200
    export_package = export_response.json()["export_package"]
    assert export_package["export_id"].startswith("delivery-governance-evidence-export-")
    assert export_package["status"] == "ready_for_review"
    assert export_package["data_platform"] == "DB MARIAM"
    assert export_package["package_manifest"]["delivery_count"] >= 1
    assert export_package["package_manifest"]["signed_bundle_count"] >= 1
    assert export_package["package_manifest"]["confirmed_delivery_count"] >= 1
    assert export_package["package_manifest"]["invalid_signature_count"] == 0
    assert export_package["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert export_package["delivery_evidence_report"]["data_platform"] == "DB MARIAM"
    drilldown_item = next(
        item for item in evidence_report["sla_drilldown_items"]
        if item["delivery_id"] == confirmed["delivery_id"]
    )
    assert drilldown_item["sla_state"] == "confirmed"
    assert drilldown_item["reviewer_queue"] == "delivery-evidence"

    second_confirm_response = client.post(
        f"/api/artifacts/deliveries/{delivery_package['delivery_id']}/confirm",
        json={
            "delivered_by": "delivery-governance",
            "client_reference": "client-confirmation-002",
            "evidence": {"client_receipt": "duplicate"},
        },
    )

    assert second_confirm_response.status_code == 400
    assert "must be ready_for_client_delivery" in second_confirm_response.json()["detail"]


def test_artifact_can_be_rejected_with_governance_reason() -> None:
    client = TestClient(create_app())
    mission_id = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Prepare an incomplete artifact.",
            "requested_by": "command-center-user",
        },
    ).json()["mission"]["mission_id"]
    artifact = client.post(f"/api/artifacts/from-mission/{mission_id}").json()["artifact"]

    reject_response = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/reject",
        json={
            "rejected_by": "artifact-governance",
            "reason": "Artifact needs stronger evidence before delivery.",
            "evidence": {"review": "changes-requested"},
        },
    )

    assert reject_response.status_code == 200
    assert reject_response.json()["artifact"]["status"] == "rejected"

    audit_response = client.get("/api/audit")
    assert artifact["artifact_id"] in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "artifact.reject" and record["decision"] == "rejected"
    ]


def test_governance_approval_assignment_records_audit_and_event() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/audit/approval-assignments",
        json={
            "assigned_by": "governance-lead",
            "assignee_id": "quality-reviewer-01",
            "target_type": "artifact",
            "target_id": "artifact-review-target-01",
            "approval_role": "quality-reviewer",
            "reason": "Assign quality review before client delivery.",
            "evidence": {"assignment_source": "test"},
        },
    )

    assert response.status_code == 200
    audit_record = response.json()["audit_record"]
    assert audit_record["action"] == "governance.assign_approval"
    assert audit_record["decision"] == "assigned"
    assert audit_record["evidence"]["assignee_id"] == "quality-reviewer-01"
    assert audit_record["evidence"]["approval_role"] == "quality-reviewer"
    assert audit_record["data_platform"] == "DB MARIAM"
    history_response = client.get("/api/audit/governance-assignment-history")
    assert history_response.status_code == 200
    history = history_response.json()["history_report"]
    assert history["title"] == "Governance Reviewer Queue Assignment History"
    assert history["status"] == "ready"
    assert history["assignment_count"] >= 1
    assignment = next(
        item for item in history["assignments"] if item["target_id"] == "artifact-review-target-01"
    )
    assert assignment["audit_id"] == audit_record["audit_id"]
    assert assignment["reviewer_id"] == "quality-reviewer-01"
    assert assignment["reviewer_queue"] == "quality-reviewer"
    assert assignment["data_platform"] == "DB MARIAM"

    events_response = client.get("/api/runtime/events")
    assert "artifact-review-target-01" in [
        event["payload"].get("target_id")
        for event in events_response.json()["events"]
        if event["name"] == "governance.approval_assigned"
    ]


def test_governance_reviewer_decision_outcome_persists_lifecycle_history() -> None:
    client = TestClient(create_app())

    assignment_response = client.post(
        "/api/audit/approval-assignments",
        json={
            "assigned_by": "governance-lead",
            "assignee_id": "quality-reviewer-decision",
            "target_type": "artifact",
            "target_id": "artifact-decision-target-01",
            "approval_role": "quality-reviewer",
            "reason": "Assign review before recording decision.",
            "evidence": {"assignment_source": "decision-test"},
        },
    )
    assignment_audit = assignment_response.json()["audit_record"]
    history_before = client.get("/api/audit/governance-assignment-history").json()["history_report"]
    assignment = next(
        item for item in history_before["assignments"] if item["audit_id"] == assignment_audit["audit_id"]
    )

    decision_response = client.post(
        "/api/audit/reviewer-decisions",
        json={
            "decided_by": "quality-reviewer-decision",
            "reviewer_id": "quality-reviewer-decision",
            "target_type": "artifact",
            "target_id": "artifact-decision-target-01",
            "assignment_id": assignment["assignment_id"],
            "decision": "approved",
            "reason": "Artifact evidence is ready for delivery.",
            "evidence": {"checklist": "complete"},
        },
    )

    assert decision_response.status_code == 200
    audit_record = decision_response.json()["audit_record"]
    assert audit_record["action"] == "governance.record_reviewer_decision"
    assert audit_record["decision"] == "approved"
    assert audit_record["evidence"]["assignment_id"] == assignment["assignment_id"]
    assert audit_record["data_platform"] == "DB MARIAM"

    history = client.get("/api/audit/governance-assignment-history").json()["history_report"]
    assert history["decision_count"] >= 1
    decision = next(
        item for item in history["decisions"] if item["target_id"] == "artifact-decision-target-01"
    )
    assert decision["audit_id"] == audit_record["audit_id"]
    assert decision["assignment_id"] == assignment["assignment_id"]
    assert decision["reviewer_id"] == "quality-reviewer-decision"
    assert decision["decision"] == "approved"
    assert decision["evidence"]["checklist"] == "complete"
    assert decision["data_platform"] == "DB MARIAM"

    workload = client.get("/api/audit/reviewer-workload").json()["workload_report"]
    reviewer = next(
        item for item in workload["items"] if item["reviewer_id"] == "quality-reviewer-decision"
    )
    assert reviewer["decision_count"] >= 1
    assert reviewer["status"] == "ready"

    sla = client.get("/api/audit/governance-sla").json()["sla_report"]
    sla_item = next(item for item in sla["items"] if item["target_id"] == "artifact-decision-target-01")
    assert sla_item["status"] == "decided"
    assert sla_item["escalation_required"] is False

    events_response = client.get("/api/runtime/events")
    assert "artifact-decision-target-01" in [
        event["payload"].get("target_id")
        for event in events_response.json()["events"]
        if event["name"] == "governance.reviewer_decision_recorded"
    ]


def test_governance_decision_evidence_can_be_exported_for_review() -> None:
    client = TestClient(create_app())
    assignment_response = client.post(
        "/api/audit/approval-assignments",
        json={
            "assigned_by": "governance-lead",
            "assignee_id": "quality-reviewer-export",
            "target_type": "artifact",
            "target_id": "artifact-export-review",
            "approval_role": "quality-reviewer",
            "reason": "Assign reviewer before exporting decision evidence.",
        },
    )
    assignment_audit = assignment_response.json()["audit_record"]
    history_before = client.get("/api/audit/governance-assignment-history").json()["history_report"]
    assignment = next(
        item for item in history_before["assignments"] if item["audit_id"] == assignment_audit["audit_id"]
    )
    client.post(
        "/api/audit/reviewer-decisions",
        json={
            "decided_by": "quality-reviewer-export",
            "reviewer_id": "quality-reviewer-export",
            "target_type": "artifact",
            "target_id": "artifact-export-review",
            "assignment_id": assignment["assignment_id"],
            "decision": "approved",
            "reason": "Exportable reviewer decision evidence is complete.",
            "evidence": {"verification": "governance-decision-export"},
        },
    )

    response = client.post("/api/audit/governance-decision-evidence/export")

    assert response.status_code == 200
    export_package = response.json()["export_package"]
    assert export_package["export_id"].startswith("governance-decision-evidence-export-")
    assert export_package["title"] == "Mariam Governance Reviewer Decision Evidence Export"
    assert export_package["status"] == "ready_for_review"
    assert export_package["format"] == "json"
    assert export_package["data_platform"] == "DB MARIAM"
    assert export_package["package_manifest"]["decision_count"] >= 1
    assert export_package["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert "quality-reviewer-export" in export_package["package_manifest"]["reviewer_ids"]
    assert "approved" in export_package["package_manifest"]["decision_outcomes"]
    assert export_package["history_report"]["decision_count"] >= 1


def test_governance_notification_routing_records_audit_and_event() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/audit/notifications/route",
        json={
            "routed_by": "governance-router",
            "recipient_id": "quality-reviewer-01",
            "channel": "command-center",
            "subject": "Artifact review assigned",
            "message": "Please review the assigned artifact before client delivery.",
            "target_type": "artifact",
            "target_id": "artifact-notification-target-01",
            "evidence": {"notification_source": "test"},
        },
    )

    assert response.status_code == 200
    audit_record = response.json()["audit_record"]
    assert audit_record["action"] == "governance.route_notification"
    assert audit_record["decision"] == "routed"
    assert audit_record["evidence"]["recipient_id"] == "quality-reviewer-01"
    assert audit_record["evidence"]["channel"] == "command-center"
    assert audit_record["evidence"]["subject"] == "Artifact review assigned"
    assert audit_record["data_platform"] == "DB MARIAM"

    events_response = client.get("/api/runtime/events")
    assert "artifact-notification-target-01" in [
        event["payload"].get("target_id")
        for event in events_response.json()["events"]
        if event["name"] == "governance.notification_routed"
    ]


def test_governance_assignment_and_notification_evidence_can_be_exported() -> None:
    client = TestClient(create_app())

    assignment_response = client.post(
        "/api/audit/approval-assignments",
        json={
            "assigned_by": "governance-lead",
            "assignee_id": "quality-reviewer-export-02",
            "target_type": "artifact",
            "target_id": "artifact-export-target-01",
            "approval_role": "quality-reviewer",
            "reason": "Verify assignment export evidence.",
            "evidence": {"assignment_source": "export-test"},
        },
    )
    notification_response = client.post(
        "/api/audit/notifications/route",
        json={
            "routed_by": "governance-router",
            "recipient_id": "quality-reviewer-export-02",
            "channel": "command-center",
            "subject": "Review artifact export target",
            "message": "Please review artifact export target before delivery.",
            "target_type": "artifact",
            "target_id": "artifact-export-target-01",
            "evidence": {"notification_source": "export-test"},
        },
    )
    assignment_audit = assignment_response.json()["audit_record"]
    notification_audit = notification_response.json()["audit_record"]

    assignment_export_response = client.post("/api/audit/governance-assignment-history/export")
    routing_report_response = client.get("/api/audit/notification-routing-evidence")
    routing_export_response = client.post("/api/audit/notification-routing-evidence/export")

    assert assignment_response.status_code == 200
    assert notification_response.status_code == 200
    assert assignment_export_response.status_code == 200
    assert routing_report_response.status_code == 200
    assert routing_export_response.status_code == 200
    assignment_export = assignment_export_response.json()["export_package"]
    routing_report = routing_report_response.json()["routing_report"]
    routing_export = routing_export_response.json()["export_package"]
    assert assignment_export["export_id"].startswith("governance-assignment-history-export-")
    assert assignment_export["status"] == "ready_for_review"
    assert assignment_export["data_platform"] == "DB MARIAM"
    assert assignment_export["package_manifest"]["contains_secrets"] is False
    assert assignment_export["package_manifest"]["assignment_count"] >= 1
    assert assignment_audit["audit_id"] in [
        item["audit_id"] for item in assignment_export["history_report"]["assignments"]
    ]
    assert routing_report["title"] == "Governance Notification Routing Evidence Report"
    assert routing_report["status"] == "ready"
    assert routing_report["data_platform"] == "DB MARIAM"
    assert routing_report["route_count"] >= 1
    assert notification_audit["audit_id"] in [route["audit_id"] for route in routing_report["routes"]]
    assert routing_export["export_id"].startswith("notification-routing-evidence-export-")
    assert routing_export["status"] == "ready_for_review"
    assert routing_export["data_platform"] == "DB MARIAM"
    assert routing_export["package_manifest"]["contains_secrets"] is False
    assert routing_export["package_manifest"]["route_count"] == routing_report["route_count"]
    assert notification_audit["audit_id"] in [
        route["audit_id"] for route in routing_export["routing_report"]["routes"]
    ]


def test_governance_reviewer_workload_reports_assignments_and_escalations() -> None:
    client = TestClient(create_app())
    for index in range(3):
        response = client.post(
            "/api/audit/approval-assignments",
            json={
                "assigned_by": "governance-lead",
                "assignee_id": "quality-reviewer-02",
                "target_type": "artifact",
                "target_id": f"artifact-workload-target-{index}",
                "approval_role": "quality-reviewer",
                "reason": "Assign workload before delivery.",
                "evidence": {"assignment_source": "test"},
            },
        )
        assert response.status_code == 200

    workload_response = client.get("/api/audit/reviewer-workload")

    assert workload_response.status_code == 200
    report = workload_response.json()["workload_report"]
    assert report["title"] == "Governance Reviewer Workload Report"
    assert report["status"] == "attention_required"
    assert "quality-reviewer-02" in report["overloaded_reviewers"]
    reviewer = next(item for item in report["items"] if item["reviewer_id"] == "quality-reviewer-02")
    assert reviewer["assigned_count"] == 3
    assert reviewer["status"] == "overloaded"
    assert reviewer["data_platform"] == "DB MARIAM"

    escalation_response = client.post(
        "/api/audit/escalations",
        json={
            "escalated_by": "governance-lead",
            "reviewer_id": "quality-reviewer-02",
            "target_type": "artifact",
            "target_id": "artifact-workload-target-0",
            "reason": "Reviewer workload requires governance lead review.",
            "escalation_level": "governance-lead-review",
            "evidence": {"source": "test"},
        },
    )

    assert escalation_response.status_code == 200
    escalation = escalation_response.json()["audit_record"]
    assert escalation["action"] == "governance.escalate_reviewer_workload"
    assert escalation["decision"] == "escalated"
    assert escalation["evidence"]["reviewer_id"] == "quality-reviewer-02"
    history = client.get("/api/audit/governance-assignment-history").json()["history_report"]
    history_escalation = next(
        item for item in history["escalations"] if item["target_id"] == "artifact-workload-target-0"
    )
    assert history_escalation["audit_id"] == escalation["audit_id"]
    assert history_escalation["reviewer_id"] == "quality-reviewer-02"
    assert history_escalation["escalation_level"] == "governance-lead-review"
    assert history_escalation["data_platform"] == "DB MARIAM"

    escalated_report = client.get("/api/audit/reviewer-workload").json()["workload_report"]
    escalated_reviewer = next(
        item for item in escalated_report["items"] if item["reviewer_id"] == "quality-reviewer-02"
    )
    assert escalated_reviewer["status"] == "escalated"
    assert escalated_reviewer["escalation_count"] >= 1


def test_governance_workload_and_sla_can_be_exported_for_review() -> None:
    client = TestClient(create_app())

    assignment_response = client.post(
        "/api/audit/approval-assignments",
        json={
            "assigned_by": "governance-lead",
            "assignee_id": "quality-reviewer-export",
            "target_type": "artifact",
            "target_id": "artifact-governance-export-target",
            "approval_role": "quality-reviewer",
            "reason": "Assign before exporting workload and SLA evidence.",
            "evidence": {"verification": "governance-workload-sla-export"},
        },
    )
    workload_export_response = client.post("/api/audit/reviewer-workload/export")
    sla_export_response = client.post("/api/audit/governance-sla/export")

    assert assignment_response.status_code == 200
    assert workload_export_response.status_code == 200
    assert sla_export_response.status_code == 200
    workload_export = workload_export_response.json()["export_package"]
    sla_export = sla_export_response.json()["export_package"]
    assert workload_export["export_id"].startswith("governance-workload-evidence-export-")
    assert workload_export["title"] == "Mariam Governance Workload Evidence Export"
    assert workload_export["status"] == "ready_for_review"
    assert workload_export["format"] == "json"
    assert workload_export["data_platform"] == "DB MARIAM"
    assert workload_export["package_manifest"]["reviewer_count"] >= 1
    assert workload_export["package_manifest"]["contains_secrets"] is False
    assert workload_export["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert "quality-reviewer-export" in [
        item["reviewer_id"] for item in workload_export["workload_report"]["items"]
    ]
    assert sla_export["export_id"].startswith("governance-sla-evidence-export-")
    assert sla_export["title"] == "Mariam Governance SLA Evidence Export"
    assert sla_export["status"] == "ready_for_review"
    assert sla_export["format"] == "json"
    assert sla_export["data_platform"] == "DB MARIAM"
    assert sla_export["package_manifest"]["item_count"] >= 1
    assert sla_export["package_manifest"]["contains_secrets"] is False
    assert sla_export["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert "artifact-governance-export-target" in [
        item["target_id"] for item in sla_export["sla_report"]["items"]
    ]


def test_governance_sla_report_tracks_assignment_aging_rules() -> None:
    client = TestClient(create_app())

    assignment_response = client.post(
        "/api/audit/approval-assignments",
        json={
            "assigned_by": "governance-lead",
            "assignee_id": "quality-reviewer-sla",
            "target_type": "artifact",
            "target_id": "artifact-sla-target-01",
            "approval_role": "quality-reviewer",
            "reason": "Assign SLA-tracked artifact review.",
            "evidence": {"assignment_source": "sla-test"},
        },
    )
    assert assignment_response.status_code == 200

    response = client.get("/api/audit/governance-sla")

    assert response.status_code == 200
    report = response.json()["sla_report"]
    assert report["title"] == "Governance SLA and Escalation Aging Report"
    assert report["status"] == "ready"
    assert report["sla_minutes"] == 240
    assert report["escalation_after_minutes"] == 480
    assert report["data_platform"] == "DB MARIAM"
    item = next(item for item in report["items"] if item["target_id"] == "artifact-sla-target-01")
    assert item["reviewer_id"] == "quality-reviewer-sla"
    assert item["status"] == "on_track"
    assert item["escalation_required"] is False


def test_rejected_artifact_can_request_revision_and_return_to_approval() -> None:
    client = TestClient(create_app())
    mission_id = client.post(
        "/api/missions",
        json={
            "plugin_id": "crm",
            "user_request": "Prepare a client report that may need revision.",
            "requested_by": "command-center-user",
        },
    ).json()["mission"]["mission_id"]
    artifact = client.post(f"/api/artifacts/from-mission/{mission_id}").json()["artifact"]
    client.post(
        f"/api/artifacts/{artifact['artifact_id']}/reject",
        json={
            "rejected_by": "artifact-governance",
            "reason": "Request stronger client evidence before delivery.",
            "evidence": {"review": "revision-needed"},
        },
    )

    revision_response = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/request-revision",
        json={
            "requested_by": "artifact-governance",
            "revision_request": "Add traceability evidence and delivery constraints.",
            "evidence": {"revision_loop": "opened"},
        },
    )

    assert revision_response.status_code == 200
    revised_artifact = revision_response.json()["artifact"]
    assert revised_artifact["status"] == "awaiting_approval"
    assert "Revision requested" in revised_artifact["content"]
    assert "Delivery remains blocked until governance approval" in revised_artifact["content"]

    approve_response = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/approve",
        json={
            "approved_by": "artifact-governance",
            "evidence": {"review": "revised-artifact-approved"},
        },
    )
    assert approve_response.status_code == 200
    quality_response = client.post(
        f"/api/artifacts/{artifact['artifact_id']}/quality-review",
        json={"reviewed_by": "quality-governance", "evidence": {"quality": "revision-loop"}},
    )
    assert quality_response.status_code == 200
    assert quality_response.json()["quality_review"]["passed"] is True

    audit_response = client.get("/api/audit")
    assert artifact["artifact_id"] in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "artifact.request_revision"
    ]
    events_response = client.get("/api/runtime/events")
    assert artifact["artifact_id"] in [
        event["payload"].get("artifact_id")
        for event in events_response.json()["events"]
        if event["name"] == "artifact.revision_requested"
    ]


def test_plugin_validation_records_audit_event_and_stamp() -> None:
    client = TestClient(create_app())
    manifest_path = Path(__file__).resolve().parents[2] / "plugins" / "crm" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plugin_id = client.post("/api/plugins", json=manifest).json()["plugin"]["plugin_id"]

    validate_response = client.post(
        f"/api/plugins/{plugin_id}/validate",
        json={
            "actor_id": "plugin-governance",
            "reason": "Validate plugin governance contract.",
            "evidence": {"review": "passed"},
        },
    )

    assert validate_response.status_code == 200
    report = validate_response.json()["validation_report"]
    assert report["passed"] is True
    assert report["validation_id"].startswith("plugin-validation-")
    assert {check["name"] for check in report["checks"]} >= {
        "dashboard_route_declared",
        "api_prefix_declared",
        "permissions_declared",
        "tests_declared",
        "chief_agent_declared",
        "data_boundary_declared",
    }

    list_response = client.get("/api/plugins")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")
    plugin = next(plugin for plugin in list_response.json()["plugins"] if plugin["plugin_id"] == plugin_id)

    assert plugin["validation"]["validation_id"] == report["validation_id"]
    assert plugin["validation"]["passed"] is True
    assert plugin_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "plugin.validate" and record["decision"] == "approved"
    ]
    assert report["validation_id"] in [
        event["payload"].get("validation_id")
        for event in event_response.json()["events"]
        if event["name"] == "plugin.validate"
    ]


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
    analyze_runtime_object_impact(client, object_id, "disable")
    approve_runtime_object_change(client, object_id, "disable")

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

    validate_response = client.post(
        f"/api/runtime-objects/{object_id}/validate",
        json={
            "actor_id": "runtime-governance",
            "reason": "Validate before enable.",
            "evidence": {"review": "passed"},
        },
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["validation_report"]["passed"] is True

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


def test_runtime_object_enable_requires_successful_validation() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Enable Gate Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime"},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]
    analyze_runtime_object_impact(client, object_id, "disable")
    approve_runtime_object_change(client, object_id, "disable")
    client.post(
        f"/api/runtime-objects/{object_id}/disable",
        json={
            "actor_id": "runtime-governance",
            "reason": "Disable before gated enable.",
            "evidence": {"review": "pending-validation"},
        },
    )

    enable_response = client.post(
        f"/api/runtime-objects/{object_id}/enable",
        json={
            "actor_id": "runtime-governance",
            "reason": "Attempt enable without validation.",
            "evidence": {"review": "missing-validation"},
        },
    )

    assert enable_response.status_code == 400
    assert "must pass validation" in enable_response.json()["detail"]


def test_runtime_object_readiness_reports_real_blockers_and_ready_state() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Readiness Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime", "local": True},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]

    first_readiness = client.get(f"/api/runtime-objects/{object_id}/readiness")
    assert first_readiness.status_code == 200
    first_report = first_readiness.json()["readiness_report"]
    assert first_report["readiness_state"] == "needs_validation"
    assert first_report["ready_to_execute"] is False
    assert "Runtime object must pass validation before execution." in first_report["blockers"]

    validate_response = client.post(
        f"/api/runtime-objects/{object_id}/validate",
        json={
            "actor_id": "runtime-governance",
            "reason": "Validate readiness provider.",
            "evidence": {"review": "readiness-test"},
        },
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["validation_report"]["passed"] is True

    ready_response = client.get(f"/api/runtime-objects/{object_id}/readiness")
    assert ready_response.status_code == 200
    ready_report = ready_response.json()["readiness_report"]
    assert ready_report["readiness_state"] == "ready"
    assert ready_report["ready_to_execute"] is True
    assert ready_report["blockers"] == []


def test_provider_disable_requires_impact_analysis() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Impact Gate Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime"},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]

    disable_response = client.post(
        f"/api/runtime-objects/{object_id}/disable",
        json={
            "actor_id": "runtime-governance",
            "reason": "Attempt disable without impact analysis.",
            "evidence": {"review": "missing-impact-analysis"},
        },
    )

    assert disable_response.status_code == 400
    assert "requires impact analysis" in disable_response.json()["detail"]


def test_high_risk_provider_disable_requires_change_approval() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Approval Gate Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime"},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]
    analyze_runtime_object_impact(client, object_id, "disable")

    disable_response = client.post(
        f"/api/runtime-objects/{object_id}/disable",
        json={
            "actor_id": "runtime-governance",
            "reason": "Attempt disable without high-risk approval.",
            "evidence": {"review": "missing-approval"},
        },
    )

    assert disable_response.status_code == 400
    assert "requires approval" in disable_response.json()["detail"]


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
    analyze_runtime_object_impact(client, object_id, "delete")
    approve_runtime_object_change(client, object_id, "delete")

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

    list_response = client.get("/api/runtime-objects")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")
    runtime_object = next(
        item for item in list_response.json()["runtime_objects"] if item["object_id"] == object_id
    )

    assert runtime_object["manifest"]["validation"]["validation_id"] == report["validation_id"]
    assert runtime_object["manifest"]["validation"]["passed"] is True

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


def test_runtime_object_impact_analysis_records_risk() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Impact Provider",
            "version": "0.1.0",
            "manifest": {
                "provider_type": "model_runtime",
                "local": True,
                "capabilities": ["chat", "embedding"],
                "dependencies": ["ollama"],
            },
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]

    impact_response = client.post(
        f"/api/runtime-objects/{object_id}/impact-analysis",
        json={
            "actor_id": "runtime-governance",
            "reason": "Analyze before disable.",
            "intended_action": "disable",
            "evidence": {"review": "pre-disable"},
        },
    )

    assert impact_response.status_code == 200
    report = impact_response.json()["impact_report"]
    assert report["object_id"] == object_id
    assert report["intended_action"] == "disable"
    assert report["risk_level"] == "high"
    assert "chat" in report["affected_capabilities"]
    assert "local-runtime-host" in report["affected_dependencies"]

    list_response = client.get("/api/runtime-objects")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")
    runtime_object = next(
        item for item in list_response.json()["runtime_objects"] if item["object_id"] == object_id
    )

    assert runtime_object["manifest"]["impact_analysis"]["impact_id"] == report["impact_id"]
    assert runtime_object["manifest"]["impact_analysis"]["intended_action"] == "disable"

    assert object_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "runtime_object.impact_analysis"
    ]
    assert report["impact_id"] in [
        event["payload"].get("impact_id")
        for event in event_response.json()["events"]
        if event["name"] == "runtime_object.impact_analysis"
    ]


def test_runtime_object_change_approval_records_gate() -> None:
    client = TestClient(create_app())
    create_response = client.post(
        "/api/runtime-objects",
        json={
            "object_type": "provider",
            "name": "Approval Provider",
            "version": "0.1.0",
            "manifest": {"provider_type": "model_runtime"},
        },
    )
    object_id = create_response.json()["runtime_object"]["object_id"]
    analyze_runtime_object_impact(client, object_id, "disable")

    approval_response = client.post(
        f"/api/runtime-objects/{object_id}/approve-change",
        json={
            "actor_id": "runtime-governance",
            "reason": "Approve provider disable.",
            "intended_action": "disable",
            "evidence": {"approval": "granted"},
        },
    )

    assert approval_response.status_code == 200
    report = approval_response.json()["approval_report"]
    assert report["object_id"] == object_id
    assert report["intended_action"] == "disable"
    assert report["approval_id"].startswith("approval-")

    list_response = client.get("/api/runtime-objects")
    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")
    runtime_object = next(
        item for item in list_response.json()["runtime_objects"] if item["object_id"] == object_id
    )

    assert runtime_object["manifest"]["change_approval"]["approval_id"] == report["approval_id"]
    assert object_id in [
        record["target_id"]
        for record in audit_response.json()["audit_records"]
        if record["action"] == "runtime_object.approve_change"
    ]
    assert report["approval_id"] in [
        event["payload"].get("approval_id")
        for event in event_response.json()["events"]
        if event["name"] == "runtime_object.approve_change"
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
    event_body = publish_response.json()["event"]

    list_response = client.get("/api/runtime/events")

    assert publish_response.status_code == 200
    assert event_body["name"] == "runtime.audit.test"
    assert event_body["source"] == "test-suite"
    assert event_body["payload"]["data_platform"] == "DB MARIAM"
    assert event_body["created_at"]
    assert list_response.status_code == 200
    assert isinstance(list_response.json()["events"], list)
    assert event_id in [event["event_id"] for event in list_response.json()["events"]]
    event = next(event for event in list_response.json()["events"] if event["event_id"] == event_id)
    assert set(event) == {"name", "source", "payload", "event_id", "created_at"}
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


def test_runtime_readiness_reports_executable_layers() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    checks = {check["name"]: check for check in body["checks"]}
    assert checks["runtime_core"]["status"] == "ready"
    assert checks["event_bus"]["status"] == "ready"
    assert checks["audit_layer"]["status"] == "ready"
    assert checks["mission_layer"]["status"] == "ready"
    assert checks["plugin_registry"]["status"] == "ready"
    assert checks["runtime_objects"]["status"] == "ready"
    assert checks["ai_resource_manager"]["status"] == "ready"
    assert checks["artifact_delivery_pipeline"]["status"] == "ready"


def test_runtime_verification_report_summarizes_required_checks() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/verification-report")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "passed"
    assert body["readiness_status"] == "ready"
    assert body["ready_checks"] == body["total_checks"]
    assert body["summary"]["health"] == "healthy"
    assert "/api/runtime/readiness" in body["required_endpoints"]
    assert "/api/artifacts/quality-reviews" in body["required_endpoints"]
    assert "quality review" in body["smoke_flow"]


def test_runtime_verification_snapshot_records_audit_evidence() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/runtime/verification-report/record",
        json={
            "actor_id": "project-verifier",
            "evidence": {"source": "test-suite"},
        },
    )

    assert response.status_code == 200
    audit_record = response.json()["audit_record"]
    assert audit_record["action"] == "runtime.verification_report.record"
    assert audit_record["target_type"] == "runtime_verification_report"
    assert audit_record["target_id"] == "command-center"
    assert audit_record["decision"] == "approved"
    assert audit_record["evidence"]["verification_status"] == "passed"
    assert audit_record["evidence"]["source"] == "test-suite"
    assert "/api/runtime/verification-report" in audit_record["evidence"]["required_endpoints"]

    audit_response = client.get("/api/audit")
    event_response = client.get("/api/runtime/events")

    assert audit_record["audit_id"] in [
        record["audit_id"] for record in audit_response.json()["audit_records"]
    ]
    assert audit_record["audit_id"] in [
        event["payload"].get("audit_id")
        for event in event_response.json()["events"]
        if event["name"] == "audit.recorded"
    ]


def test_runtime_verification_snapshot_history_lists_snapshots() -> None:
    client = TestClient(create_app())
    first_response = client.post(
        "/api/runtime/verification-report/record",
        json={
            "actor_id": "project-verifier",
            "evidence": {"sequence": "first"},
        },
    )
    second_response = client.post(
        "/api/runtime/verification-report/record",
        json={
            "actor_id": "project-verifier",
            "evidence": {"sequence": "second"},
        },
    )

    history_response = client.get("/api/runtime/verification-report/snapshots")

    assert history_response.status_code == 200
    snapshots = history_response.json()["snapshots"]
    snapshot_ids = [snapshot["audit_id"] for snapshot in snapshots]
    assert first_response.json()["audit_record"]["audit_id"] in snapshot_ids
    assert second_response.json()["audit_record"]["audit_id"] in snapshot_ids
    assert snapshots[0]["action"] == "runtime.verification_report.record"
    assert snapshots[0]["evidence"]["verification_status"] == "passed"


def test_runtime_diagnostics_reports_verification_readiness_and_activity() -> None:
    client = TestClient(create_app())
    snapshot_response = client.post(
        "/api/runtime/verification-report/record",
        json={
            "actor_id": "diagnostics-verifier",
            "evidence": {"source": "diagnostics-test"},
        },
    )
    audit_id = snapshot_response.json()["audit_record"]["audit_id"]

    response = client.get("/api/runtime/diagnostics")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "passed"
    assert body["data_platform"] == "DB MARIAM"
    assert body["verification_report"]["readiness_status"] == "ready"
    assert body["verification_report"]["ready_checks"] == body["verification_report"]["total_checks"]
    assert any(check["name"] == "artifact_delivery_pipeline" for check in body["readiness_checks"])
    assert audit_id in [record["audit_id"] for record in body["recent_audit_records"]]
    assert "audit.recorded" in [event["name"] for event in body["recent_events"]]


def test_runtime_diagnostics_can_be_exported_as_review_package() -> None:
    client = TestClient(create_app())

    response = client.post("/api/runtime/diagnostics/export")

    assert response.status_code == 200
    export_package = response.json()["export_package"]
    assert export_package["export_id"].startswith("diagnostics-export-")
    assert export_package["status"] == "ready_for_review"
    assert export_package["format"] == "json"
    assert export_package["data_platform"] == "DB MARIAM"
    assert export_package["package_manifest"]["title"] == "Mariam Runtime Diagnostics Export"
    assert export_package["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert export_package["diagnostics"]["verification_report"]["readiness_status"] == "ready"


def test_runtime_usage_guide_maps_buttons_to_backend_results() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/usage-guide")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Mariam Command Center End-to-End Usage Guide"
    assert body["status"] == "executable"
    assert body["data_platform"] == "DB MARIAM"
    assert "visible action" in body["operating_rule"]
    assert len(body["steps"]) >= 6
    actions = {step["action"] for step in body["steps"]}
    assert "Create governed mission" in actions
    assert "Export diagnostics" in actions
    diagnostics_step = next(step for step in body["steps"] if step["action"] == "Export diagnostics")
    assert diagnostics_step["frontend_control"] == "Export Diagnostics"
    assert diagnostics_step["api_endpoint"] == "POST /api/runtime/diagnostics/export"
    assert diagnostics_step["result"] == "The user receives a diagnostics export id with ready_for_review status."


def test_runtime_usage_guide_can_be_exported_as_review_package() -> None:
    client = TestClient(create_app())

    response = client.post("/api/runtime/usage-guide/export")

    assert response.status_code == 200
    export_package = response.json()["export_package"]
    assert export_package["export_id"].startswith("usage-guide-export-")
    assert export_package["status"] == "ready_for_review"
    assert export_package["format"] == "json"
    assert export_package["data_platform"] == "DB MARIAM"
    assert export_package["package_manifest"]["title"] == "Mariam Command Center End-to-End Usage Guide"
    assert export_package["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert export_package["package_manifest"]["step_count"] == len(export_package["usage_guide"]["steps"])
    assert export_package["usage_guide"]["steps"][0]["frontend_control"] == "Refresh System Status"


def test_runtime_completion_report_summarizes_project_readiness() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/completion-report")

    assert response.status_code == 200
    report = response.json()
    assert report["title"] == "Mariam Executable Project Completion Report"
    assert report["status"] == "in_progress_verified"
    assert report["data_platform"] == "DB MARIAM"
    assert 1 <= report["completion_percent"] <= 100
    assert report["verification"]["status"] == "passed"
    assert report["usage_guide"]["status"] == "executable"
    assert {area["name"] for area in report["areas"]} >= {
        "Backend API foundation",
        "Frontend Command Center",
        "DB MARIAM persistence boundary",
        "Governance and delivery workflow",
        "Verification automation",
    }


def test_runtime_governed_endpoints_publish_typed_response_models() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    openapi = response.json()
    assert (
        openapi["paths"]["/api/runtime/completion-report"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ProjectCompletionReportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/implementation-roadmap"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ImplementationRoadmapResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/verification-automation"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/VerificationAutomationResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/verification-automation/failure-summary/export"]["post"]
        ["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/VerificationFailureSummaryExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/verification-report"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/VerificationReportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/verification-report/record"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/VerificationSnapshotRecordResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/verification-report/snapshots"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/VerificationSnapshotsResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/events"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/RuntimeEventsResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/events"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/RuntimeEventPublishResponse"
    )
    assert (
        openapi["paths"]["/api/audit/reviewer-workload"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ReviewerWorkloadResponse"
    )
    assert (
        openapi["paths"]["/api/audit/reviewer-workload/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/GovernanceWorkloadEvidenceExportResponse"
    )
    assert (
        openapi["paths"]["/api/audit/governance-assignment-history"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/GovernanceAssignmentHistoryResponse"
    )
    assert (
        openapi["paths"]["/api/audit/governance-assignment-history/export"]["post"]
        ["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/GovernanceAssignmentHistoryExportResponse"
    )
    assert (
        openapi["paths"]["/api/audit/notification-routing-evidence"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/NotificationRoutingEvidenceResponse"
    )
    assert (
        openapi["paths"]["/api/audit/notification-routing-evidence/export"]["post"]
        ["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/NotificationRoutingEvidenceExportResponse"
    )
    assert (
        openapi["paths"]["/api/audit/reviewer-decisions"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/AuditRecordResponse"
    )
    assert (
        openapi["paths"]["/api/audit/governance-sla"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/GovernanceSLAResponse"
    )
    assert (
        openapi["paths"]["/api/audit/governance-sla/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/GovernanceSLAEvidenceExportResponse"
    )
    assert (
        openapi["paths"]["/api/audit/escalations"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/AuditRecordResponse"
    )
    assert (
        openapi["paths"]["/api/audit/governance-decision-evidence/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/GovernanceDecisionEvidenceExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/diagnostics"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DiagnosticsResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/diagnostics/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DiagnosticsExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/usage-guide"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/UsageGuideResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/usage-guide/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/UsageGuideExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/delivery-evidence-report"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DeliveryEvidenceReportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/delivery-evidence-report/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DeliveryEvidenceExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/readiness"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DataPlatformReadinessResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/readiness/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DataPlatformReadinessExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/migration-runner"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/MigrationRunnerStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/migration-runner/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/MigrationRunnerExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/seed-data"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/SeedDataStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/backup-readiness"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/BackupReadinessStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/plugin-schema-isolation"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PluginSchemaIsolationStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/docker-persistence"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DockerPersistenceStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/live-db-smoke"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/LiveDatabaseSmokeStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/docker-container-execution"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/DockerContainerExecutionStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/live-write-smoke"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/LiveDatabaseWriteStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/live-repository-write-smoke"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/LiveRepositoryWriteStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/logs-store"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/LogsStoreReadStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/logs-store/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/LogsStoreExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/audit-event-archive"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/AuditEventArchiveReadStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/audit-event-archive/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/AuditEventArchiveExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/metrics-store"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/MetricsStoreReadStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/metrics-store/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/MetricsStoreExportResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/artifact-lineage"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ArtifactLineageReadStatusResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/data-platform/artifact-lineage/export"]["post"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ArtifactLineageExportResponse"
    )
    data_record_store_response_refs = {
        ("get", "/api/runtime/data-platform/communication-store"): "DataRecordStoreReadStatusResponse",
        ("post", "/api/runtime/data-platform/communication-store/export"): "DataRecordStoreExportResponse",
        ("get", "/api/runtime/data-platform/document-store"): "DataRecordStoreReadStatusResponse",
        ("post", "/api/runtime/data-platform/document-store/export"): "DataRecordStoreExportResponse",
        ("get", "/api/runtime/data-platform/workflow-store"): "DataRecordStoreReadStatusResponse",
        ("post", "/api/runtime/data-platform/workflow-store/export"): "DataRecordStoreExportResponse",
        ("get", "/api/runtime/data-platform/capability-graph-store"): "DataRecordStoreReadStatusResponse",
        ("post", "/api/runtime/data-platform/capability-graph-store/export"): "DataRecordStoreExportResponse",
        ("get", "/api/runtime/data-platform/vector-index-store"): "DataRecordStoreReadStatusResponse",
        ("post", "/api/runtime/data-platform/vector-index-store/export"): "DataRecordStoreExportResponse",
        ("get", "/api/runtime/data-platform/artifact-store"): "DataRecordStoreReadStatusResponse",
        ("post", "/api/runtime/data-platform/artifact-store/export"): "DataRecordStoreExportResponse",
    }
    for (method, path), schema_name in data_record_store_response_refs.items():
        assert (
            openapi["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
            == f"#/components/schemas/{schema_name}"
        )
    assert (
        openapi["paths"]["/api/runtime/frontend/regression-snapshot"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/FrontendRegressionSnapshotResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/frontend/visual-contract"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/FrontendVisualContractResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/frontend/browser-screenshot-plan"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/FrontendBrowserScreenshotPlanResponse"
    )
    assert (
        openapi["paths"]["/api/runtime/frontend/browser-screenshot-capture"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/FrontendBrowserScreenshotCaptureResponse"
    )
    assert (
        openapi["paths"]["/api/plugins/{plugin_id}/timeline"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PluginTimelineResponse"
    )
    assert (
        openapi["paths"]["/api/plugins/{plugin_id}/settings"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PluginSettingsResponse"
    )
    assert (
        openapi["paths"]["/api/plugins/{plugin_id}/settings"]["patch"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PluginSettingsResponse"
    )
    assert (
        openapi["paths"]["/api/plugins/{plugin_id}/dashboard"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PluginDashboardResponse"
    )
    assert (
        openapi["paths"]["/api/plugins/{plugin_id}/workspace"]["get"]["responses"]["200"]
        ["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PluginWorkspaceResponse"
    )
    plugin_response_refs = {
        ("post", "/api/plugins"): "PluginMutationResponse",
        ("get", "/api/plugins"): "PluginListResponse",
        ("post", "/api/plugins/{plugin_id}/chat"): "PluginChatResponse",
        ("post", "/api/plugins/{plugin_id}/enable"): "PluginMutationResponse",
        ("patch", "/api/plugins/{plugin_id}"): "PluginMutationResponse",
        ("post", "/api/plugins/{plugin_id}/validate"): "PluginValidationResponse",
        ("post", "/api/plugins/{plugin_id}/disable"): "PluginMutationResponse",
        ("post", "/api/plugins/{plugin_id}/delete"): "PluginMutationResponse",
        ("post", "/api/plugins/{plugin_id}/restore"): "PluginMutationResponse",
        ("post", "/api/plugins/{plugin_id}/impact-analysis"): "PluginImpactResponse",
        ("post", "/api/plugins/{plugin_id}/approve-change"): "PluginApprovalResponse",
        ("post", "/api/plugins/{plugin_id}/rollback"): "PluginMutationResponse",
        ("post", "/api/plugins/{plugin_id}/export-dna"): "PluginDNAExportResponse",
        ("post", "/api/plugins/import-dna"): "PluginMutationResponse",
    }
    for (method, path), schema_name in plugin_response_refs.items():
        assert (
            openapi["paths"][path][method]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
            == f"#/components/schemas/{schema_name}"
        )
    assert "CompletionAreaResponse" in openapi["components"]["schemas"]
    assert "RuntimeCheckResponse" in openapi["components"]["schemas"]
    assert "RuntimeEventPublishRequest" in openapi["components"]["schemas"]
    assert "RuntimeEventResponse" in openapi["components"]["schemas"]
    assert "RuntimeEventsResponse" in openapi["components"]["schemas"]
    assert "RuntimeEventPublishResponse" in openapi["components"]["schemas"]
    assert "AuditRecordResponse" in openapi["components"]["schemas"]
    assert "ReviewerWorkloadResponse" in openapi["components"]["schemas"]
    assert "ReviewerWorkloadReport" in openapi["components"]["schemas"]
    assert "GovernanceWorkloadEvidenceExportResponse" in openapi["components"]["schemas"]
    assert "GovernanceWorkloadEvidenceExportPackage" in openapi["components"]["schemas"]
    assert "GovernanceAssignmentHistoryExportResponse" in openapi["components"]["schemas"]
    assert "GovernanceAssignmentHistoryExportPackage" in openapi["components"]["schemas"]
    assert "NotificationRoutingEvidenceResponse" in openapi["components"]["schemas"]
    assert "NotificationRoutingEvidenceReport" in openapi["components"]["schemas"]
    assert "NotificationRoutingEvidenceExportResponse" in openapi["components"]["schemas"]
    assert "NotificationRoutingEvidenceExportPackage" in openapi["components"]["schemas"]
    assert "GovernanceAssignmentHistoryResponse" in openapi["components"]["schemas"]
    assert "GovernanceAssignmentHistoryReport" in openapi["components"]["schemas"]
    assert "GovernanceSLAResponse" in openapi["components"]["schemas"]
    assert "GovernanceSLAReport" in openapi["components"]["schemas"]
    assert "GovernanceSLAEvidenceExportResponse" in openapi["components"]["schemas"]
    assert "GovernanceSLAEvidenceExportPackage" in openapi["components"]["schemas"]
    assert "GovernanceDecisionEvidenceExportResponse" in openapi["components"]["schemas"]
    assert "GovernanceDecisionEvidenceExportPackage" in openapi["components"]["schemas"]
    assert "PluginTimelineResponse" in openapi["components"]["schemas"]
    assert "PluginTimelineAuditRecordResponse" in openapi["components"]["schemas"]
    assert "PluginTimelineEventResponse" in openapi["components"]["schemas"]
    assert "PluginTimelineSummaryResponse" in openapi["components"]["schemas"]
    assert "PluginWorkspaceResponse" in openapi["components"]["schemas"]
    assert "PluginDashboardResponse" in openapi["components"]["schemas"]
    assert "PluginSettingsResponse" in openapi["components"]["schemas"]
    assert "PluginChiefAgentResponse" in openapi["components"]["schemas"]
    assert "PluginSwarmAgentResponse" in openapi["components"]["schemas"]
    assert "PluginWorkspaceActionResponse" in openapi["components"]["schemas"]
    assert "PluginDataBoundaryResponse" in openapi["components"]["schemas"]
    assert "DataPlatformReadinessResponse" in openapi["components"]["schemas"]
    assert "MigrationRunnerStatusResponse" in openapi["components"]["schemas"]
    assert "SeedDataStatusResponse" in openapi["components"]["schemas"]
    assert "BackupReadinessStatusResponse" in openapi["components"]["schemas"]
    assert "PluginSchemaIsolationStatusResponse" in openapi["components"]["schemas"]
    assert "DockerPersistenceStatusResponse" in openapi["components"]["schemas"]
    assert "LiveDatabaseSmokeStatusResponse" in openapi["components"]["schemas"]
    assert "DockerContainerExecutionStatusResponse" in openapi["components"]["schemas"]
    assert "LiveDatabaseWriteStatusResponse" in openapi["components"]["schemas"]
    assert "LiveRepositoryWriteStatusResponse" in openapi["components"]["schemas"]
    assert "LogsStoreReadStatusResponse" in openapi["components"]["schemas"]
    assert "LogsStoreExportResponse" in openapi["components"]["schemas"]
    assert "AuditEventArchiveReadStatusResponse" in openapi["components"]["schemas"]
    assert "AuditEventArchiveExportResponse" in openapi["components"]["schemas"]
    assert "MetricsStoreReadStatusResponse" in openapi["components"]["schemas"]
    assert "MetricsStoreExportResponse" in openapi["components"]["schemas"]
    assert "ArtifactLineageReadStatusResponse" in openapi["components"]["schemas"]
    assert "ArtifactLineageExportResponse" in openapi["components"]["schemas"]
    assert "DataRecordStoreReadStatusResponse" in openapi["components"]["schemas"]
    assert "DataRecordStoreExportResponse" in openapi["components"]["schemas"]
    assert "DeliveryEvidenceExportResponse" in openapi["components"]["schemas"]
    live_repository_properties = openapi["components"]["schemas"]["LiveRepositoryWriteStatusResponse"][
        "properties"
    ]
    assert "logs_store_record_id" in live_repository_properties
    assert "artifact_lineage_record_id" in live_repository_properties
    assert "logs_store_record_written" in live_repository_properties
    assert "artifact_lineage_record_written" in live_repository_properties
    assert "VerificationReportResponse" in openapi["components"]["schemas"]
    assert "DiagnosticsResponse" in openapi["components"]["schemas"]
    assert "UsageGuideResponse" in openapi["components"]["schemas"]
    assert "FrontendRegressionSnapshotResponse" in openapi["components"]["schemas"]


def test_runtime_completion_report_can_be_exported_as_review_package() -> None:
    client = TestClient(create_app())

    response = client.post("/api/runtime/completion-report/export")

    assert response.status_code == 200
    export_package = response.json()["export_package"]
    assert export_package["export_id"].startswith("completion-report-export-")
    assert export_package["status"] == "ready_for_review"
    assert export_package["format"] == "json"
    assert export_package["data_platform"] == "DB MARIAM"
    assert export_package["package_manifest"]["title"] == "Mariam Executable Project Completion Report"
    assert export_package["package_manifest"]["verification_status"] == "passed"
    assert export_package["package_manifest"]["area_count"] == len(export_package["completion_report"]["areas"])
    assert export_package["completion_report"]["status"] == "in_progress_verified"


def test_runtime_implementation_roadmap_orders_next_work() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/implementation-roadmap")

    assert response.status_code == 200
    roadmap = response.json()
    assert roadmap["title"] == "Mariam Next Implementation Roadmap"
    assert roadmap["status"] == "ready_for_execution"
    assert roadmap["data_platform"] == "DB MARIAM"
    assert roadmap["items"][0]["area"] == "Backend API foundation"
    assert roadmap["items"][0]["priority"] == "high"
    assert "lowest-completion" in roadmap["operating_rule"]
    assert all("acceptance_signal" in item for item in roadmap["items"])


def test_runtime_frontend_regression_snapshot_records_critical_controls() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/frontend/regression-snapshot")

    assert response.status_code == 200
    snapshot = response.json()
    assert snapshot["title"] == "Mariam Command Center Frontend Regression Snapshot"
    assert snapshot["status"] == "ready"
    assert snapshot["data_platform"] == "DB MARIAM"
    assert "Refresh Actor Context" in snapshot["controls_checked"]
    assert "Enforce Human Identity" in snapshot["controls_checked"]
    assert "Refresh Docker Execution" in snapshot["controls_checked"]
    assert "Run DB MARIAM Write Smoke" in snapshot["controls_checked"]
    assert "Run Repository Write Smoke" in snapshot["controls_checked"]
    assert "Refresh Audit Event Archive" in snapshot["controls_checked"]
    assert "Export Audit Event Archive Evidence" in snapshot["controls_checked"]
    assert "Refresh Metrics Store" in snapshot["controls_checked"]
    assert "Export Metrics Store Evidence" in snapshot["controls_checked"]
    assert "Refresh Reviewer Workload" in snapshot["controls_checked"]
    assert "Refresh Governance SLA" in snapshot["controls_checked"]
    assert "Escalate Reviewer Workload" in snapshot["controls_checked"]
    assert "Record Reviewer Decision" in snapshot["controls_checked"]
    assert "Export Reviewer Decision Evidence" in snapshot["controls_checked"]
    assert "Export Delivery Governance Evidence" in snapshot["controls_checked"]
    assert "Refresh Visual Contract" in snapshot["controls_checked"]
    assert "Refresh Screenshot Plan" in snapshot["controls_checked"]
    assert "Refresh Screenshot Capture" in snapshot["controls_checked"]
    assert "Refresh Verification Automation" in snapshot["controls_checked"]
    assert "Export Failure Summary" in snapshot["controls_checked"]
    assert "Latest CI run result ingestion" in snapshot["controls_checked"]
    assert "Filter delivery SLA by state" in snapshot["controls_checked"]
    assert "Filter delivery SLA by reviewer queue" in snapshot["controls_checked"]
    assert "Filter reviewer decisions by reviewer" in snapshot["controls_checked"]
    assert "Filter reviewer decisions by outcome" in snapshot["controls_checked"]
    assert "mariam.commandCenter.preferences.v1" in snapshot["controls_checked"]
    assert "deliverySlaStateFilter" in snapshot["controls_checked"]
    assert "deliveryReviewerQueueFilter" in snapshot["controls_checked"]
    assert "governanceDecisionReviewerFilter" in snapshot["controls_checked"]
    assert "governanceDecisionOutcomeFilter" in snapshot["controls_checked"]
    assert "Retry" in snapshot["controls_checked"]
    assert "command-center-error-banner" in snapshot["controls_checked"]
    assert snapshot["missing_controls"] == []
    assert snapshot["missing_viewports"] == []
    assert snapshot["missing_keyboard_traversal_targets"] == []
    assert snapshot["missing_error_contracts"] == []
    assert "buildApiError" in snapshot["error_contracts"]
    assert "createPanelError" in snapshot["error_contracts"]
    assert "retryAction" in snapshot["error_contracts"]
    assert 'className="skip-link"' in snapshot["keyboard_traversal_targets"]
    assert 'aria-label="Command Center sections"' in snapshot["keyboard_traversal_targets"]
    assert "aria-current={activeSection === item.href.slice(1) ? 'page' : undefined}" in snapshot[
        "keyboard_traversal_targets"
    ]
    assert "data-active={activeSection === item.href.slice(1) ? 'true' : undefined}" in snapshot[
        "keyboard_traversal_targets"
    ]
    assert "writeCommandCenterPreference('activeSection', sectionId)" in snapshot[
        "keyboard_traversal_targets"
    ]
    assert 'id="workspace" tabIndex="-1"' in snapshot["keyboard_traversal_targets"]
    assert snapshot["artifact_path"].endswith("command-center-regression-snapshot.json")
    assert Path(snapshot["artifact_path"]).exists()


def test_runtime_frontend_visual_contract_records_layout_and_breakpoints() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/frontend/visual-contract")

    assert response.status_code == 200
    contract = response.json()
    assert contract["title"] == "Mariam Command Center Frontend Visual Contract"
    assert contract["status"] == "ready"
    assert contract["data_platform"] == "DB MARIAM"
    assert "--bg: #0a0b12" in contract["design_tokens_checked"]
    assert ".shell" in contract["layout_contracts_checked"]
    assert "@media (max-width: 860px)" in contract["breakpoint_contracts_checked"]
    assert "#governance" in contract["screenshot_targets"]
    assert contract["missing_design_tokens"] == []
    assert contract["missing_layout_contracts"] == []
    assert contract["missing_breakpoint_contracts"] == []
    assert contract["artifact_path"].endswith("command-center-visual-contract.json")
    assert Path(contract["artifact_path"]).exists()


def test_runtime_frontend_browser_screenshot_plan_records_viewports_and_artifacts() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/frontend/browser-screenshot-plan")

    assert response.status_code == 200
    plan = response.json()
    assert plan["title"] == "Mariam Command Center Browser Screenshot Artifact Plan"
    assert plan["status"] == "ready"
    assert plan["data_platform"] == "DB MARIAM"
    assert "desktop" in [target["name"] for target in plan["viewport_targets"]]
    assert "#governance" in plan["critical_sections"]
    assert any(
        artifact.endswith("desktop-command-center.png")
        for artifact in plan["screenshot_artifacts"]
    )
    assert "screenshot_artifacts_captured" in plan["required_browser_checks"]
    assert plan["artifact_path"].endswith("command-center-browser-screenshot-plan.json")
    assert Path(plan["artifact_path"]).exists()


def test_runtime_frontend_browser_screenshot_capture_reports_generated_artifacts() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/frontend/browser-screenshot-capture")

    assert response.status_code == 200
    report = response.json()
    assert report["title"] == "Mariam Command Center Browser Screenshot Capture Report"
    assert report["data_platform"] == "DB MARIAM"
    assert report["artifact_path"].endswith("command-center-browser-screenshot-capture.json")
    assert {artifact["viewport"] for artifact in report["artifacts"]} == {"desktop", "tablet", "mobile"}
    assert {preview["viewport"] for preview in report["thumbnail_previews"]} == {"desktop", "tablet", "mobile"}
    assert all(preview["data_url"].startswith("data:image/png;base64,") for preview in report["thumbnail_previews"])
    assert all(artifact["thumbnail_data_url"].startswith("data:image/png;base64,") for artifact in report["artifacts"])
    assert "capture_report_written" in [check["name"] for check in report["checks"]]
    assert "thumbnail_previews_available" in [check["name"] for check in report["checks"]]


def test_runtime_verification_automation_contract_records_local_coverage() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/verification-automation")

    assert response.status_code == 200
    contract = response.json()
    assert contract["title"] == "Mariam Verification Automation Contract"
    assert contract["status"] == "ready"
    assert contract["data_platform"] == "DB MARIAM"
    assert contract["local_automation_status"] == "ready"
    assert contract["ci_status"] == "ready"
    assert contract["ci_badge"]["badge_url"].endswith("/actions/workflows/verify.yml/badge.svg?branch=main")
    assert contract["ci_badge"]["actions_url"].endswith("/actions/workflows/verify.yml")
    assert contract["latest_run_status"]["polling_status"] == "configured"
    assert contract["latest_run_status"]["ingestion_status"] == "ready"
    assert "actions/workflows/verify.yml/runs" in contract["latest_run_status"]["api_url"]
    assert contract["ci_run_ingestion"]["ingestion_status"] == "ready"
    assert contract["ci_run_ingestion"]["mode"] == "github_actions_api_contract_with_local_fallback"
    assert contract["ci_run_ingestion"]["latest_run"]["name"] == "Mariam Verify"
    assert "status" in contract["ci_run_ingestion"]["parsed_fields"]
    assert "conclusion" in contract["ci_run_ingestion"]["parsed_fields"]
    assert "/api/runtime/verification-automation/failure-summary/export" in contract["required_endpoints"]
    assert contract["local_history_comparison"]["status"] in {"insufficient_history", "stable", "changed"}
    assert "snapshot_count" in contract["local_history_comparison"]
    assert contract["quality_gates"]["backend_test_gate"] == "ready"
    assert contract["quality_gates"]["backend_test_count"] >= contract["quality_gates"]["minimum_backend_tests"]
    assert contract["quality_gates"]["endpoint_coverage_gate"] == "ready"
    assert contract["quality_gates"]["artifact_coverage_gate"] == "ready"
    assert contract["quality_gates"]["artifact_freshness_gate"] == "ready"
    assert contract["quality_gates"]["mutation_gate"] == "ready"
    assert contract["quality_gates"]["mutation_gate_coverage_ratio"] == 1
    assert contract["quality_gates"]["missing_mutation_gates"] == []
    assert "POST /api/audit/reviewer-decisions" in contract["quality_gates"]["mutation_gate_covered_endpoints"]
    assert "POST /api/artifacts/{artifact_id}/package-delivery" in contract["quality_gates"]["mutation_gate_covered_endpoints"]
    assert "POST /api/runtime/delivery-evidence-report/export" in contract["quality_gates"]["mutation_gate_covered_endpoints"]
    assert contract["artifact_freshness"]["status"] == "ready"
    assert contract["artifact_freshness"]["max_age_hours"] == 24
    assert contract["artifact_freshness"]["stale_artifacts"] == []
    assert "npm run verify" in contract["required_commands"]
    assert "py -3.11 tools/capture_frontend_screenshots.py" in contract["required_commands"]
    assert "py -3.11 tools/verify_governance_export_interaction.py" in contract["required_commands"]
    assert "py -3.11 tools/verify_delivery_governance_export_visual.py" in contract["required_commands"]
    assert "node tools/verify_command_center_export_click_smoke.mjs" in contract["required_commands"]
    assert "node tools/verify_command_center_keyboard_focus_smoke.mjs" in contract["required_commands"]
    assert "node tools/verify_command_center_responsive_navigation_smoke.mjs" in contract["required_commands"]
    assert "node tools/verify_command_center_responsive_action_panels_smoke.mjs" in contract["required_commands"]
    assert "node tools/verify_command_center_all_buttons_smoke.mjs" in contract["required_commands"]
    assert "py -3.11 tools/verify_ci_artifact_replay.py" in contract["required_commands"]
    assert "npm run verify:schema-diff" in contract["required_commands"]
    assert any(
        check["name"] == "ci_frontend_artifact_upload" and check["status"] == "ready"
        for check in contract["checks"]
    )
    assert any(
        check["name"] == "ci_frontend_artifact_retention" and check["status"] == "ready"
        for check in contract["checks"]
    )
    assert any(
        check["name"] == "ci_frontend_artifact_download" and check["status"] == "ready"
        for check in contract["checks"]
    )
    assert any(
        check["name"] == "ci_frontend_artifact_replay" and check["status"] == "ready"
        for check in contract["checks"]
    )
    assert contract["ci_artifact_retention"]["artifact_name"] == "mariam-frontend-regression-artifacts"
    assert contract["ci_artifact_retention"]["retention_days"] == 14
    assert contract["ci_artifact_retention"]["run_artifacts_url"].endswith("/actions/workflows/verify.yml")
    assert contract["ci_artifact_retention"]["download_path"].endswith(
        "mariam-frontend-regression-artifacts"
    )
    assert contract["ci_artifact_retention"]["replay_report"].endswith("ci-artifact-replay-report.json")
    assert "/api/runtime/api-error-contract" in contract["required_endpoints"]
    assert "/api/runtime/delivery-evidence-report" in contract["required_endpoints"]
    assert "/api/runtime/frontend/browser-screenshot-capture" in contract["required_endpoints"]
    assert "/api/runtime/frontend/visual-contract" in contract["required_endpoints"]
    assert "/api/runtime/frontend/browser-screenshot-plan" in contract["required_endpoints"]
    assert "/api/runtime/data-platform/communication-store/export" in contract["required_endpoints"]
    assert "/api/runtime/data-platform/document-store/export" in contract["required_endpoints"]
    assert "/api/runtime/data-platform/workflow-store/export" in contract["required_endpoints"]
    assert "/api/runtime/data-platform/capability-graph-store/export" in contract["required_endpoints"]
    assert "/api/runtime/data-platform/vector-index-store/export" in contract["required_endpoints"]
    assert "/api/runtime/data-platform/artifact-store/export" in contract["required_endpoints"]
    assert "/api/audit/governance-assignment-history/export" in contract["required_endpoints"]
    assert "/api/audit/notification-routing-evidence/export" in contract["required_endpoints"]
    assert "artifacts/frontend-regression/command-center-browser-screenshot-plan.json" in contract["required_artifacts"]
    assert "artifacts/frontend-regression/command-center-browser-screenshot-capture.json" in contract["required_artifacts"]
    assert (
        "artifacts/frontend-regression/command-center-governance-export-interaction-smoke.json"
        in contract["required_artifacts"]
    )
    assert (
        "artifacts/frontend-regression/command-center-delivery-governance-export-visual-smoke.json"
        in contract["required_artifacts"]
    )
    assert (
        "artifacts/frontend-regression/command-center-export-button-click-smoke.json"
        in contract["required_artifacts"]
    )
    assert (
        "artifacts/frontend-regression/command-center-keyboard-focus-smoke.json"
        in contract["required_artifacts"]
    )
    assert (
        "artifacts/frontend-regression/command-center-responsive-navigation-smoke.json"
        in contract["required_artifacts"]
    )
    assert (
        "artifacts/frontend-regression/command-center-responsive-action-panels-smoke.json"
        in contract["required_artifacts"]
    )
    assert "artifacts/frontend-regression/command-center-all-buttons-smoke.json" in contract["required_artifacts"]
    assert (
        "artifacts/frontend-regression/command-center-export-click-smoke-governance-before.png"
        in contract["required_artifacts"]
    )
    assert (
        "artifacts/frontend-regression/command-center-export-click-smoke-after.png"
        in contract["required_artifacts"]
    )
    assert "artifacts/frontend-regression/desktop-command-center.png" in contract["required_artifacts"]
    assert "artifacts/ci-artifact-replay/ci-artifact-replay-report.json" in contract["required_artifacts"]
    assert "artifacts/verification/governed-write-api-schema-snapshots.json" in contract["required_artifacts"]
    assert "artifacts/verification/governed-write-api-schema-snapshots.sha256" in contract["required_artifacts"]
    assert "artifacts/verification/verification-automation-contract.json" in contract["required_artifacts"]
    assert "artifacts/verification/local-verification-runs.json" in contract["required_artifacts"]
    assert contract["artifact_path"].endswith("verification-automation-contract.json")
    assert contract["persisted_run_log_path"].endswith("local-verification-runs.json")
    assert isinstance(contract["persisted_verification_runs"], list)
    assert contract["persisted_verification_run_count"] == len(contract["persisted_verification_runs"])
    assert "ci_badge_metadata_ready" in [check["name"] for check in contract["checks"]]
    assert "latest_ci_run_polling_configured" in [check["name"] for check in contract["checks"]]
    assert "latest_ci_run_result_ingestion_ready" in [check["name"] for check in contract["checks"]]
    assert "verification_failure_summary_export_ready" in [check["name"] for check in contract["checks"]]
    assert "local_verification_history_comparison_ready" in [check["name"] for check in contract["checks"]]
    assert "persisted_local_verification_runs_ready" in [check["name"] for check in contract["checks"]]
    assert "minimum_backend_test_count_gate" in [check["name"] for check in contract["checks"]]
    assert "endpoint_coverage_quality_gate" in [check["name"] for check in contract["checks"]]
    assert "artifact_coverage_quality_gate" in [check["name"] for check in contract["checks"]]
    assert "artifact_freshness_quality_gate" in [check["name"] for check in contract["checks"]]
    assert "mutation_level_write_endpoint_gate" in [check["name"] for check in contract["checks"]]
    assert "command_center_keyboard_focus_smoke_included" in [check["name"] for check in contract["checks"]]
    assert "command_center_responsive_navigation_smoke_included" in [
        check["name"] for check in contract["checks"]
    ]
    assert "command_center_responsive_action_panels_smoke_included" in [
        check["name"] for check in contract["checks"]
    ]
    assert "command_center_all_buttons_smoke_included" in [check["name"] for check in contract["checks"]]
    assert "ci_frontend_artifact_replay" in [check["name"] for check in contract["checks"]]
    assert "governance_export_interaction_smoke_included" in [
        check["name"] for check in contract["checks"]
    ]
    assert "delivery_governance_export_visual_smoke_included" in [
        check["name"] for check in contract["checks"]
    ]
    assert "command_center_export_button_click_smoke_included" in [
        check["name"] for check in contract["checks"]
    ]
    assert "governed_write_schema_regression_snapshot_included" in [
        check["name"] for check in contract["checks"]
    ]
    assert "governed_write_schema_diff_gate_included" in [
        check["name"] for check in contract["checks"]
    ]
    assert (
        contract["next_ci_step"]
        == "Add browser-level failure-state screenshots for CI and local verification summary panels."
    )
    assert Path(contract["artifact_path"]).exists()
    assert Path(contract["persisted_run_log_path"]).exists()


def test_runtime_verification_failure_summary_export_packages_local_and_ci_failures() -> None:
    client = TestClient(create_app())

    response = client.post("/api/runtime/verification-automation/failure-summary/export", json={})

    assert response.status_code == 200
    export_package = response.json()["export_package"]
    assert export_package["status"] == "ready_for_review"
    assert export_package["data_platform"] == "DB MARIAM"
    assert export_package["package_manifest"]["title"] == "Mariam Verification Failure Summary"
    assert export_package["package_manifest"]["contains_secrets"] is False
    assert export_package["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert export_package["failure_summary"]["status"] == "ready"
    assert export_package["failure_summary"]["data_platform"] == "DB MARIAM"
    assert export_package["failure_summary"]["contains_secrets"] is False
    assert "ci_source" in export_package["failure_summary"]
    assert "latest_run" in export_package["failure_summary"]
    assert isinstance(export_package["failure_summary"]["blocked_checks"], list)
    assert "Run npm run verify" in " ".join(export_package["failure_summary"]["remediation_order"])


def test_runtime_verification_automation_compares_latest_two_local_snapshots() -> None:
    client = TestClient(create_app())

    first = client.post(
        "/api/runtime/verification-report/record",
        json={"actor_id": "history-verifier", "evidence": {"run_label": "first"}},
    ).json()["audit_record"]
    second = client.post(
        "/api/runtime/verification-report/record",
        json={"actor_id": "history-verifier", "evidence": {"run_label": "second"}},
    ).json()["audit_record"]

    response = client.get("/api/runtime/verification-automation")

    assert response.status_code == 200
    comparison = response.json()["local_history_comparison"]
    assert comparison["status"] == "stable"
    assert comparison["snapshot_count"] >= 2
    assert comparison["latest_snapshot_id"] == second["audit_id"]
    assert comparison["previous_snapshot_id"] == first["audit_id"]
    assert comparison["ready_checks_delta"] == 0
    assert comparison["verification_status_changed"] is False


def test_runtime_implementation_roadmap_can_be_exported_as_review_package() -> None:
    client = TestClient(create_app())

    response = client.post("/api/runtime/implementation-roadmap/export")

    assert response.status_code == 200
    export_package = response.json()["export_package"]
    assert export_package["export_id"].startswith("implementation-roadmap-export-")
    assert export_package["status"] == "ready_for_review"
    assert export_package["format"] == "json"
    assert export_package["data_platform"] == "DB MARIAM"
    assert export_package["package_manifest"]["roadmap_status"] == "ready_for_execution"
    assert export_package["package_manifest"]["first_priority_area"] == "Backend API foundation"
    assert export_package["package_manifest"]["item_count"] == len(export_package["roadmap"]["items"])


def test_data_platform_readiness_reports_db_mariam_boundaries() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/data-platform/readiness")

    assert response.status_code == 200
    readiness = response.json()
    assert readiness["title"] == "DB MARIAM Data Platform Readiness"
    assert readiness["status"] == "ready"
    assert readiness["database_name"] == "DB MARIAM"
    assert "***" in readiness["database_url"]
    assert "mariam:mariam" not in readiness["database_url"]
    assert "0001_initial.sql" in readiness["migrations_found"]
    assert {"missions", "artifacts", "delivery_packages", "audit_log"}.issubset(
        set(readiness["expected_tables"])
    )
    assert {
        "communication_records",
        "document_records",
        "workflow_records",
        "capability_graph_records",
        "vector_index_records",
        "artifact_store_records",
        "audit_event_archive_records",
        "metrics_store_records",
        "logs_store_records",
        "artifact_lineage_records",
        "reviewer_queue_assignments",
        "governance_sla_escalations",
        "reviewer_decision_outcomes",
    }.issubset(set(readiness["expected_tables"]))
    assert all(check["status"] == "ready" for check in readiness["checks"])


def test_data_platform_readiness_can_be_exported_without_secrets() -> None:
    client = TestClient(create_app())

    response = client.post("/api/runtime/data-platform/readiness/export")

    assert response.status_code == 200
    export_package = response.json()["export_package"]
    assert export_package["export_id"].startswith("data-platform-readiness-export-")
    assert export_package["status"] == "ready_for_review"
    assert export_package["format"] == "json"
    assert export_package["data_platform"] == "DB MARIAM"
    assert export_package["package_manifest"]["readiness_status"] == "ready"
    assert export_package["package_manifest"]["secrets_masked"] is True
    assert export_package["package_manifest"]["expected_table_count"] == len(
        export_package["readiness"]["expected_tables"]
    )
    assert "mariam:mariam" not in export_package["readiness"]["database_url"]


def test_data_platform_migration_runner_reports_ordered_migrations() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/data-platform/migration-runner")

    assert response.status_code == 200
    status = response.json()
    assert status["title"] == "DB MARIAM Migration Runner Status"
    assert status["status"] == "ready"
    assert status["data_platform"] == "DB MARIAM"
    assert status["migration_count"] >= 6
    assert status["ordered_migrations"][0] == "0001_initial.sql"
    assert status["table_definitions"] >= 10
    assert status["index_definitions"] >= 1
    assert all(check["status"] == "ready" for check in status["checks"])


def test_data_platform_migration_runner_can_be_exported_for_review() -> None:
    client = TestClient(create_app())

    response = client.post("/api/runtime/data-platform/migration-runner/export")

    assert response.status_code == 200
    export_package = response.json()["export_package"]
    assert export_package["export_id"].startswith("migration-runner-export-")
    assert export_package["status"] == "ready_for_review"
    assert export_package["format"] == "json"
    assert export_package["data_platform"] == "DB MARIAM"
    assert export_package["package_manifest"]["runner_status"] == "ready"
    assert export_package["package_manifest"]["first_migration"] == "0001_initial.sql"
    assert export_package["package_manifest"]["migration_count"] == len(
        export_package["migration_runner"]["ordered_migrations"]
    )


def test_data_platform_seed_data_status_reports_non_secret_seed_manifest() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/data-platform/seed-data")

    assert response.status_code == 200
    status = response.json()
    assert status["title"] == "DB MARIAM Seed Data Status"
    assert status["status"] == "ready"
    assert status["data_platform"] == "DB MARIAM"
    assert status["seed_id"] == "db-mariam-core-seed-v1"
    assert status["contains_secrets"] is False
    assert status["item_count"] >= 3
    assert "plugin_manifests" in status["target_tables"]
    assert all(check["status"] == "ready" for check in status["checks"])


def test_data_platform_backup_readiness_reports_governed_policy() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/data-platform/backup-readiness")

    assert response.status_code == 200
    status = response.json()
    assert status["title"] == "DB MARIAM Backup Readiness"
    assert status["status"] == "ready"
    assert status["data_platform"] == "DB MARIAM"
    assert status["policy_id"] == "db-mariam-backup-policy-v1"
    assert status["contains_secrets"] is False
    assert status["scope_count"] >= 10
    assert status["retention"]["production_daily"] == "30 days"
    assert all(check["status"] == "ready" for check in status["checks"])


def test_data_platform_plugin_schema_isolation_reports_crm_boundary() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/data-platform/plugin-schema-isolation")

    assert response.status_code == 200
    status = response.json()
    assert status["title"] == "DB MARIAM Plugin Schema Isolation"
    assert status["status"] == "ready"
    assert status["data_platform"] == "DB MARIAM"
    assert status["manifest_id"] == "db-mariam-plugin-schema-isolation-v1"
    assert status["contains_secrets"] is False
    assert status["plugin_schema_count"] >= 1
    assert status["shared_table_count"] >= 3
    assert status["private_table_count"] >= 5
    assert all(check["status"] == "ready" for check in status["checks"])


def test_data_platform_docker_persistence_reports_postgres_profile() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/data-platform/docker-persistence")

    assert response.status_code == 200
    status = response.json()
    assert status["title"] == "DB MARIAM Docker Persistence Profile"
    assert status["status"] == "ready"
    assert status["data_platform"] == "DB MARIAM"
    assert status["postgres_store_count"] == 9
    assert "***" in status["database_url_masked"]
    assert "mariam:mariam" not in status["database_url_masked"]
    assert all(check["status"] == "ready" for check in status["checks"])


def test_data_platform_live_database_smoke_reports_docker_readiness() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/data-platform/live-db-smoke")

    assert response.status_code == 200
    status = response.json()
    assert status["title"] == "DB MARIAM Live Database Smoke Readiness"
    assert status["status"] == "ready"
    assert status["data_platform"] == "DB MARIAM"
    assert status["docker_available"] is True
    assert status["compose_config_valid"] is True
    assert "pg_isready" in status["smoke_command"]
    assert all(check["status"] == "ready" for check in status["checks"])


def test_data_platform_docker_container_execution_reports_running_postgres() -> None:
    client = TestClient(create_app())

    response = client.get("/api/runtime/data-platform/docker-container-execution")

    assert response.status_code == 200
    status = response.json()
    assert status["title"] == "DB MARIAM Docker Container Execution Verification"
    assert status["status"] == "ready"
    assert status["data_platform"] == "DB MARIAM"
    assert status["postgres_running"] is True
    assert status["pg_isready"] is True
    assert "postgres" in status["services"]
    assert "docker compose up -d postgres" in status["execution_commands"]
    assert any(check["name"] == "postgres_pg_isready" for check in status["checks"])


def test_data_platform_live_write_smoke_writes_audit_and_event_records() -> None:
    client = TestClient(create_app())

    response = client.post("/api/runtime/data-platform/live-write-smoke")

    assert response.status_code == 200
    status = response.json()
    assert status["title"] == "DB MARIAM Live Database Write Verification"
    assert status["status"] == "ready"
    assert status["data_platform"] == "DB MARIAM"
    assert status["audit_written"] is True
    assert status["event_written"] is True
    assert status["audit_id"]
    assert status["event_id"]
    assert all(check["status"] == "ready" for check in status["checks"])


def test_data_platform_live_repository_write_smoke_writes_core_repositories() -> None:
    client = TestClient(create_app())

    response = client.post("/api/runtime/data-platform/live-repository-write-smoke")

    assert response.status_code == 200
    status = response.json()
    assert status["title"] == "DB MARIAM Live Repository Write Verification"
    assert status["status"] == "ready"
    assert status["data_platform"] == "DB MARIAM"
    assert status["mission_written"] is True
    assert status["artifact_written"] is True
    assert status["delivery_written"] is True
    assert status["plugin_written"] is True
    assert status["runtime_object_written"] is True
    assert status["ai_resource_route_written"] is True
    assert status["quality_review_written"] is True
    assert status["communication_record_written"] is True
    assert status["document_record_written"] is True
    assert status["workflow_record_written"] is True
    assert status["capability_graph_record_written"] is True
    assert status["vector_index_record_written"] is True
    assert status["artifact_store_record_written"] is True
    assert status["audit_event_archive_record_written"] is True
    assert status["metrics_store_record_written"] is True
    assert status["logs_store_record_written"] is True
    assert status["artifact_lineage_record_written"] is True
    assert status["mission_id"]
    assert status["artifact_id"]
    assert status["delivery_id"]
    assert status["plugin_id"].startswith("repository-smoke-")
    assert status["runtime_object_id"]
    assert status["ai_resource_route_id"]
    assert status["quality_review_id"]
    assert status["communication_record_id"]
    assert status["document_record_id"]
    assert status["workflow_record_id"]
    assert status["capability_graph_record_id"]
    assert status["vector_index_record_id"]
    assert status["artifact_store_record_id"]
    assert status["audit_event_archive_record_id"]
    assert status["metrics_store_record_id"]
    assert status["logs_store_record_id"]
    assert status["artifact_lineage_record_id"]
    assert "live_ai_resource_route_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_artifact_quality_review_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_communication_record_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_document_record_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_workflow_record_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_capability_graph_record_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_vector_index_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_artifact_store_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_audit_event_archive_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_metrics_store_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_logs_store_repository_write" in [check["name"] for check in status["checks"]]
    assert "live_artifact_lineage_repository_write" in [check["name"] for check in status["checks"]]
    assert all(check["status"] == "ready" for check in status["checks"])


def test_data_platform_evidence_store_read_apis_return_recent_records() -> None:
    client = TestClient(create_app())

    smoke_response = client.post("/api/runtime/data-platform/live-repository-write-smoke")
    smoke = smoke_response.json()

    logs_response = client.get("/api/runtime/data-platform/logs-store")
    audit_archive_response = client.get("/api/runtime/data-platform/audit-event-archive")
    metrics_store_response = client.get("/api/runtime/data-platform/metrics-store")
    lineage_response = client.get("/api/runtime/data-platform/artifact-lineage")
    data_record_store_responses = {
        "communication-store": client.get("/api/runtime/data-platform/communication-store"),
        "document-store": client.get("/api/runtime/data-platform/document-store"),
        "workflow-store": client.get("/api/runtime/data-platform/workflow-store"),
        "capability-graph-store": client.get("/api/runtime/data-platform/capability-graph-store"),
        "vector-index-store": client.get("/api/runtime/data-platform/vector-index-store"),
        "artifact-store": client.get("/api/runtime/data-platform/artifact-store"),
    }

    assert smoke_response.status_code == 200
    assert smoke["status"] == "ready"
    assert logs_response.status_code == 200
    assert audit_archive_response.status_code == 200
    assert metrics_store_response.status_code == 200
    assert lineage_response.status_code == 200
    assert all(response.status_code == 200 for response in data_record_store_responses.values())
    logs_status = logs_response.json()
    audit_archive_status = audit_archive_response.json()
    metrics_store_status = metrics_store_response.json()
    lineage_status = lineage_response.json()
    assert logs_status["title"] == "DB MARIAM Logs Store Read API"
    assert logs_status["status"] == "ready"
    assert logs_status["data_platform"] == "DB MARIAM"
    assert logs_status["record_count"] >= 1
    assert smoke["logs_store_record_id"] in [record["log_id"] for record in logs_status["records"]]
    log_record = next(
        record for record in logs_status["records"] if record["log_id"] == smoke["logs_store_record_id"]
    )
    assert log_record["source"] == "db-mariam-repository-smoke"
    assert log_record["context"]["verification"] == "repository-write-smoke"
    assert all(check["status"] == "ready" for check in logs_status["checks"])
    assert audit_archive_status["title"] == "DB MARIAM Audit Event Archive Read API"
    assert audit_archive_status["status"] == "ready"
    assert audit_archive_status["data_platform"] == "DB MARIAM"
    assert audit_archive_status["record_count"] >= 1
    assert smoke["audit_event_archive_record_id"] in [
        record["archive_id"] for record in audit_archive_status["records"]
    ]
    audit_archive_record = next(
        record
        for record in audit_archive_status["records"]
        if record["archive_id"] == smoke["audit_event_archive_record_id"]
    )
    assert audit_archive_record["target_id"] == smoke["artifact_id"]
    assert audit_archive_record["actor_id"] == "db-mariam-repository-smoke"
    assert audit_archive_record["payload"]["verification"] == "repository-write-smoke"
    assert all(check["status"] == "ready" for check in audit_archive_status["checks"])
    assert metrics_store_status["title"] == "DB MARIAM Metrics Store Read API"
    assert metrics_store_status["status"] == "ready"
    assert metrics_store_status["data_platform"] == "DB MARIAM"
    assert metrics_store_status["record_count"] >= 1
    assert smoke["metrics_store_record_id"] in [
        record["metric_id"] for record in metrics_store_status["records"]
    ]
    metrics_store_record = next(
        record
        for record in metrics_store_status["records"]
        if record["metric_id"] == smoke["metrics_store_record_id"]
    )
    assert metrics_store_record["metric_name"] == "db_mariam.repository_write_smoke.ready_records"
    assert metrics_store_record["source"] == "db-mariam-repository-smoke"
    assert metrics_store_record["dimensions"]["verification"] == "repository-write-smoke"
    assert all(check["status"] == "ready" for check in metrics_store_status["checks"])
    assert lineage_status["title"] == "DB MARIAM Artifact Lineage Read API"
    assert lineage_status["status"] == "ready"
    assert lineage_status["data_platform"] == "DB MARIAM"
    assert lineage_status["record_count"] >= 1
    assert smoke["artifact_lineage_record_id"] in [
        record["lineage_id"] for record in lineage_status["records"]
    ]
    lineage_record = next(
        record
        for record in lineage_status["records"]
        if record["lineage_id"] == smoke["artifact_lineage_record_id"]
    )
    assert lineage_record["artifact_id"] == smoke["artifact_id"]
    assert lineage_record["mission_id"] == smoke["mission_id"]
    assert lineage_record["lineage_metadata"]["verification"] == "repository-write-smoke"
    assert all(check["status"] == "ready" for check in lineage_status["checks"])
    data_record_store_checks = {
        "communication-store": ("communication_record_id", "record_id", "communication_records"),
        "document-store": ("document_record_id", "document_id", "document_records"),
        "workflow-store": ("workflow_record_id", "workflow_id", "workflow_records"),
        "capability-graph-store": ("capability_graph_record_id", "capability_id", "capability_graph_records"),
        "vector-index-store": ("vector_index_record_id", "vector_id", "vector_index_records"),
        "artifact-store": ("artifact_store_record_id", "store_id", "artifact_store_records"),
    }
    for store_name, (smoke_key, record_key, table_name) in data_record_store_checks.items():
        status = data_record_store_responses[store_name].json()
        assert status["title"] == f"DB MARIAM {store_name.title()} Read API"
        assert status["status"] == "ready"
        assert status["data_platform"] == "DB MARIAM"
        assert status["store_name"] == store_name
        assert status["table_name"] == table_name
        assert status["record_count"] >= 1
        assert smoke[smoke_key] in [record[record_key] for record in status["records"]]
        assert all(check["status"] == "ready" for check in status["checks"])


def test_data_platform_evidence_stores_can_be_exported_for_review() -> None:
    client = TestClient(create_app())

    smoke_response = client.post("/api/runtime/data-platform/live-repository-write-smoke")
    smoke = smoke_response.json()

    audit_export_response = client.post("/api/runtime/data-platform/audit-event-archive/export")
    metrics_export_response = client.post("/api/runtime/data-platform/metrics-store/export")
    logs_export_response = client.post("/api/runtime/data-platform/logs-store/export")
    lineage_export_response = client.post("/api/runtime/data-platform/artifact-lineage/export")
    data_record_store_export_responses = {
        "communication-store": client.post("/api/runtime/data-platform/communication-store/export"),
        "document-store": client.post("/api/runtime/data-platform/document-store/export"),
        "workflow-store": client.post("/api/runtime/data-platform/workflow-store/export"),
        "capability-graph-store": client.post("/api/runtime/data-platform/capability-graph-store/export"),
        "vector-index-store": client.post("/api/runtime/data-platform/vector-index-store/export"),
        "artifact-store": client.post("/api/runtime/data-platform/artifact-store/export"),
    }

    assert smoke_response.status_code == 200
    assert smoke["status"] == "ready"
    assert audit_export_response.status_code == 200
    assert metrics_export_response.status_code == 200
    assert logs_export_response.status_code == 200
    assert lineage_export_response.status_code == 200
    assert all(response.status_code == 200 for response in data_record_store_export_responses.values())
    audit_export = audit_export_response.json()["export_package"]
    metrics_export = metrics_export_response.json()["export_package"]
    logs_export = logs_export_response.json()["export_package"]
    lineage_export = lineage_export_response.json()["export_package"]
    assert audit_export["export_id"].startswith("audit-event-archive-export-")
    assert audit_export["status"] == "ready_for_review"
    assert audit_export["format"] == "json"
    assert audit_export["data_platform"] == "DB MARIAM"
    assert audit_export["package_manifest"]["record_count"] >= 1
    assert audit_export["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert audit_export["package_manifest"]["contains_secrets"] is False
    assert audit_export["audit_event_archive"]["status"] == "ready"
    assert smoke["audit_event_archive_record_id"] in [
        record["archive_id"] for record in audit_export["audit_event_archive"]["records"]
    ]
    assert metrics_export["export_id"].startswith("metrics-store-export-")
    assert metrics_export["status"] == "ready_for_review"
    assert metrics_export["format"] == "json"
    assert metrics_export["data_platform"] == "DB MARIAM"
    assert metrics_export["package_manifest"]["record_count"] >= 1
    assert metrics_export["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert metrics_export["package_manifest"]["contains_secrets"] is False
    assert metrics_export["metrics_store"]["status"] == "ready"
    assert smoke["metrics_store_record_id"] in [
        record["metric_id"] for record in metrics_export["metrics_store"]["records"]
    ]
    assert logs_export["export_id"].startswith("logs-store-export-")
    assert logs_export["status"] == "ready_for_review"
    assert logs_export["format"] == "json"
    assert logs_export["data_platform"] == "DB MARIAM"
    assert logs_export["package_manifest"]["record_count"] >= 1
    assert logs_export["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert logs_export["package_manifest"]["contains_secrets"] is False
    assert logs_export["logs_store"]["status"] == "ready"
    assert smoke["logs_store_record_id"] in [
        record["log_id"] for record in logs_export["logs_store"]["records"]
    ]
    assert lineage_export["export_id"].startswith("artifact-lineage-export-")
    assert lineage_export["status"] == "ready_for_review"
    assert lineage_export["format"] == "json"
    assert lineage_export["data_platform"] == "DB MARIAM"
    assert lineage_export["package_manifest"]["record_count"] >= 1
    assert lineage_export["package_manifest"]["requires_governance_review_before_external_delivery"] is True
    assert lineage_export["package_manifest"]["contains_secrets"] is False
    assert lineage_export["artifact_lineage"]["status"] == "ready"
    assert smoke["artifact_lineage_record_id"] in [
        record["lineage_id"] for record in lineage_export["artifact_lineage"]["records"]
    ]
    data_record_store_export_checks = {
        "communication-store": ("communication_record_id", "record_id", "communication_records"),
        "document-store": ("document_record_id", "document_id", "document_records"),
        "workflow-store": ("workflow_record_id", "workflow_id", "workflow_records"),
        "capability-graph-store": ("capability_graph_record_id", "capability_id", "capability_graph_records"),
        "vector-index-store": ("vector_index_record_id", "vector_id", "vector_index_records"),
        "artifact-store": ("artifact_store_record_id", "store_id", "artifact_store_records"),
    }
    for store_name, (smoke_key, record_key, table_name) in data_record_store_export_checks.items():
        export_package = data_record_store_export_responses[store_name].json()["export_package"]
        assert export_package["export_id"].startswith(f"{store_name}-export-")
        assert export_package["status"] == "ready_for_review"
        assert export_package["format"] == "json"
        assert export_package["data_platform"] == "DB MARIAM"
        assert export_package["package_manifest"]["store_name"] == store_name
        assert export_package["package_manifest"]["table_name"] == table_name
        assert export_package["package_manifest"]["record_count"] >= 1
        assert export_package["package_manifest"]["requires_governance_review_before_external_delivery"] is True
        assert export_package["package_manifest"]["contains_secrets"] is False
        assert export_package["store"]["status"] == "ready"
        assert smoke[smoke_key] in [record[record_key] for record in export_package["store"]["records"]]


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


def test_artifact_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    artifact_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0004_artifact_storage.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    artifact_upgrade = artifact_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS artifacts" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "idx_artifacts_mission_status" in migration
    assert "CREATE TABLE IF NOT EXISTS artifacts" in artifact_upgrade
    assert "mission_id UUID NOT NULL REFERENCES missions" in artifact_upgrade


def test_delivery_package_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    delivery_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0005_delivery_package_storage.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    delivery_upgrade = delivery_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS delivery_packages" in migration
    assert "package_manifest JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "idx_delivery_packages_plugin_status" in migration
    assert "CREATE TABLE IF NOT EXISTS delivery_packages" in delivery_upgrade
    assert "artifact_id UUID NOT NULL REFERENCES artifacts" in delivery_upgrade


def test_artifact_quality_review_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    quality_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0006_artifact_quality_review_storage.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    quality_upgrade = quality_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS artifact_quality_reviews" in migration
    assert "checks JSONB NOT NULL DEFAULT '[]'::jsonb" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "idx_artifact_quality_reviews_artifact_created" in migration
    assert "CREATE TABLE IF NOT EXISTS artifact_quality_reviews" in quality_upgrade
    assert "artifact_id UUID NOT NULL REFERENCES artifacts" in quality_upgrade


def test_communication_and_document_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    upgrade_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0007_communication_document_storage.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    upgrade = upgrade_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS communication_records" in migration
    assert "CREATE TABLE IF NOT EXISTS document_records" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "metadata JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "idx_communication_records_channel_created" in migration
    assert "idx_document_records_type_created" in migration
    assert "CREATE TABLE IF NOT EXISTS communication_records" in upgrade
    assert "CREATE TABLE IF NOT EXISTS document_records" in upgrade
    assert "artifact_id UUID REFERENCES artifacts" in upgrade


def test_workflow_and_capability_graph_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    upgrade_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0008_workflow_capability_graph_storage.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    upgrade = upgrade_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS workflow_records" in migration
    assert "CREATE TABLE IF NOT EXISTS capability_graph_records" in migration
    assert "steps JSONB NOT NULL DEFAULT '[]'::jsonb" in migration
    assert "nodes JSONB NOT NULL DEFAULT '[]'::jsonb" in migration
    assert "edges JSONB NOT NULL DEFAULT '[]'::jsonb" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "idx_workflow_records_plugin_created" in migration
    assert "idx_capability_graph_records_type_created" in migration
    assert "CREATE TABLE IF NOT EXISTS workflow_records" in upgrade
    assert "CREATE TABLE IF NOT EXISTS capability_graph_records" in upgrade


def test_vector_index_and_artifact_store_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    upgrade_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0009_vector_artifact_store_records.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    upgrade = upgrade_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS vector_index_records" in migration
    assert "CREATE TABLE IF NOT EXISTS artifact_store_records" in migration
    assert "vector_metadata JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "metadata JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "idx_vector_index_records_namespace_created" in migration
    assert "idx_artifact_store_records_provider_created" in migration
    assert "CREATE TABLE IF NOT EXISTS vector_index_records" in upgrade
    assert "CREATE TABLE IF NOT EXISTS artifact_store_records" in upgrade
    assert "artifact_id UUID REFERENCES artifacts" in upgrade


def test_audit_archive_and_metrics_store_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    upgrade_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0011_audit_archive_metrics_store.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    upgrade = upgrade_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS audit_event_archive_records" in migration
    assert "CREATE TABLE IF NOT EXISTS metrics_store_records" in migration
    assert "payload JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "dimensions JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "DOUBLE PRECISION" in migration
    assert "idx_audit_event_archive_records_target_created" in migration
    assert "idx_metrics_store_records_name_created" in migration
    assert "CREATE TABLE IF NOT EXISTS audit_event_archive_records" in upgrade
    assert "CREATE TABLE IF NOT EXISTS metrics_store_records" in upgrade
    assert "event_id UUID REFERENCES runtime_events" in upgrade


def test_logs_store_and_artifact_lineage_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    upgrade_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0013_logs_store_artifact_lineage.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    upgrade = upgrade_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS logs_store_records" in migration
    assert "CREATE TABLE IF NOT EXISTS artifact_lineage_records" in migration
    assert "context JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "lineage_metadata JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "idx_logs_store_records_source_created" in migration
    assert "idx_artifact_lineage_records_artifact_created" in migration
    assert "CREATE TABLE IF NOT EXISTS logs_store_records" in upgrade
    assert "CREATE TABLE IF NOT EXISTS artifact_lineage_records" in upgrade
    assert "artifact_id UUID REFERENCES artifacts" in upgrade


def test_data_record_repositories_are_explicit_abstractions() -> None:
    root = Path(__file__).resolve().parents[2]
    backend_root = root / "backend"
    repository_source = (backend_root / "app" / "repositories" / "data_records.py").read_text(
        encoding="utf-8"
    )
    core_source = (backend_root / "app" / "core" / "data_records.py").read_text(encoding="utf-8")
    command_center_source = (
        backend_root / "app" / "services" / "command_center.py"
    ).read_text(encoding="utf-8")

    assert "class CommunicationRecordRepository" in repository_source
    assert "class DocumentRecordRepository" in repository_source
    assert "class WorkflowRecordRepository" in repository_source
    assert "class CapabilityGraphRecordRepository" in repository_source
    assert "class VectorIndexRecordRepository" in repository_source
    assert "class ArtifactStoreRecordRepository" in repository_source
    assert "class AuditEventArchiveRecordRepository" in repository_source
    assert "class MetricsStoreRecordRepository" in repository_source
    assert "class LogsStoreRecordRepository" in repository_source
    assert "class ArtifactLineageRecordRepository" in repository_source
    assert "class CursorCommunicationRecordRepository" in repository_source
    assert "class CursorDocumentRecordRepository" in repository_source
    assert "class CursorWorkflowRecordRepository" in repository_source
    assert "class CursorCapabilityGraphRecordRepository" in repository_source
    assert "class CursorVectorIndexRecordRepository" in repository_source
    assert "class CursorArtifactStoreRecordRepository" in repository_source
    assert "class CursorAuditEventArchiveRecordRepository" in repository_source
    assert "class CursorMetricsStoreRecordRepository" in repository_source
    assert "class CursorLogsStoreRecordRepository" in repository_source
    assert "class CursorArtifactLineageRecordRepository" in repository_source
    assert "class CommunicationRecord" in core_source
    assert "class DocumentRecord" in core_source
    assert "class WorkflowRecord" in core_source
    assert "class CapabilityGraphRecord" in core_source
    assert "class VectorIndexRecord" in core_source
    assert "class ArtifactStoreRecord" in core_source
    assert "class AuditEventArchiveRecord" in core_source
    assert "class MetricsStoreRecord" in core_source
    assert "class LogsStoreRecord" in core_source
    assert "class ArtifactLineageRecord" in core_source
    assert "CursorCommunicationRecordRepository(cursor)" in command_center_source
    assert "CursorDocumentRecordRepository(cursor)" in command_center_source
    assert "CursorWorkflowRecordRepository(cursor)" in command_center_source
    assert "CursorCapabilityGraphRecordRepository(cursor)" in command_center_source
    assert "CursorVectorIndexRecordRepository(cursor)" in command_center_source
    assert "CursorArtifactStoreRecordRepository(cursor)" in command_center_source
    assert "CursorAuditEventArchiveRecordRepository(cursor)" in command_center_source
    assert "CursorMetricsStoreRecordRepository(cursor)" in command_center_source
    assert "CursorLogsStoreRecordRepository(cursor)" in command_center_source
    assert "CursorArtifactLineageRecordRepository(cursor)" in command_center_source


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


def test_governance_assignment_history_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    upgrade_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0010_governance_assignment_history.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    upgrade = upgrade_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS reviewer_queue_assignments" in migration
    assert "CREATE TABLE IF NOT EXISTS governance_sla_escalations" in migration
    assert "CREATE TABLE IF NOT EXISTS reviewer_decision_outcomes" in migration
    assert "audit_id UUID REFERENCES audit_log" in migration
    assert "assignment_id UUID REFERENCES reviewer_queue_assignments" in migration
    assert "evidence JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "data_platform TEXT NOT NULL DEFAULT 'DB MARIAM'" in migration
    assert "idx_reviewer_queue_assignments_reviewer_created" in migration
    assert "idx_governance_sla_escalations_reviewer_created" in migration
    assert "idx_reviewer_decision_outcomes_reviewer_created" in migration
    assert "CREATE TABLE IF NOT EXISTS reviewer_queue_assignments" in upgrade
    assert "CREATE TABLE IF NOT EXISTS governance_sla_escalations" in upgrade


def test_reviewer_decision_outcomes_schema_targets_db_mariam() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial.sql"
    upgrade_path = (
        Path(__file__).resolve().parents[2]
        / "database"
        / "migrations"
        / "0012_reviewer_decision_outcomes.sql"
    )
    migration = migration_path.read_text(encoding="utf-8")
    upgrade = upgrade_path.read_text(encoding="utf-8")

    assert "CREATE TABLE IF NOT EXISTS reviewer_decision_outcomes" in migration
    assert "decision_id UUID PRIMARY KEY" in migration
    assert "assignment_id UUID REFERENCES reviewer_queue_assignments" in migration
    assert "evidence JSONB NOT NULL DEFAULT '{}'::jsonb" in migration
    assert "idx_reviewer_decision_outcomes_target_created" in migration
    assert "CREATE TABLE IF NOT EXISTS reviewer_decision_outcomes" in upgrade
    assert "idx_reviewer_decision_outcomes_reviewer_created" in upgrade
