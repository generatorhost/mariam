# Mariam AI Enterprise OS

This is the official code repository for Mariam AI Enterprise OS.

Mariam is being rebuilt from a documentation-driven architecture. The source of truth is:

https://github.com/generatorhost/Mariam-Architecture-Library

This repository now contains the first executable rebuild foundation:

- Backend API scaffold
- Frontend command center scaffold
- Database schema migrations
- DB MARIAM technical database identifier: `db_mariam`
- Runtime service boundaries
- Audit Log API and governance evidence foundation
- Runtime Object API and registry foundation
- AI Resource Manager provider routing
- Postgres-backed repository boundaries for audit records, runtime objects, events, plugin manifests, missions, and AI routes
- Plugin/App manifest rules
- Docker compose runtime stack
- Executable backend tests

No legacy implementation code is copied into Mariam. External repositories may be reviewed only to extract patterns, risks, and architecture ideas.

## Run Locally

```bash
docker compose up --build
```

Backend API:

```text
http://localhost:8000
```

Frontend:

```text
http://localhost:5173
```

## Test

```bash
cd backend
pip install -r requirements.txt
pytest
```

## First Executable Flow

The current rebuild foundation supports a small end-to-end mission flow:

0. Open the Command Center to automatically call `GET /api/runtime/summary`; press **Refresh System Status** to reload backend health, runtime, governance, mission, plugin, audit, AI routing counts, and recent runtime activity from the same Command Center API.

1. Open the Command Center.
2. Press **Start CRM Mission**.
3. The frontend sends `POST /api/missions`.
4. The backend validates the request and creates a governed mission plan.
5. The mission records the Plugin Chief, runtime scheduling step, approval gate, and `DB MARIAM` data platform boundary.
6. The backend emits `mission.created`.
7. The mission is saved behind a repository boundary.
8. The runtime event is saved behind an event repository boundary.
9. Docker stores mission history in the `missions` and ordered `mission_steps` tables.
10. The frontend displays the mission status and step-by-step result.
11. Press **Approve Mission** to call `POST /api/missions/{mission_id}/approve`.
12. The backend updates the mission status to `approved`, emits `mission.approved`, and records a governance audit decision.
13. Press **Reject Mission** to call `POST /api/missions/{mission_id}/reject`.
14. The backend updates the mission status to `rejected`, emits `mission.rejected`, and records rejection evidence in the audit log.
15. Mission History reads `GET /api/missions` and refreshes automatically after create, approve, or reject actions.
16. Pending Mission History records expose **Approve** and **Reject** actions so older awaiting missions can still pass through governance.
17. Audit History reads `GET /api/audit` and refreshes automatically after governance decisions.

## First AI Resource Flow

1. Press **Route AI Capability**.
2. The frontend sends `POST /api/ai-resources/route`.
3. The backend selects an approved provider for the requested capability.
4. The backend records a route decision with `route_id` and `created_at`.
5. The route decision includes `requested_by` and the `DB MARIAM` data boundary.
6. Local-first chat routing selects Ollama as a model runtime provider, not as Mariam Core.
7. The route history is available from `GET /api/ai-resources/routes`.
8. Route storage is behind a repository boundary so tests can use memory while Docker writes to Postgres in `DB MARIAM`.
9. AI Route History reads `GET /api/ai-resources/routes` and refreshes automatically after routing decisions.

## First Runtime Object Flow

1. Press **Register Runtime Object**.
2. The frontend sends `POST /api/runtime-objects`.
3. The backend registers an enabled provider runtime object.
4. The backend emits `runtime_object.registered`.
5. The backend records an audit decision for the registration.
6. Runtime Object History reads `GET /api/runtime-objects` and refreshes automatically after runtime object registration.
7. Press **Disable** or **Enable** in Runtime Object History to call the governed state-change endpoints. Disable/Delete for high-risk providers requires impact analysis and change approval; Enable requires a successful validation stamp.
8. The backend updates the runtime object status, emits a runtime event, and records an audit decision.
9. Press **Delete** to soft-delete the object without removing audit history.
10. Press **Restore** to return a soft-deleted object to disabled review state before re-enabling.
11. Press **Upgrade** to patch runtime object metadata and version through a governed audit trail.
12. Press **Rollback** to restore the previous runtime object version and manifest snapshot.
13. Press **Export DNA** to produce a governed JSON DNA package for the runtime object.
14. Press **Import Last DNA** to create a disabled runtime object from the exported DNA package for governance review.
15. Press **Validate** to run runtime object governance checks, store a validation stamp, and record pass/fail evidence.
16. Press **Analyze Impact** to estimate affected capabilities, dependencies, and risk before a runtime object change, and to store the impact stamp required for provider disable/delete.
17. Press **Approve Change** to approve a high-risk provider change after impact analysis.

## First Plugin Registry Flow

1. Press **Register CRM Plugin**.
2. The frontend sends `POST /api/plugins`.
3. The backend validates the plugin manifest.
4. The backend stores the plugin in the registry repository.
5. The backend emits `plugin.registered`.
6. Plugin Registry History reads `GET /api/plugins` and refreshes automatically after plugin registration.
7. Press **Enable Plugin** or **Disable Plugin** in Plugin Registry History to change Plugin-managed Business Unit status.
8. The backend emits plugin lifecycle events and records governance audit evidence.

## First Audit Flow

1. Press **Record Audit Decision**.
2. The frontend sends `POST /api/audit`.
3. The backend records a governance decision with evidence.
4. The backend emits `audit.recorded`.

## DB MARIAM Runtime Storage

Docker uses `MARIAM_AUDIT_STORE=postgres`, so governance decisions are stored in the `audit_log` table.
Docker uses `MARIAM_RUNTIME_OBJECT_STORE=postgres`, so runtime objects are stored in the `runtime_objects` table.
Docker uses `MARIAM_EVENT_STORE=postgres`, so runtime events are stored in the `runtime_events` table.
Docker uses `MARIAM_PLUGIN_STORE=postgres`, so registered plugins are stored in the `plugin_manifests` table.
Docker uses `MARIAM_MISSION_STORE=postgres`, so mission history is stored in the `missions` and `mission_steps` tables.
Docker uses `MARIAM_AI_RESOURCE_ROUTE_STORE=postgres`, so AI resource route decisions are stored in the `ai_resource_routes` table.
Local tests use the default in-memory repository unless that setting is explicitly changed.

## Frontend API Configuration

The Command Center uses `VITE_MARIAM_API_BASE_URL` for all backend calls.
The default is `http://localhost:8000`, and Docker Compose passes the same value to the frontend service.

## Current Completion Estimate

- Full Mariam Enterprise OS target: about 25%.
- Executable rebuild foundation target: about 96%.
