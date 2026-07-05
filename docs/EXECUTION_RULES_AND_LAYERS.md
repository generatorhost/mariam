# Mariam Execution Rules And Correct Layers

## Core Rule

Mariam is a Living Enterprise OS Core. It must stay small, replaceable, testable, and documentation-driven.

The core owns:

- Runtime lifecycle
- API routing boundary
- Event bus
- Plugin/App registry
- Provider/Connector registry
- Governance and permissions hooks
- Health and observability contracts

The core must not contain business-specific plugin logic.

## Official Terms

These terms are mandatory in code, documentation, API names, database naming, plugin manifests, and UI labels unless a legacy import explicitly records the older name as historical only.

- Mariam Living Enterprise OS Core: the official name of the core runtime. Do not reduce Mariam to an AI kernel.
- Mariam Data Platform: the official data layer. Do not use Business DB as an official term.
- Runtime Object: any object that can be added, edited, deleted, disabled, enabled, upgraded, replaced, forked, rolled back, imported from DNA, or exported as DNA.
- DNA Managed Runtime Object: a runtime object governed by DNA import/export, compatibility, versioning, audit, and rollback.
- Plugin Business Unit: a plugin/app that behaves as a managed business or department with its own dashboard, settings, Chief Agent, swarm, data boundary, workflows, tests, and delivery gates.
- Provider: a model, service, platform, tool, or runtime provider registered through a governed provider boundary.
- Connector: a governed bridge to an external system, platform, API, account, webhook, or data source.
- MCP Server: a managed integration runtime exposed through the Model Context Protocol boundary.
- Chief Agent: the accountable lead agent for a plugin, department, mission, or platform capability.
- Swarm: a coordinated group of agents with declared roles, permissions, events, tests, and acceptance criteria.
- Mission: a governed unit of work with traceability, runtime state, events, artifacts, approvals, and rollback.
- Artifact: any generated or imported file, report, document, model, export, dataset, or evidence package managed by Mariam.
- Governance Gate: a permission, audit, approval, quality, compatibility, or security checkpoint before a side effect or delivery.

## Forbidden Terms

The following terms must not be used as official architecture terms:

- Business DB
- Business Database
- AI Kernel
- Kernel only
- simple plugin
- small add-on
- hardcoded provider
- static component

When these appear in legacy notes, they must be marked as legacy wording and mapped to the official term.

## Required Layers

1. Experience Layer: dashboards, command center, plugin workspaces, settings, approvals.
2. API Layer: HTTP/WebSocket endpoints, auth boundary, validation, rate limits.
3. Runtime Layer: runtime services, event bus, schedulers, workers, plugin activation.
4. Plugin/App Layer: independent business units installed through manifests.
5. Provider/Connector Layer: external platforms, model providers, tools, MCP servers.
6. Data Platform Layer: runtime DB, plugin DB boundaries, object storage, cache, logs, metrics.
7. Governance Layer: permission, audit, approval, rollback, compatibility.
8. Testing Layer: unit, API, runtime, plugin, integration, security, acceptance tests.

## Plugin/App Contract

Every plugin or app must have:

- `manifest.json`
- unique ID and version
- dashboard route
- settings schema
- API route prefix
- data boundary declaration
- private tables declaration when needed
- shared tables declaration when needed
- permissions
- events produced and consumed
- Chief Agent role
- Swarm roles
- workflow definitions
- provider/connector dependencies
- runtime service dependencies
- tests
- acceptance criteria
- rollback plan

## Prohibited

- No large monolithic files.
- No business logic inside the core.
- No hardcoded secrets.
- No provider-specific hacks inside runtime services.
- No plugin without manifest.
- No API without tests.
- No database table without migration.
- No runtime service without health reporting.

## External Repository Rule

External repositories may be inspected for DNA, patterns, and architecture lessons. Their code must not be copied into Mariam.

Patterns extracted from `sdcb/chats` and `MoneyPrinterTurbo` for this scaffold:

- backend/frontend separation
- API router boundaries
- provider registry pattern
- Docker-based local runtime stack
- Redis cache service
- object storage service
- database migration folder
- frontend dashboard shell
- testable service boundaries
