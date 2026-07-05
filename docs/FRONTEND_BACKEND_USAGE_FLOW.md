# Mariam Frontend And Backend Usage Flow

## Purpose
This report explains the first executable Mariam rebuild flow from a frontend button click to backend mission creation and visible result.

## Current Executable Scope
The current codebase is the first foundation, not the full Mariam platform. It includes:

- FastAPI backend.
- React Command Center frontend.
- Audit Log API and repository boundary.
- Runtime Object API and repository boundary.
- Plugin manifest runtime contract.
- Plugin registry repository boundary.
- Runtime event bus.
- Runtime event repository boundary.
- Mission API.
- Mission repository boundary.
- DB MARIAM migration foundation using the technical database identifier `db_mariam`.
- Docker Compose stack for backend, frontend, PostgreSQL, Redis, and MinIO.
- Backend API tests.

## Run The Project
Use Docker Compose from the repository root:

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

The frontend reads `VITE_MARIAM_API_BASE_URL` for backend calls. Docker Compose sets it to `http://localhost:8000`.

## Button To Result Flow

### Load And Refresh System Status
1. User opens the Command Center.
2. The frontend automatically sends `GET /api/runtime/summary`.
3. The backend reads health, runtime objects, plugins, missions, AI routes, audit records, and runtime events through the current repository configuration.
4. The backend returns one Command Center summary payload.
5. The frontend displays the runtime summary in one compact status grid.
6. If the user presses `Refresh System Status`, the frontend repeats the same call and replaces the counts.

### Start CRM Mission
1. User opens the Command Center.
2. User presses `Start CRM Mission`.
3. The React frontend sends:

```http
POST /api/missions
```

with:

```json
{
  "plugin_id": "crm",
  "user_request": "Create a follow-up plan for a qualified lead",
  "requested_by": "command-center"
}
```

4. FastAPI receives the request in the missions router.
5. The request is validated by the `MissionRequest` model.
6. `MissionService` creates a mission plan.
7. The mission plan records:
   - plugin id
   - user request
   - requesting actor
   - Chief Agent
   - mission steps
   - governance gate
   - `DB MARIAM` as the data platform boundary
8. The runtime event bus emits `mission.created`.
9. The event is saved through the configured runtime event repository.
10. The mission is saved through the configured mission repository.
11. Docker stores the mission in `missions` and its ordered steps in `mission_steps`.
12. The backend returns the mission JSON.
13. The frontend renders:
   - mission id
   - mission status
   - data platform
   - each step and actor

### Route AI Capability
1. User presses `Route AI Capability`.
2. The frontend sends `POST /api/ai-resources/route`.
3. The backend selects a provider for the requested capability.
4. The result displays provider, route id, fallbacks, requester, and `DB MARIAM`.

### Register Runtime Object
1. User presses `Register Runtime Object`.
2. The frontend sends `POST /api/runtime-objects`.
3. The backend creates an enabled runtime object.
4. The backend emits `runtime_object.registered`.
5. The backend records an audit decision for the registration.
6. The frontend displays object id, status, type, version, and `DB MARIAM`.

### Register CRM Plugin
1. User presses `Register CRM Plugin`.
2. The frontend sends `POST /api/plugins`.
3. The backend validates the plugin manifest contract.
4. The backend stores the plugin in the configured plugin repository.
5. The backend emits `plugin.registered`.
6. The frontend displays plugin id, dashboard route, Chief Agent, and data boundary.

### Record Audit Decision
1. User presses `Record Audit Decision`.
2. The frontend sends `POST /api/audit`.
3. The backend stores the approval decision and evidence.
4. The backend emits `audit.recorded`.
5. The frontend displays audit id, action, target, actor, and `DB MARIAM`.

## Backend Layers Used
- API layer: `backend/app/api/missions.py`
- Audit API layer: `backend/app/api/audit.py`
- Audit repository: `backend/app/repositories/audit.py`
- AI Resource API layer: `backend/app/api/ai_resources.py`
- Runtime Object API layer: `backend/app/api/runtime_objects.py`
- Runtime Object repository: `backend/app/repositories/runtime_objects.py`
- Plugin API layer: `backend/app/api/plugins.py`
- Plugin repository: `backend/app/repositories/plugins.py`
- Mission model: `backend/app/core/missions.py`
- Mission service: `backend/app/services/missions.py`
- Mission repository: `backend/app/repositories/missions.py`
- AI Resource Manager: `backend/app/services/ai_resources.py`
- Event bus: `backend/app/core/events.py`
- Event repository: `backend/app/repositories/events.py`
- Runtime wiring: `backend/app/dependencies.py`
- Frontend API client: `frontend/src/main.jsx`

## Database Layer
The official display name is `DB MARIAM`.

The technical PostgreSQL database identifier is:

```text
db_mariam
```

The migration adds:

- `audit_log`
- `runtime_objects`
- `missions`
- `mission_steps`

These tables are the first executable Mission DB boundary.
Docker sets `MARIAM_AUDIT_STORE=postgres` and writes governance decisions into `DB MARIAM`.
Docker sets `MARIAM_RUNTIME_OBJECT_STORE=postgres` and writes runtime objects into `DB MARIAM`.
Docker sets `MARIAM_EVENT_STORE=postgres` and writes runtime event history into `DB MARIAM`.
Docker sets `MARIAM_PLUGIN_STORE=postgres` and writes plugin registry history into `DB MARIAM`.
Local tests use the memory mission repository; Docker sets `MARIAM_MISSION_STORE=postgres` and writes mission history into `DB MARIAM`.

## Result Contract
A successful mission response contains:

- `mission_id`
- `plugin_id`
- `status`
- `chief_agent`
- `governance_gate`
- `data_platform`
- `steps`
- `created_at`

## Test Coverage
The backend tests verify:

- root architecture pointer
- health endpoint
- plugin manifest registration
- repository CRM manifest contract
- official terminology
- mission creation
- mission event emission

Run:

```bash
cd backend
pytest
```

## Acceptance Criteria
- Opening the frontend loads a real backend Command Center summary.
- Pressing each frontend action button has a real backend result.
- Frontend exposes status, mission, AI routing, plugin registration, runtime object, and audit flows.
- Audit records are available from `GET /api/audit`.
- Runtime objects are available from `GET /api/runtime-objects`.
- Registered plugins are available from `GET /api/plugins`.
- The Command Center status panel reads aggregated counts from `GET /api/runtime/summary`.
- The backend creates a governed mission plan.
- The mission references `DB MARIAM`.
- Mission history is available from `GET /api/missions`.
- The event bus records mission creation.
- AI capability routing can select a governed provider such as Ollama without making Ollama the system core.
- Every AI resource route returns a `route_id`, `created_at`, `requested_by`, `DB MARIAM`, selected provider, policy, and fallback list.
- `GET /api/ai-resources/routes` returns the runtime route history for audit and UI review.
- AI route storage is accessed through a repository boundary.
- Local tests use the memory repository; Docker sets `MARIAM_AI_RESOURCE_ROUTE_STORE=postgres` and writes route decisions into `DB MARIAM`.
- Tests pass.
- Frontend production build succeeds.
- Frontend API calls use one configurable base URL.
- Frontend status panel auto-loads and refreshes live backend counts through one Command Center summary API.

## Current Completion Estimate
- Full Mariam Enterprise OS target: about 24%.
- Executable rebuild foundation target: about 90%.
