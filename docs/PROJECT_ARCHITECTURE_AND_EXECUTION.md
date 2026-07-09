# Mariam Project Architecture And Execution

This file is the practical implementation-side guide for working inside `generatorhost/mariam`.

The canonical source of truth is:
`generatorhost/Mariam-Architecture-Library`

Related Architecture Library document:
`architecture-library/volume-07-development-guide/mariam-project-architecture-and-execution-guide.md`

## What Mariam Is
Mariam is a Living Enterprise OS for an AI-managed company.

It is not only a dashboard, chatbot, or AI kernel. It manages:
- Chief agents, teams, agents, skills, capabilities, missions, tasks, reviews, and approvals.
- Plugin-managed business units.
- DNA extraction and runtime loading.
- Models, providers, connectors, tools, APIs, MCP servers, workflows, and knowledge assets.
- DB MARIAM, governance, audit, health, metrics, and runtime readiness.

## Correct Layer Order
Use this order before changing code:

1. Experience Layer: React UI, Command Center, plugin workspace, settings, approvals.
2. API Layer: FastAPI routers and request/response contracts.
3. Runtime Service Layer: service logic and orchestration.
4. Runtime Object Layer: DNA-managed runtime objects.
5. Plugin Business Unit Layer: plugin manifest, dashboard, settings, Chief Agent, swarm, lifecycle.
6. Provider/Connector Layer: external APIs, models, tools, MCP servers.
7. Data Platform Layer: DB MARIAM stores, repositories, migrations, artifacts.
8. Governance Layer: permissions, validation, audit, approval, rollback.
9. Testing Layer: unit, API, browser, runtime, data platform, acceptance.

## Required Execution Path
Every feature must follow:

1. User action.
2. Frontend command.
3. API endpoint.
4. Permission/governance check.
5. Runtime service.
6. DB MARIAM read/write.
7. Event and audit record.
8. UI result indicator.
9. Test coverage.
10. Architecture Library update.

## Seed DNA Flow
When using `#seed-dna`:

1. Enter a local path, ZIP path, GitHub URL, or HuggingFace model URL.
2. Click `Inspect Source Path`.
3. The UI calls `POST /api/seed-imports/inspect`.
4. Backend extracts domains, plugin candidates, and DNA objects.
5. The UI shows extraction mode, scanned files, domains, plugin candidates, DNA object count, and counts by type.
6. Click `Load Extracted DNA to Runtime Store`.
7. The UI calls `POST /api/seed-imports/{source_id}/load-runtime-objects`.
8. Backend creates records in `runtime_objects`.
9. The UI shows loaded runtime object count.

## Required DNA Object Types
Seed DNA and future importers must classify evidence into these types when supported:

Chief, Team, Agent, Skill, Capability, Workflow, Plugin, Connector, Provider, Model, Tool, Service, Prompt, Policy, Rule, Permission, Dashboard, Report, Scraper, Scheduler, Planner, Executor, Reviewer, Validator, Optimizer, Knowledge Asset, Vector Index, Storage Adapter, API, MCP Server.

New types require Architecture Library documentation and tests.

## Plugin Rule
Every plugin is a Plugin-managed Business Unit.

Visual mockups are not plugin architecture. They are only visual seeds. See:
`docs/PLUGIN_BUSINESS_UNIT_ARCHITECTURE.md`

Each plugin must declare:
- dashboard
- settings
- API prefix
- data boundary
- private table prefix
- Chief Agent
- swarm roles
- workflows
- provider/connector dependencies
- health/readiness
- lifecycle actions
- tests
- acceptance criteria
- rollback plan

Plugin private tables must start with the plugin ID.

## Model And Provider Rule
HuggingFace, GGUF, ONNX, SafeTensors, Ollama, llama.cpp, vLLM, PyTorch, and Transformers sources are model/provider DNA sources.

Do not treat them as static links. Extract:
- model identity
- file formats
- runtime compatibility
- capability signals
- provider requirements
- governance requirements

Do not download or activate model weights automatically without approval, sandboxing, checksum, license review, and compatibility validation.

## Documentation Rule
Any meaningful change in this repository must be documented in Architecture Library when it changes:
- object types
- APIs
- runtime behavior
- database storage
- plugins
- providers/connectors
- model handling
- UI workflow
- governance/security
- acceptance criteria

## Verify
Before reporting completion:

```powershell
npm run verify
```

The feature is not complete until tests pass and the UI shows the practical result of the action.
