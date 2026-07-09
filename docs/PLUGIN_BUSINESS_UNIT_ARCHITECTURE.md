# Plugin Business Unit Architecture

This file is the implementation-side guardrail for building plugins inside `generatorhost/mariam`.

Canonical Architecture Library document:
`architecture-library/volume-31-plugin-enterprise-management-os/plugin-visual-mockups-are-not-plugin-architecture.md`

## Core Rule
Do not build a Mariam plugin as a single dashboard screen.

A plugin is a Plugin-managed Business Unit. The user may see an app-like workspace, but the implementation must include runtime, data, API, agents, governance, quality, approval, health, readiness, and lifecycle behavior.

## Visual Mockups
Screenshots and visual mockups are seeds only.

They can inform layout direction, common panels, quick actions, useful metrics, navigation ideas, and user workflow hints.

They do not define plugin architecture, database schema, API contracts, runtime completion, permission rules, governance rules, or fake metrics as real system state.

## Minimum Plugin Contract
Every plugin must declare or implement:

- plugin ID
- plugin manifest
- dashboard route
- settings route
- API prefix
- data boundary
- private table prefix
- Chief Agent
- swarm roles
- workflows
- missions, tasks, jobs, and reviews
- provider and connector dependencies
- model/runtime settings when applicable
- lifecycle actions
- validation checks
- runtime readiness checks
- health checks
- logs and audit records
- governance gates
- quality gates
- security gates
- approval gates
- delivery gates
- tests
- rollback plan

## DNA Pipeline Contract
Any local folder, ZIP, GitHub repository, HuggingFace model page, or supported model file may become a plugin source only through the governed DNA pipeline.

The operator must choose one of these modes:

- `extract_only`: create a source inspection record only.
- `load_runtime`: extract DNA and load DNA objects into the runtime object store.
- `promote_plugins`: extract DNA and promote plugin candidates as disabled Plugin-managed Business Units.
- `full`: extract DNA, load runtime objects, and promote plugin candidates.

Generated plugins are never enabled automatically. They remain disabled until validation, readiness, governance, approval, and rollback evidence exist.

## Database Rule
Plugin private tables must start with the plugin ID.

Shared platform tables are reserved for identity, permissions, audit, events, billing, registry, runtime objects, and governance.

## Cross-Plugin Rule
A plugin can request capabilities from another plugin only through approved orchestration.

No plugin may directly read another plugin private table, skip permissions, bypass audit, or call another plugin capability as an uncontrolled shortcut.

## UI Rule
The UI is an experience layer over the plugin runtime.

Keep the user screen simple:

- command/chat
- clear plugin actions
- current jobs
- approvals
- health/readiness
- settings
- logs when needed

Expose advanced internals through progressive disclosure.

## Acceptance
A plugin is not accepted until:

- the UI action calls an API
- the API performs permission and governance checks
- runtime services execute real behavior
- DB MARIAM stores durable state
- events and audit logs are written
- health/readiness is visible
- validation and tests pass
- Architecture Library is updated
