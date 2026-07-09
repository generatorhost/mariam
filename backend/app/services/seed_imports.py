import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from zipfile import ZipFile

import httpx

from app.core.audit import AuditRecordRequest
from app.core.events import InMemoryEventBus
from app.core.plugin_manifest import PluginManifest
from app.core.seed_imports import (
    ExternalSeedSource,
    SeedDNAObject,
    SeedDomainEvidence,
    SeedImportRecord,
    SeedImportRequest,
    SeedPluginCandidate,
    SeedPluginPromotionRequest,
    SeedRuntimeLoadRequest,
    SeedRuntimeLoadResponse,
    create_seed_import_record,
)
from app.core.runtime_objects import RuntimeObjectRequest
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
        "domains": [
            "model_providers",
            "model_serving",
            "model_runtime_compatibility",
            "transformers_runtime",
            "llm",
            "slm",
            "vlm",
            "audio_models",
            "inference_engines",
            "embeddings",
            "safetensors",
            "onnx",
        ],
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
        "domains": ["gguf", "gguf_models"],
        "features": [
            "HuggingFace GGUF model discovery",
            "GGUF provider candidate registration",
            "llama.cpp/llamafile runtime compatibility review",
            "Model metadata, quantization, license, and safety review candidates",
        ],
    },
}


CANONICAL_DNA_OBJECT_TYPES = {
    "Chief": ["agents", "roles", "departments"],
    "Team": ["agents", "roles", "departments", "workers"],
    "Agent": ["agents", "workers"],
    "Skill": ["skills", "capabilities", "audio_models"],
    "Capability": ["capabilities", "skills", "audio_models"],
    "Workflow": ["workflows", "workflow_engine", "processes", "async_runtimes", "task_queue"],
    "Plugin": ["apis", "connectors", "workflows", "business"],
    "Connector": ["connectors", "apis", "api_gateways"],
    "Provider": ["model_providers", "llm_provider_registry", "model_provider_registry", "model_serving", "model_runtime_compatibility", "transformers_runtime", "gguf", "gguf_models", "onnx", "safetensors", "llm", "embeddings"],
    "Model": ["gguf", "gguf_models", "onnx", "safetensors", "model_serving", "llm", "audio_models", "model_runtime_compatibility", "quantization_metadata", "embeddings"],
    "Tool": ["tools", "mcp", "apis"],
    "Service": ["apis", "api_service", "api_gateways", "deployment", "docker"],
    "Prompt": ["llm", "agents", "workflows"],
    "Policy": ["policies", "rbac", "governance", "security"],
    "Rule": ["policies", "governance", "compliance"],
    "Permission": ["rbac", "security", "governance"],
    "Dashboard": ["monitoring", "webui", "crm", "business", "video_generation"],
    "Report": ["audit", "compliance", "business", "monitoring"],
    "Scraper": ["apis", "connectors", "datasets"],
    "Scheduler": ["workflows", "workflow_engine", "task_queue", "async_runtimes", "processes"],
    "Planner": ["agents", "workflows", "capabilities"],
    "Executor": ["async_runtimes", "workflows", "deployment"],
    "Reviewer": ["governance", "audit", "compliance"],
    "Validator": ["security", "governance", "compliance"],
    "Optimizer": ["monitoring", "model_serving", "workflows"],
    "Knowledge Asset": ["knowledge_graph", "documents", "datasets", "memory", "rag"],
    "Vector Index": ["vector_databases", "embeddings", "rag"],
    "Storage Adapter": ["storage", "databases", "docker"],
    "API": ["apis", "api_service", "api_gateways"],
    "MCP Server": ["mcp", "tools", "apis"],
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
        if self._is_url(request.source_path):
            return self._inspect_url_source(request)
        source_path = Path(request.source_path)
        if not source_path.exists():
            first_split = Path(f"{request.source_path}.001")
            if first_split.exists():
                raise ValueError(
                    f"Seed source path {request.source_path} was not found as a single ZIP file. "
                    "A split archive was detected; extract or combine the .001 parts first, "
                    "or use the already extracted folder path."
                )
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

    def _is_url(self, source_path: str) -> bool:
        parsed = urlparse(source_path)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _inspect_url_source(self, request: SeedImportRequest) -> SeedImportRecord:
        parsed = urlparse(request.source_path)
        host = parsed.netloc.lower()
        if host == "github.com":
            return self._inspect_github_repository(request)
        if host == "huggingface.co":
            return self._inspect_huggingface_model(request)
        raise ValueError("URL seed extraction currently supports github.com repositories and huggingface.co model pages.")

    def _inspect_github_repository(self, request: SeedImportRequest) -> SeedImportRecord:
        match = re.match(r"^/([^/]+)/([^/]+?)(?:\.git)?/?$", urlparse(request.source_path).path)
        if match is None:
            raise ValueError("GitHub seed URL must use https://github.com/{owner}/{repo}.")
        owner, repo = match.group(1), match.group(2)
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            metadata_response = client.get(api_url, headers={"Accept": "application/vnd.github+json"})
            if metadata_response.status_code >= 400:
                raise ValueError(f"GitHub repository metadata could not be read: HTTP {metadata_response.status_code}.")
            metadata = metadata_response.json()
            default_branch = metadata.get("default_branch") or "main"
            archive_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{default_branch}.zip"
            archive_response = client.get(archive_url, timeout=120.0)
            if archive_response.status_code >= 400:
                raise ValueError(f"GitHub repository archive could not be downloaded: HTTP {archive_response.status_code}.")
        with TemporaryDirectory(prefix="mariam-github-seed-") as temp_dir:
            archive_path = Path(temp_dir) / f"{repo}.zip"
            archive_path.write_bytes(archive_response.content)
            extracted_root = Path(temp_dir) / "extracted"
            extracted_root.mkdir()
            self._extract_seed_zip(archive_path, extracted_root)
            seed_roots = [path for path in extracted_root.iterdir() if path.is_dir()]
            seed_root = seed_roots[0] if len(seed_roots) == 1 else extracted_root
            record = self._inspect_generic_seed_root(request, seed_root, Path(f"github.com/{owner}/{repo}"))
            metadata_coverage = {
                **record.coverage,
                "extraction_mode": "github_repository_dna",
                "source_url": request.source_path,
                "github_owner": owner,
                "github_repo": repo,
                "github_default_branch": default_branch,
                "github_stars": metadata.get("stargazers_count", 0),
                "github_language": metadata.get("language"),
            }
            updated = record.model_copy(update={"coverage": metadata_coverage})
            return self._repository.save(updated)

    def _inspect_huggingface_model(self, request: SeedImportRequest) -> SeedImportRecord:
        model_id = urlparse(request.source_path).path.strip("/")
        if model_id.count("/") < 1:
            raise ValueError("HuggingFace seed URL must use https://huggingface.co/{owner}/{model}.")
        api_url = f"https://huggingface.co/api/models/{model_id}"
        warnings: list[str] = []
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            response = client.get(api_url)
            if response.status_code >= 400:
                raise ValueError(f"HuggingFace model metadata could not be read: HTTP {response.status_code}.")
            metadata = response.json()
        siblings = list(metadata.get("siblings", []))
        tags = [str(tag).lower() for tag in metadata.get("tags", [])]
        sibling_names = [str(item.get("rfilename", "")).lower() for item in siblings if isinstance(item, dict)]
        domains = {
            "model_providers",
            "model_serving",
            "llm",
            "api_service",
        }
        if any("safetensors" in name for name in sibling_names):
            domains.add("safetensors")
            domains.add("model_runtime_compatibility")
        if any("onnx" in name for name in sibling_names) or "onnx" in tags:
            domains.add("onnx")
            domains.add("model_runtime_compatibility")
        if any("gguf" in name for name in sibling_names) or "gguf" in tags:
            domains.add("gguf_models")
            domains.add("gguf")
        if any("audio" in tag for tag in tags) or "audio" in model_id.lower():
            domains.add("audio_models")
            domains.add("capabilities")
        if any("transformers" in tag for tag in tags):
            domains.add("transformers_runtime")
            domains.add("model_runtime_compatibility")
        if not siblings:
            warnings.append("HuggingFace metadata did not expose file siblings; extraction used tags and model id only.")

        domain_evidence = [
            SeedDomainEvidence(
                domain=domain,
                runtime_readiness="candidate",
                total_matching_assets=max(1, len(siblings)),
                total_matching_terms=max(1, len(tags)),
                top_source_projects=[{"name": model_id, "count": max(1, len(siblings))}],
                top_source_categories=[{"name": tag, "count": 1} for tag in tags[:10]],
            )
            for domain in sorted(domains)
        ]
        plugin_candidates = self._build_plugin_candidates(domain_evidence, request.source_path)
        dna_objects = self._build_dna_objects(domain_evidence, plugin_candidates, request.source_path)
        record = create_seed_import_record(
            source_path=request.source_path,
            source_name=model_id,
            coverage={
                "eligible_files_discovered": len(siblings),
                "files_scanned": len(siblings),
                "files_failed": 0,
                "source_coverage_pct": 100,
                "extraction_mode": "huggingface_model_dna",
                "model_id": model_id,
                "pipeline_tag": metadata.get("pipeline_tag"),
                "library_name": metadata.get("library_name"),
                "downloads": metadata.get("downloads", 0),
                "likes": metadata.get("likes", 0),
            },
            registry_files=sibling_names[:50],
            domain_evidence=domain_evidence,
            dna_objects=dna_objects,
            plugin_candidates=plugin_candidates,
            warnings=warnings,
        )
        saved = self._repository.save(record)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="seed_import.huggingface_model_inspect",
                target_type="huggingface_model",
                target_id=saved.source_id,
                decision="approved",
                evidence={
                    "source_path": saved.source_path,
                    "model_id": model_id,
                    "reason": request.reason,
                    "dna_objects": len(saved.dna_objects),
                    "dna_object_counts": saved.dna_object_counts,
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "seed_import.huggingface_model_inspected",
            "seed-import-runtime",
            {
                "source_id": saved.source_id,
                "model_id": model_id,
                "dna_objects": len(saved.dna_objects),
                "dna_object_counts": saved.dna_object_counts,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def _inspect_seed_root(
        self,
        request: SeedImportRequest,
        seed_root: Path,
        display_path: Path,
    ) -> SeedImportRecord:
        registry_path = seed_root / "registry"
        if not registry_path.exists():
            return self._inspect_generic_seed_root(request, seed_root, display_path)

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
        dna_objects = self._build_dna_objects(domain_evidence, plugin_candidates, str(display_path))
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
            dna_objects=dna_objects,
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
                    "dna_objects": len(saved.dna_objects),
                    "dna_object_counts": saved.dna_object_counts,
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
                "dna_objects": len(saved.dna_objects),
                "dna_object_counts": saved.dna_object_counts,
                "domain_evidence": len(saved.domain_evidence),
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def _inspect_generic_seed_root(
        self,
        request: SeedImportRequest,
        seed_root: Path,
        display_path: Path,
    ) -> SeedImportRecord:
        warnings = ["Registry directory was not found; generic DNA extraction was used."]
        allowed_suffixes = {
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".sql",
            ".html",
            ".css",
        }
        skipped_dirs = {".git", "node_modules", "__pycache__", ".pytest_cache", "dist", "build", ".venv", "venv"}
        domain_names = sorted({domain for group in CANONICAL_PLUGIN_GROUPS.values() for domain in group["domains"]})
        domain_hits = {domain: {"assets": 0, "terms": 0, "evidence": []} for domain in domain_names}
        files_scanned = 0
        files_failed = 0
        eligible_files = 0

        for path in seed_root.rglob("*"):
            if not path.is_file() or any(part in skipped_dirs for part in path.parts):
                continue
            if path.suffix.lower() not in allowed_suffixes:
                continue
            eligible_files += 1
            if files_scanned >= 2000:
                warnings.append("Generic scan stopped at 2000 files to keep import responsive.")
                break
            try:
                relative = str(path.relative_to(seed_root)).lower()
                text = path.read_text(encoding="utf-8", errors="ignore")[:20000].lower()
                haystack = f"{relative}\n{text}"
                files_scanned += 1
            except OSError:
                files_failed += 1
                continue
            for domain in domain_names:
                terms = self._domain_terms(domain)
                matches = sum(1 for term in terms if term in haystack)
                if matches:
                    domain_hits[domain]["assets"] += 1
                    domain_hits[domain]["terms"] += matches
                    if len(domain_hits[domain]["evidence"]) < 5:
                        domain_hits[domain]["evidence"].append(
                            {
                                "file": str(path.relative_to(seed_root)),
                                "matches": matches,
                                "snippet": self._snippet_for_terms(haystack, terms),
                            }
                        )

        domain_evidence = [
            SeedDomainEvidence(
                domain=domain,
                runtime_readiness="candidate",
                total_matching_assets=int(hit["assets"]),
                total_matching_terms=int(hit["terms"]),
                top_source_projects=[{"name": display_path.name, "count": int(hit["assets"])}],
                top_source_categories=[
                    {
                        "name": evidence["file"],
                        "count": int(evidence["matches"]),
                        "snippet": evidence["snippet"],
                    }
                    for evidence in list(hit["evidence"])
                ],
            )
            for domain, hit in domain_hits.items()
            if int(hit["assets"]) > 0
        ]
        plugin_candidates = self._build_plugin_candidates(domain_evidence, str(display_path))
        dna_objects = self._build_dna_objects(domain_evidence, plugin_candidates, str(display_path))
        record = create_seed_import_record(
            source_path=str(display_path),
            source_name=display_path.name,
            coverage={
                "eligible_files_discovered": eligible_files,
                "files_scanned": files_scanned,
                "files_failed": files_failed,
                "source_coverage_pct": 100 if files_scanned else 0,
                "extraction_mode": "generic_folder_dna",
                "scan_limit": 2000,
            },
            registry_files=[],
            domain_evidence=domain_evidence,
            dna_objects=dna_objects,
            plugin_candidates=plugin_candidates,
            warnings=warnings,
        )
        saved = self._repository.save(record)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="seed_import.inspect_generic",
                target_type="seed_source",
                target_id=saved.source_id,
                decision="approved",
                evidence={
                    "source_path": saved.source_path,
                    "source_name": saved.source_name,
                    "reason": request.reason,
                    "plugin_candidates": len(saved.plugin_candidates),
                    "dna_objects": len(saved.dna_objects),
                    "dna_object_counts": saved.dna_object_counts,
                    "domain_evidence": len(saved.domain_evidence),
                    "data_platform": saved.data_platform,
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "seed_import.generic_inspected",
            "seed-import-runtime",
            {
                "source_id": saved.source_id,
                "source_path": saved.source_path,
                "plugin_candidates": len(saved.plugin_candidates),
                "dna_objects": len(saved.dna_objects),
                "dna_object_counts": saved.dna_object_counts,
                "domain_evidence": len(saved.domain_evidence),
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def _snippet_for_terms(self, haystack: str, terms: list[str]) -> str:
        normalized_terms = [term for term in terms if term]
        match_positions = [
            (position, term)
            for term in normalized_terms
            if (position := haystack.find(term.lower())) >= 0
        ]
        if not match_positions:
            return haystack[:180].replace("\n", " ").strip()
        position, term = min(match_positions, key=lambda item: item[0])
        start = max(0, position - 70)
        end = min(len(haystack), position + len(term) + 110)
        snippet = haystack[start:end].replace("\n", " ").strip()
        return re.sub(r"\s+", " ", snippet)[:240]

    def _domain_terms(self, domain: str) -> list[str]:
        normalized = domain.replace("_", " ")
        compact = domain.replace("_", "")
        terms = {domain.lower(), normalized.lower(), compact.lower()}
        if domain in {"mcp", "apis", "api_gateways"}:
            terms.update({"mcp", "api", "gateway", "server"})
        if domain in {"agents", "roles", "departments", "workers", "skills", "capabilities"}:
            terms.update({"agent", "chief", "team leader", "skill", "capability", "mission", "task"})
        if domain in {"workflows", "processes", "event_streaming", "async_runtimes"}:
            terms.update({"workflow", "pipeline", "scheduler", "executor", "task graph", "event"})
        if domain in {"knowledge_graph", "memory", "rag", "vector_databases", "datasets", "documents"}:
            terms.update({"knowledge", "memory", "vector", "embedding", "semantic", "document", "rag"})
        if domain in {"model_providers", "model_serving", "llm", "embeddings"}:
            terms.update({"model", "provider", "ollama", "gguf", "onnx", "safetensors", "embedding"})
        if domain in {"security", "rbac", "policies", "governance", "audit", "compliance"}:
            terms.update({"security", "permission", "policy", "governance", "audit", "approval"})
        if domain in {"docker", "kubernetes", "deployment", "monitoring", "logging", "storage", "databases"}:
            terms.update({"docker", "database", "postgres", "redis", "storage", "metrics", "logs"})
        if domain in {"crm", "sales", "business", "saas"}:
            terms.update({"crm", "sales", "client", "business", "lead", "pipeline"})
        if domain in {"video_generation", "media", "voice", "subtitle", "material", "upload_post"}:
            terms.update({"video", "media", "voice", "subtitle", "render", "upload"})
        return sorted(terms)

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
        domain_evidence = [
            SeedDomainEvidence(
                domain=domain,
                runtime_readiness="candidate",
                total_matching_assets=1,
                total_matching_terms=1,
                top_source_projects=[{"name": source.name, "count": 1}],
                top_source_categories=[{"name": domain, "count": 1}],
            )
            for domain in source.extracted_dna_domains
        ]
        dna_objects = self._build_dna_objects(domain_evidence, candidates, source.url)
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
            domain_evidence=domain_evidence,
            dna_objects=dna_objects,
            plugin_candidates=candidates,
            warnings=[
                "External source prepared as live DNA objects and plugin candidates.",
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
                    "dna_objects": len(saved.dna_objects),
                    "dna_object_counts": saved.dna_object_counts,
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
                "dna_objects": len(saved.dna_objects),
                "dna_object_counts": saved.dna_object_counts,
                "data_platform": saved.data_platform,
            },
        )
        return saved

    def get(self, source_id: str) -> SeedImportRecord:
        record = self._repository.get(source_id)
        if record is None:
            raise ValueError(f"Seed import {source_id} was not found.")
        return record

    def build_runtime_object_requests(self, source_id: str) -> list[RuntimeObjectRequest]:
        record = self.get(source_id)
        requests: list[RuntimeObjectRequest] = []
        for dna_object in record.dna_objects:
            requests.append(
                RuntimeObjectRequest(
                    object_type=dna_object.object_type,
                    name=dna_object.name,
                    version="0.1.0",
                    manifest={
                        "dna_object_key": dna_object.object_key,
                        "seed_source_id": record.source_id,
                        "seed_source_path": record.source_path,
                        "seed_source_name": record.source_name,
                        "status": "loaded_from_seed_dna",
                        "runtime_target": dna_object.runtime_target,
                        "governance_gate": dna_object.governance_gate,
                        "source_domains": dna_object.source_domains,
                        "evidence_assets": dna_object.evidence_assets,
                        "evidence_terms": dna_object.evidence_terms,
                        "extraction_evidence": dna_object.extraction_evidence,
                        "traceability": dna_object.traceability,
                        "data_platform": "DB MARIAM",
                    },
                )
            )
        return requests

    def mark_runtime_loaded(
        self,
        source_id: str,
        request: SeedRuntimeLoadRequest,
        runtime_object_ids: list[str],
    ) -> SeedRuntimeLoadResponse:
        record = self.get(source_id)
        loaded_ids = sorted(set([*record.loaded_runtime_object_ids, *runtime_object_ids]))
        updated = record.model_copy(update={"loaded_runtime_object_ids": loaded_ids, "status": "loaded_to_runtime_store"})
        saved = self._repository.save(updated)
        self._audit_service.record(
            AuditRecordRequest(
                actor_id=request.actor_id,
                action="seed_import.load_runtime_objects",
                target_type="seed_source",
                target_id=source_id,
                decision="approved",
                evidence={
                    "reason": request.reason,
                    "runtime_store": "runtime_objects",
                    "loaded_runtime_object_ids": loaded_ids,
                    "loaded_counts": saved.dna_object_counts,
                    "data_platform": "DB MARIAM",
                    **request.evidence,
                },
            )
        )
        self._event_bus.publish(
            "seed_import.runtime_objects_loaded",
            "seed-import-runtime",
            {
                "source_id": source_id,
                "runtime_store": "runtime_objects",
                "loaded_runtime_objects": len(loaded_ids),
                "loaded_counts": saved.dna_object_counts,
                "data_platform": "DB MARIAM",
            },
        )
        return SeedRuntimeLoadResponse(
            source_id=source_id,
            status=saved.status,
            loaded_runtime_object_ids=loaded_ids,
            loaded_counts=saved.dna_object_counts,
            notes=[
                "Extracted DNA objects were loaded into the runtime_objects store.",
                "Each object keeps seed traceability and governance gates.",
                "DB MARIAM remains the target data platform for runtime loading.",
            ],
        )

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

    def _build_dna_objects(
        self,
        domain_evidence: list[SeedDomainEvidence],
        plugin_candidates: list[SeedPluginCandidate],
        source_path: str,
    ) -> list[SeedDNAObject]:
        evidence_by_domain = {item.domain: item for item in domain_evidence}
        objects: list[SeedDNAObject] = []
        for object_type, mapped_domains in CANONICAL_DNA_OBJECT_TYPES.items():
            present = [domain for domain in mapped_domains if domain in evidence_by_domain]
            if not present:
                continue
            assets = sum(evidence_by_domain[domain].total_matching_assets for domain in present)
            terms = sum(evidence_by_domain[domain].total_matching_terms for domain in present)
            object_key = object_type.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
            runtime_target = self._runtime_target_for_object_type(object_type)
            extraction_evidence = []
            for domain in present:
                for evidence in evidence_by_domain[domain].top_source_categories[:3]:
                    extraction_evidence.append(
                        {
                            "domain": domain,
                            "file": evidence.get("name"),
                            "matches": evidence.get("count", 1),
                            "snippet": evidence.get("snippet", ""),
                        }
                    )
            objects.append(
                SeedDNAObject(
                    object_key=f"seed_{object_key}",
                    object_type=object_type,
                    name=f"Extracted {object_type} DNA",
                    source_domains=present,
                    evidence_assets=assets,
                    evidence_terms=terms,
                    runtime_target=runtime_target,
                    extraction_evidence=extraction_evidence[:8],
                    traceability={
                        "source_path": source_path,
                        "matched_domains": {
                            domain: {
                                "assets": evidence_by_domain[domain].total_matching_assets,
                                "terms": evidence_by_domain[domain].total_matching_terms,
                                "runtime_readiness": evidence_by_domain[domain].runtime_readiness,
                            }
                            for domain in present
                        },
                        "related_plugin_candidates": [
                            candidate.plugin_id
                            for candidate in plugin_candidates
                            if set(candidate.source_domains).intersection(present)
                        ],
                        "merge_rule": "same_type_features_are_loaded_as_one_governed_runtime_object_candidate",
                    },
                )
            )
        return objects

    def _runtime_target_for_object_type(self, object_type: str) -> str:
        if object_type in {"Chief", "Team", "Agent", "Skill", "Capability", "Planner", "Executor", "Reviewer", "Validator", "Optimizer"}:
            return "agent_runtime"
        if object_type in {"Workflow", "Scheduler"}:
            return "workflow_runtime"
        if object_type in {"Plugin", "Connector", "Provider", "Model", "Tool", "Service", "API", "MCP Server"}:
            return "runtime_ecosystem"
        if object_type in {"Knowledge Asset", "Vector Index"}:
            return "knowledge_runtime"
        if object_type in {"Policy", "Rule", "Permission", "Report"}:
            return "governance_runtime"
        if object_type in {"Dashboard"}:
            return "experience_runtime"
        if object_type in {"Storage Adapter"}:
            return "data_platform_runtime"
        return "dna_runtime"

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
