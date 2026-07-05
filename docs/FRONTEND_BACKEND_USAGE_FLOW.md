# Mariam Frontend And Backend Usage Flow

## Purpose
This report explains the first executable Mariam rebuild flow from a frontend button click to backend mission creation and visible result.

## Current Executable Scope
The current codebase is the first foundation, not the full Mariam platform. It includes:

- FastAPI backend.
- React Command Center frontend.
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

## Button To Result Flow
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

## Backend Layers Used
- API layer: `backend/app/api/missions.py`
- AI Resource API layer: `backend/app/api/ai_resources.py`
- Plugin API layer: `backend/app/api/plugins.py`
- Plugin repository: `backend/app/repositories/plugins.py`
- Mission model: `backend/app/core/missions.py`
- Mission service: `backend/app/services/missions.py`
- Mission repository: `backend/app/repositories/missions.py`
- AI Resource Manager: `backend/app/services/ai_resources.py`
- Event bus: `backend/app/core/events.py`
- Event repository: `backend/app/repositories/events.py`
- Runtime wiring: `backend/app/dependencies.py`

## Database Layer
The official display name is `DB MARIAM`.

The technical PostgreSQL database identifier is:

```text
db_mariam
```

The migration adds:

- `missions`
- `mission_steps`

These tables are the first executable Mission DB boundary.
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
- Pressing the frontend button has a real backend result.
- Registered plugins are available from `GET /api/plugins`.
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

## Current Completion Estimate
- Full Mariam Enterprise OS target: about 19%.
- Executable rebuild foundation target: about 76%.
