# Mariam Living DNA to Plugin Execution Rules

## Purpose

This document fixes the execution rule for external seeds such as `C:\1\mayou-1001`.
Seeds are not passive references. Mariam imports them as living DNA candidates, merges repeated
domain features, and promotes approved groups into governed Plugin-managed Business Units.

## Core Rule

External seed data follows this path:

```text
Seed folder or ZIP
-> safe inspection
-> domain evidence extraction
-> repeated-domain deduplication
-> canonical plugin candidate
-> disabled plugin promotion
-> validation
-> governance approval
-> runtime enablement
```

No imported seed feature may execute automatically during inspection.

## Canonical Runtime Unification Rule

Mariam does not keep separate "old" and "new" user-facing systems.

After extraction, every useful seed feature must be normalized into one of the canonical runtime families:

- Runtime Object
- Plugin-managed Business Unit
- Agent Society
- Workflow
- Provider
- Connector
- Model Runtime
- Tool
- API
- MCP Server
- Knowledge Asset
- Vector Index
- Storage Adapter

If a seed artifact cannot become one of these canonical runtime objects, it remains evidence only and must not appear as an active dashboard, plugin, or command option.

Historical names and archives are traceability evidence, not product identity and not active user workflow.

## Deduplication Rule

If a domain appears in several sources, Mariam does not create duplicate plugins.
Mariam merges the useful features into one canonical candidate while preserving traceability.

Examples:

- `mcp`, `tools`, `apis`, `connectors`, and `api_gateways` merge into `plugin_mcp_runtime_manager`.
- `model_providers`, `model_serving`, `llm`, `slm`, `vlm`, `inference_engines`, and `embeddings`
  merge into `plugin_model_provider_manager`.
- `agents`, `roles`, `departments`, `workers`, `skills`, and `capabilities`
  merge into `plugin_agent_society_manager`.
- MoneyPrinterTurbo video-generation concepts merge into `plugin_video_generation_manager`
  and related provider/connector/security plugins.
- HuggingFace GGUF catalog concepts merge into `plugin_gguf_model_catalog_manager`
  and `plugin_model_provider_manager`.

## Plugin Promotion Rule

Promoted seed candidates must be created as disabled plugins.
They become active only after:

- validation,
- impact analysis,
- governance approval,
- security review where required,
- runtime readiness check.

## Database Rule

Every promoted plugin must use its plugin id as private table prefix.

Example:

```text
plugin_mcp_runtime_manager_settings
plugin_mcp_runtime_manager_workflows
plugin_mcp_runtime_manager_artifacts
```

Shared platform tables remain shared:

```text
identity
permissions
audit
events
registry
```

## Model Runtime Rule

Model packages and model metadata extracted from seeds become provider/model runtime candidates,
not hard-coded kernel logic.

Supported candidate families include:

- Ollama local models,
- remote AI APIs,
- GGUF through llama.cpp/llamafile-compatible runtimes,
- ONNX through ONNX Runtime-compatible runtimes,
- SafeTensors through Transformers-compatible runtimes.

## External Source Rule

External repositories and model catalogs may be added as living DNA sources only when they remain disabled
until governance review.

Current external DNA source candidates:

- `MoneyPrinterTurbo`: short-video generation DNA, including script generation, search terms,
  stock material connectors, voice/subtitle generation, task queue, WebUI/API surface, and Docker runtime patterns.
- `HuggingFace GGUF Model Library`: GGUF model catalog DNA, including model provider registration,
  quantization metadata, runtime compatibility, license review, checksum review, and sandboxed activation.

External source inspection must not import secrets, generated artifacts, uploaded media, model weights,
or runtime task data.

## Acceptance Criteria

- Seed inspection records source coverage and warnings.
- Repeated domains are merged into canonical plugin candidates.
- Candidate promotion creates disabled plugins only.
- Every candidate keeps source traceability.
- Private plugin table prefixes use the plugin id.
- DB MARIAM is the target data platform.
- Active UI shows only canonical runtime objects, plugins, missions, agents, providers, connectors, models, workflows, APIs, MCP servers, and evidence-backed dashboards.
- Archive files are not loaded as active runtime context unless explicitly selected as a Seed DNA source.
