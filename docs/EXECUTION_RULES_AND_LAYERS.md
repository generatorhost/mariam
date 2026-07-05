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

