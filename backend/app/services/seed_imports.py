import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.plugin_manifest import PluginManifest
from app.core.seed_imports import (
    ExternalSeedSource,
    SeedDomainEvidence,
    SeedImportRecord,
    SeedImportRequest,
    SeedPluginCandidate,
    SeedPluginPromotionRequest,
    create_seed_import_record,
)
from app.repositories.seed_imports import SeedImportRepository
from app.services.audit import AuditService
from app.services.runtime import RuntimeRegistry


CANONICAL_PLUGIN_GROUPS = {
    "plugin_mcp_runtime_manager": {
        "name": "MCP Runtime Manager",
        "domains": ["mcp", "tools", "apis", "connectors", "api_gateways"],
        "features": [
            "MCP server registry",
            "MCP tool registry",
            "Connector/API discovery",
            "Permissioned tool execution",
            "Health and readiness checks",
        ],
    },
    "plugin_model_provider_manager": {
        "name": "Model Provider Manager",
        "domains": ["model_providers", "model_serving", "llm", "slm", "vlm", "inference_engines", "embeddings"],
        "features": [
            "Ollama/API provider registration",
            "GGUF/ONNX/SafeTensors model route candidates",
            "Embedding and multimodal capability detection",
            "Provider health and benchmark evidence",
        ],
    },
    "plugin_agent_society_manager": {
        "name": "Agent Society Manager",
        "domains": ["agents", "roles", "departments", "workers", "skills", "capabilities"],
        "features": [
            "Chief, department, specialist, worker, review, and report agent maps",
            "Skill and capability assignment evidence",
            "Delegation and approval flow seeds",
        ],
    },
    "plugin_workflow_engine_manager": {
        "name": "Workflow Engine Manager",
        "domains": ["workflows", "processes", "event_streaming", "async_runtimes"],
        "features": [
            "Workflow registry ingestion",
            "Task map extraction",
            "Trigger map extraction",
            "Recovery and evaluation gate mapping",
        ],
    },
    "plugin_knowledge_engine_manager": {
        "name": "Knowledge Engine Manager",
        "domains": ["knowledge_graph", "memory", "rag", "vector_databases", "datasets", "documents", "pdf", "office"],
        "features": [
            "Knowledge graph seed registration",
            "Memory/RAG domain evidence",
            "Vector index candidate creation",
            "Document and file knowledge routing",
        ],
    },
    "plugin_security_governance_manager": {
        "name": "Security Governance Manager",
        "domains": ["security", "cybersecurity", "rbac", "policies", "governance", "audit", "compliance"],
        "features": [
            "RBAC and policy evidence",
            "Governance gate candidates",
            "Audit and compliance source mapping",
            "Security review workflow seeds",
        ],
    },
    "plugin_infrastructure_runtime_manager": {
        "name": "Infrastructure Runtime Manager",
        "domains": ["docker", "kubernetes", "devops", "deployment", "monitoring", "logging", "storage", "databases"],
        "features": [
            "Container/runtime target evidence",
            "Storage and database runtime candidates",
            "Monitoring/logging readiness",
            "Deployment and DevOps patterns",
        ],
    },
    "plugin_business_crm_manager": {
        "name": "Business CRM Manager",
        "domains": ["crm", "sales", "business", "saas"],
        "features": [
            "CRM and sales domain evidence",
            "Business workflow candidates",
            "Plugin-managed business unit seeds",
        ],
    },
    "plugin_video_generation_manager": {
        "name": "Video Generation Manager",
        "domains": ["video_generation", "media", "voice", "subtitle", "material", "upload_post"],
        "features": [
            "Short video generation workflow",
            "Script, terms, materials, voice, subtitle, and composition pipeline",
            "WebUI/API task orchestration",
            "Stock media provider and publishing connector candidates",
        ],
    },
    "plugin_gguf_model_catalog_manager": {
        "name": "GGUF Model Catalog Manager",
        "domains": ["gguf", "model_providers", "model_serving", "llm", "embeddings"],
        "features": [
            "HuggingFace GGUF model discovery",
            "GGUF provider candidate registration",
            "llama.cpp/llamafile runtime compatibility review",
            "Model metadata, quantization, license, and safety review candidates",
        ],
    },
}


EXTERNAL_SEED_SOURCES = {
    "moneyprinterturbo": ExternalSeedSource(
        source_key="moneyprinterturbo",
        name="MoneyPrinterTurbo",
        source_type="github_repository",
        url="https://github.com/harry0703/MoneyPrinterTurbo",
        target_plugins=[
            "plugin_video_generation_manager",
            "plugin_model_provider_manager",
            "plugin_mcp_runtime_manager",
            "plugin_security_governance_manager",
        ],
        extracted_dna_domains=[
            "video_generation",
            "workflow_engine",
            "api_service",
            "webui",
            "llm_provider_registry",
            "media_material_connectors",
            "voice_subtitle_pipeline",
            "task_queue",
            "file_security",
            "docker_runtime",
        ],
        integration_notes=[
            "Import as idea/DNA only; do not copy application code into Mariam core.",
            "Map video generation to a Plugin-managed Business Unit with Chief, swarm, dashboard, settings, and API boundary.",
            "Map Kimi/OpenAI/Gemini/Ollama and compatible providers to the Model Provider Manager.",
            "Map Pexels/Pixabay/Coverr/TwelveLabs as connector/provider candidates requiring user credentials.",
        ],
        security_notes=[
            "Do not import API keys, generated videos, uploaded materials, or runtime task data.",
            "Keep generated media tasks sandboxed and governed before client delivery.",
            "Review external media licenses before artifact approval.",
        ],
        traceability={
            "files_inspected": [
                "README-en.md",
                "config.example.toml",
                "docker-compose.yml",
                "app/router.py",
                "app/controllers/v1/video.py",
                "app/services/task.py",
                "app/services/llm.py",
            ],
            "source_evidence": "GitHub page describes automated script/material/subtitle/music/video generation with WebUI and API.",
        },
    ),
    "huggingface-gguf": ExternalSeedSource(
        source_key="huggingface-gguf",
        name="HuggingFace GGUF Model Library",
        source_type="model_catalog",
        url="https://huggingface.co/models?library=gguf",
        target_plugins=[
            "plugin_gguf_model_catalog_manager",
            "plugin_model_provider_manager",
            "plugin_security_governance_manager",
        ],
        extracted_dna_domains=[
            "gguf_models",
            "model_provider_registry",
            "model_runtime_compatibility",
            "quantization_metadata",
            "license_review",
            "model_safety_review",
        ],
        integration_notes=[
            "Treat GGUF entries as model provider candidates, not as Mariam core code.",
            "Require metadata extraction before activation: model id, files, quantization, context, license, size, and runtime compatibility.",
            "Route execution through Ollama/llama.cpp/llamafile-compatible runtimes after governance approval.",
        ],
        security_notes=[
            "Do not auto-download model weights during catalog inspection.",
            "Require license, malware, checksum, and sandbox checks before model activation.",
            "Keep model activation disabled until provider/runtime compatibility is validated.",
        ],
        traceability={
            "source_evidence": "HuggingFace model catalog filtered by library=gguf.",
            "runtime_family": ["llama.cpp", "llamafile", "ollama", "ktransformers"],
        },
    ),
}


class SeedImportService:
    def __init__(
        self,
        event_bus: InMemoryEventBus,
        repository: SeedImportRepository,
        runtime_registry: RuntimeRegistry,
        audit_service: AuditService,
    ) -> None:
        self._event_bus = event_bus
        self._repository = repository
        self._runtime_registry = runtime_registry
        self._audit_service = audit_service

    def inspect_source(self, request: SeedImportRequest) -> SeedImportRecord:
        source_path = Path(request.source_path)
        if not source_path.exists():
            raise ValueError(f"Seed source path {request.source_path} was not found.")
        if source_path.is_file() and source_path.suffix.lower() == ".zip":
            with TemporaryDirectory(prefix="mariam-seed-dna-") as temp_dir:
                extracted_root = Path(temp_dir)
                self._extract_seed_zip(source_path, extracted_root)
                seed_root = self._find_seed_root(extracted_root)
                return self._inspect_seed_root(request, seed_root, source_path)
        if not source_path.is_dir():
            raise ValueError(f"Seed source path {request.source_path} must be a directory or .zip file.")
        return self._inspect_seed_root(request, source_path, source_path)

    def _inspect_seed_root(
        self,
        request: SeedImportRequest,
        seed_root: Path,
        display_path: Path,
    ) -> SeedImportRecord:
        registry_path = seed_root / "registry"
        if not registry_path.exists():
            raise ValueError(f"Seed source path {request.source_path} does not contain a registry directory.")

        warnings: list[str] = []
        coverage = self._read_json(seed_root / "SOURCE_COVERAGE.json", warnings)
        registry_files = [
            str(path.relative_to(seed_root))
            for path in [
                registry_path / "MASTER_AGENT_REGISTRY.json",
                registry_path / "MASTER_CAPABILITY_REGISTRY.json",
                registry_path / "MASTER_WORKFLOW_REGISTRY.json",
                registry_path / "MASTER_RUNTIME_TARGET_REGISTRY.json",
            ]
            if path.exists()
        ]
        domain_evidence = self._read_domain_evidence(registry_path, warnings)
        plugin_candidates = self._build_plugin_candidates(domain_evidence, str(display_path))
        record = create_seed_import_record(
            source_path=str(display_path),
            source_name=display_path.name,
            coverage={
                "eligible_files_discovered": coverage.get("eligible_files_discovered", 0),
                "files_scanned": coverage.get("files_scanned", 0),
                "files_failed": coverage.get("files_failed", 0),
                "source_coverage_pct": coverage.get("source_coverage_pct", 0),
                "excluded_dirs": coverage.get("excluded_dirs", []),
                "forbidden_roots_rejected": coverage.get("forbidden_roots_rejected", []),
            },
            registry_files=registry_files,
            domain_evidence=domain_evidence,
            plugin_candidates=plugin_candidates,
            warnings=warnings,
        )
        saved = self._repository.save(record)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="seed_import.inspect",
                target_type="seed_source",
                target_id=saved.source_id,
                decision="approved",
                evidence={
                    "source_path": saved.source_path,
                    "source_name": saved.source_name,
                    "reason": request.reason,
                    "plugin_candidates": len(saved.plugin_candidates),
                    "domain_evidence": len(saved.domain_evidence),
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "seed_import.inspected",
            "seed-import-service",
            {
                "source_id": saved.source_id,
                "source_path": saved.source_path,
                "source_name": saved.source_name,
                "plugin_candidates": len(saved.plugin_candidates),
                "domain_evidence": len(saved.domain_evidence),
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def _extract_seed_zip(self, zip_path: Path, target_root: Path) -> None:
        with ZipFile(zip_path) as archive:
            for member in archive.infolist():
                member_path = target_root / member.filename
                resolved_target = member_path.resolve()
                if not str(resolved_target).startswith(str(target_root.resolve())):
                    raise ValueError(f"Unsafe ZIP entry rejected: {member.filename}")
            archive.extractall(target_root)

    def _find_seed_root(self, extracted_root: Path) -> Path:
        if (extracted_root / "registry").exists():
            return extracted_root
        candidates = [
            path
            for path in extracted_root.iterdir()
            if path.is_dir() and (path / "registry").exists()
        ]
        if len(candidates) == 1:
            return candidates[0]
        raise ValueError("ZIP seed package must contain a registry directory at root or inside one top-level folder.")

    def list_imports(self) -> list[SeedImportRecord]:
        return self._repository.list()

    def list_external_sources(self) -> list[ExternalSeedSource]:
        return list(EXTERNAL_SEED_SOURCES.values())

    def prepare_external_source(self, source_key: str, request: SeedImportRequest) -> SeedImportRecord:
        source = EXTERNAL_SEED_SOURCES.get(source_key)
        if source is None:
            raise ValueError(f"External seed source {source_key} was not found.")

        candidates = [self._external_source_candidate(source, plugin_id) for plugin_id in source.target_plugins]
        record = create_seed_import_record(
            source_path=source.url,
            source_name=source.name,
            coverage={
                "eligible_files_discovered": len(source.traceability.get("files_inspected", [])),
                "files_scanned": len(source.traceability.get("files_inspected", [])),
                "files_failed": 0,
                "source_coverage_pct": 100,
                "external_source_type": source.source_type,
                "source_key": source.source_key,
            },
            registry_files=list(source.traceability.get("files_inspected", [])),
            domain_evidence=[
                SeedDomainEvidence(
                    domain=domain,
                    runtime_readiness="candidate",
                    total_matching_assets=1,
                    total_matching_terms=1,
                    top_source_projects=[{"name": source.name, "count": 1}],
                    top_source_categories=[{"name": domain, "count": 1}],
                )
                for domain in source.extracted_dna_domains
            ],
            plugin_candidates=candidates,
            warnings=[
                "External source prepared as DNA candidate only.",
                "Runtime execution requires governance approval and sandbox validation.",
            ],
        )
        saved = self._repository.save(record)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="seed_import.external_source_prepare",
                target_type="external_seed_source",
                target_id=saved.source_id,
                decision="approved",
                evidence={
                    "source_key": source.source_key,
                    "source_url": source.url,
                    "reason": request.reason,
                    "target_plugins": source.target_plugins,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "seed_import.external_source_prepared",
            "seed-import-service",
            {
                "source_id": saved.source_id,
                "source_key": source.source_key,
                "source_url": source.url,
                "plugin_candidates": len(saved.plugin_candidates),
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def get(self, source_id: str) -> SeedImportRecord:
        record = self._repository.get(source_id)
        if record is None:
            raise ValueError(f"Seed import {source_id} was not found.")
        return record

    def promote_plugin_candidate(
        self,
        source_id: str,
        plugin_id: str,
        request: SeedPluginPromotionRequest,
    ) -> PluginManifest:
        record = self.get(source_id)
        candidate = next((item for item in record.plugin_candidates if item.plugin_id == plugin_id), None)
        if candidate is None:
            raise ValueError(f"Plugin candidate {plugin_id} was not found in seed import {source_id}.")

        manifest = PluginManifest(
            plugin_id=candidate.plugin_id,
            name=candidate.name,
            version="0.1.0",
            status="disabled",
            dashboard_route=f"/plugins/{candidate.plugin_id}",
            settings_schema={
                "source_path": {"type": "string", "readOnly": True},
                "enabled_domains": {"type": "array", "items": {"type": "string"}},
                "activation_mode": {"type": "string", "enum": ["review_only", "governed_runtime"]},
            },
            settings_values={
                "source_path": record.source_path,
                "enabled_domains": candidate.source_domains,
                "activation_mode": "review_only",
            },
            api_prefix=f"/api/plugins/{candidate.plugin_id}",
            data_boundary=candidate.data_boundary,
            permissions=[
                f"{candidate.plugin_id}.read",
                f"{candidate.plugin_id}.review",
                f"{candidate.plugin_id}.approve",
            ],
            produced_events=[f"{candidate.plugin_id}.candidate_promoted"],
            consumed_events=["seed_import.inspected", "governance.approved"],
            chief_agent_role=f"{candidate.name} Chief Agent",
            swarm_roles=[
                f"{candidate.name} Analyst",
                f"{candidate.name} Validator",
                f"{candidate.name} Governance Reviewer",
            ],
            workflows=[
                "inspect_seed_evidence",
                "deduplicate_repeated_domain_features",
                "prepare_governed_activation",
            ],
            provider_dependencies=[],
            connector_dependencies=[],
            runtime_dependencies=["event_bus", "audit_log", "runtime_registry"],
            tests=["api", "runtime", "permissions", "seed-evidence", "governance"],
            acceptance_criteria=[
                "Candidate remains disabled until explicit validation and approval.",
                "Every imported feature keeps source traceability.",
                "Repeated domains are merged into one canonical plugin candidate.",
            ],
            rollback_plan="Disable the promoted plugin and retain the seed import record for audit review.",
        )
        plugin = self._runtime_registry.register_plugin(manifest)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="seed_import.promote_plugin_candidate",
                target_type="plugin",
                target_id=plugin.plugin_id,
                decision="approved",
                evidence={
                    "source_id": source_id,
                    "source_path": record.source_path,
                    "reason": request.reason,
                    "candidate": candidate.model_dump(mode="json"),
                    "data_platform": "DB MARIAM",
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "seed_import.plugin_candidate_promoted",
            "seed-import-service",
            {
                "source_id": source_id,
                "plugin_id": plugin.plugin_id,
                "status": plugin.status,
                "source_domains": candidate.source_domains,
                "data_platform": "DB MARIAM",
            },
        )
        return plugin

    def _read_domain_evidence(self, registry_path: Path, warnings: list[str]) -> list[SeedDomainEvidence]:
        evidence: list[SeedDomainEvidence] = []
        domain_names = sorted({domain for group in CANONICAL_PLUGIN_GROUPS.values() for domain in group["domains"]})
        for domain in domain_names:
            summary_path = registry_path / domain / "SUMMARY.json"
            if not summary_path.exists():
                warnings.append(f"Missing domain summary: {domain}")
                continue
            summary = self._read_json(summary_path, warnings)
            evidence.append(
                SeedDomainEvidence(
                    domain=domain,
                    runtime_readiness=str(summary.get("runtime_readiness", "unknown")),
                    total_matching_assets=int(summary.get("total_matching_assets", 0)),
                    total_matching_terms=int(summary.get("total_matching_terms", 0)),
                    top_source_projects=list(summary.get("top_source_projects", []))[:10],
                    top_source_categories=list(summary.get("top_source_categories", []))[:10],
                )
            )
        return evidence

    def _build_plugin_candidates(
        self,
        domain_evidence: list[SeedDomainEvidence],
        source_path: str,
    ) -> list[SeedPluginCandidate]:
        evidence_by_domain = {item.domain: item for item in domain_evidence}
        candidates: list[SeedPluginCandidate] = []
        for plugin_id, group in CANONICAL_PLUGIN_GROUPS.items():
            present = [domain for domain in group["domains"] if domain in evidence_by_domain]
            if not present:
                continue
            assets = sum(evidence_by_domain[domain].total_matching_assets for domain in present)
            terms = sum(evidence_by_domain[domain].total_matching_terms for domain in present)
            readiness = "high" if all(evidence_by_domain[domain].runtime_readiness == "high" for domain in present) else "mixed"
            candidates.append(
                SeedPluginCandidate(
                    plugin_id=plugin_id,
                    name=str(group["name"]),
                    source_domains=present,
                    feature_summary=list(group["features"]),
                    evidence_assets=assets,
                    evidence_terms=terms,
                    runtime_readiness=readiness,
                    data_boundary=plugin_id,
                    private_table_prefix=plugin_id,
                    traceability={
                        "source_path": source_path,
                        "merge_rule": "same_domain_features_are_deduplicated_into_one_canonical_plugin",
                        "domains": {
                            domain: {
                                "assets": evidence_by_domain[domain].total_matching_assets,
                                "terms": evidence_by_domain[domain].total_matching_terms,
                                "runtime_readiness": evidence_by_domain[domain].runtime_readiness,
                            }
                            for domain in present
                        },
                    },
                )
            )
        return candidates

    def _external_source_candidate(self, source: ExternalSeedSource, plugin_id: str) -> SeedPluginCandidate:
        group = CANONICAL_PLUGIN_GROUPS[plugin_id]
        return SeedPluginCandidate(
            plugin_id=plugin_id,
            name=str(group["name"]),
            source_domains=list(source.extracted_dna_domains),
            feature_summary=list(group["features"]),
            evidence_assets=len(source.extracted_dna_domains),
            evidence_terms=len(source.integration_notes),
            runtime_readiness="candidate",
            data_boundary=plugin_id,
            private_table_prefix=plugin_id,
            governance_gate="external_seed_review_before_activation",
            traceability={
                "source_key": source.source_key,
                "source_url": source.url,
                "source_type": source.source_type,
                "integration_notes": source.integration_notes,
                "security_notes": source.security_notes,
                "original_traceability": source.traceability,
            },
        )

    def _read_json(self, path: Path, warnings: list[str]) -> dict:
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except FileNotFoundError:
            warnings.append(f"Missing JSON file: {path}")
            return {}
        except json.JSONDecodeError as error:
            warnings.append(f"Invalid JSON file {path}: {error}")
            return {}
        if isinstance(payload, dict):
            return payload
        warnings.append(f"JSON file is not an object: {path}")
        return {}
