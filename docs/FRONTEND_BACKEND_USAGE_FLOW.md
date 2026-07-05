# Mariam Frontend And Backend Usage Flow

## Purpose
This report explains the first executable Mariam rebuild flow from a frontend button click to backend mission creation and visible result.

## Current Executable Scope
The current codebase is the first foundation, not the full Mariam platform. It includes:

- FastAPI backend.
- React Command Center frontend.
- Plugin manifest runtime contract.
- Runtime event bus.
- Mission API.
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
9. The backend returns the mission JSON.
10. The frontend renders:
   - mission id
   - mission status
   - data platform
   - each step and actor

## Backend Layers Used
- API layer: `backend/app/api/missions.py`
- AI Resource API layer: `backend/app/api/ai_resources.py`
- Mission model: `backend/app/core/missions.py`
- Mission service: `backend/app/services/missions.py`
- AI Resource Manager: `backend/app/services/ai_resources.py`
- Event bus: `backend/app/core/events.py`
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
- The backend creates a governed mission plan.
- The mission references `DB MARIAM`.
- The event bus records mission creation.
- AI capability routing can select a governed provider such as Ollama without making Ollama the system core.
- Every AI resource route returns a `route_id`, `created_at`, selected provider, policy, and fallback list.
- `GET /api/ai-resources/routes` returns the runtime route history for audit and UI review.
- Tests pass.
- Frontend production build succeeds.
