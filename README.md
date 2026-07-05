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

0. Open the Command Center to automatically call `GET /api/runtime/summary`; press **Refresh System Status** to reload backend health, runtime, governance, mission, plugin, audit, and AI routing counts from the same Command Center API.

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

## First AI Resource Flow

1. Press **Route AI Capability**.
2. The frontend sends `POST /api/ai-resources/route`.
3. The backend selects an approved provider for the requested capability.
4. The backend records a route decision with `route_id` and `created_at`.
5. The route decision includes `requested_by` and the `DB MARIAM` data boundary.
6. Local-first chat routing selects Ollama as a model runtime provider, not as Mariam Core.
7. The route history is available from `GET /api/ai-resources/routes`.
8. Route storage is behind a repository boundary so tests can use memory while Docker writes to Postgres in `DB MARIAM`.

## First Runtime Object Flow

1. Press **Register Runtime Object**.
2. The frontend sends `POST /api/runtime-objects`.
3. The backend registers an enabled provider runtime object.
4. The backend emits `runtime_object.registered`.
5. The backend records an audit decision for the registration.

## First Plugin Registry Flow

1. Press **Register CRM Plugin**.
2. The frontend sends `POST /api/plugins`.
3. The backend validates the plugin manifest.
4. The backend stores the plugin in the registry repository.
5. The backend emits `plugin.registered`.

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

- Full Mariam Enterprise OS target: about 24%.
- Executable rebuild foundation target: about 90%.
