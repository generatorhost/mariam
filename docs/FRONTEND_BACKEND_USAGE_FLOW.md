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
3. The backend reads health, runtime objects, plugins, missions, AI routes, audit records, runtime events, and the latest runtime activity through the current repository configuration.
4. The backend returns one Command Center summary payload.
5. The frontend displays the runtime summary in one compact status grid and shows the latest runtime activity feed below it.
6. If the user presses `Refresh System Status`, the frontend repeats the same call and replaces the counts.
7. After any successful action button, the frontend automatically refreshes the same summary so the counts match the latest backend state.

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
14. The frontend refreshes `GET /api/runtime/summary` so mission and event counts update automatically.
15. If the mission is `awaiting_approval`, the frontend shows `Approve Mission` and `Reject Mission`.
16. The Mission History panel refreshes `GET /api/missions` and displays the new mission in the recent list.

### Approve CRM Mission
1. User presses `Approve Mission`.
2. The frontend sends:

```http
POST /api/missions/{mission_id}/approve
```

with:

```json
{
  "approved_by": "command-center-governance",
  "evidence": {
    "review": "Approved from Command Center mission panel"
  }
}
```

3. The backend loads the mission through the mission repository.
4. The backend updates the mission status to `approved`.
5. The backend records `mission.approve` in the audit log with the governance evidence.
6. The backend emits `mission.approved`.
7. The frontend replaces the mission result with the approved mission state.
8. The frontend refreshes `GET /api/runtime/summary` so audit and event activity update automatically.
9. The Mission History panel refreshes and shows the mission as `approved`.

### Reject CRM Mission
1. User presses `Reject Mission`.
2. The frontend sends:

```http
POST /api/missions/{mission_id}/reject
```

with:

```json
{
  "rejected_by": "command-center-governance",
  "reason": "Rejected from Command Center governance panel for revision.",
  "evidence": {
    "review": "Rejected before delivery export"
  }
}
```

3. The backend loads the mission through the mission repository.
4. The backend updates the mission status to `rejected`.
5. The backend records `mission.reject` in the audit log with rejection evidence.
6. The backend emits `mission.rejected`.
7. The frontend replaces the mission result with the rejected mission state.
8. The frontend refreshes `GET /api/runtime/summary` so audit and event activity update automatically.
9. The Mission History panel refreshes and shows the mission as `rejected`.

### Review Mission History
1. User opens the Command Center.
2. The frontend automatically sends:

```http
GET /api/missions
```

3. The backend reads mission records through the configured mission repository.
4. The frontend displays the most recent mission records with status, Chief Agent, request, and creation time.
5. If the user presses `Refresh Mission History`, the frontend repeats the same call.
6. If a mission is `awaiting_approval`, the history record exposes `Approve` and `Reject`.
7. Pressing either action calls the same mission governance endpoints, refreshes mission history, and refreshes the Command Center summary.

### Route AI Capability
1. User presses `Route AI Capability`.
2. The frontend sends `POST /api/ai-resources/route`.
3. The backend selects a provider for the requested capability.
4. The result displays provider, route id, fallbacks, requester, and `DB MARIAM`.
5. The frontend refreshes the Command Center summary so AI route and event counts update automatically.
6. The AI Route History panel refreshes and shows the provider routing decision.

### Review AI Route History
1. User opens the Command Center.
2. The frontend automatically sends:

```http
GET /api/ai-resources/routes
```

3. The backend reads AI route decisions through the configured AI resource route repository.
4. The frontend displays recent routing decisions with provider, capability, reason, and time.
5. If the user presses `Refresh AI Route History`, the frontend repeats the same call.

### Register Runtime Object
1. User presses `Register Runtime Object`.
2. The frontend sends `POST /api/runtime-objects`.
3. The backend creates an enabled runtime object.
4. The backend emits `runtime_object.registered`.
5. The backend records an audit decision for the registration.
6. The frontend displays object id, status, type, version, and `DB MARIAM`.
7. The frontend refreshes the Command Center summary so runtime object, audit, and event counts update automatically.
8. The Runtime Object History panel refreshes and shows the registered runtime object.

### Review Runtime Object History
1. User opens the Command Center.
2. The frontend automatically sends:

```http
GET /api/runtime-objects
```

3. The backend reads runtime objects through the configured runtime object repository.
4. The frontend displays recent runtime objects with name, type, status, version, and creation time.
5. If the user presses `Refresh Runtime Objects`, the frontend repeats the same call.

### Disable Runtime Object
1. User presses `Disable` on an enabled runtime object.
2. The frontend sends:

```http
POST /api/runtime-objects/{object_id}/disable
```

3. The backend loads the runtime object from the runtime object repository.
4. If the object is a provider, the backend requires a matching `disable` impact analysis stamp.
5. If the impact risk is high, the backend requires a matching approval stamp.
6. The backend changes status to `disabled` and updates the timestamp.
7. The backend records `runtime_object.disable` in the audit log with actor, reason, evidence, and `DB MARIAM`.
8. The backend emits `runtime_object.disable`.
9. The frontend refreshes Runtime Object History and the Command Center summary.

### Enable Runtime Object
1. User presses `Enable` on a disabled runtime object.
2. The frontend sends:

```http
POST /api/runtime-objects/{object_id}/enable
```

3. The backend loads the runtime object from the runtime object repository.
4. The backend requires a successful validation stamp in the runtime object manifest.
5. The backend changes status to `enabled` and updates the timestamp.
6. The backend records `runtime_object.enable` in the audit log with actor, reason, evidence, and `DB MARIAM`.
7. The backend emits `runtime_object.enable`.
8. The frontend refreshes Runtime Object History and the Command Center summary.

### Soft Delete Runtime Object
1. User presses `Delete` on a runtime object that is not already deleted.
2. The frontend sends:

```http
POST /api/runtime-objects/{object_id}/delete
```

3. The backend loads the runtime object from the runtime object repository.
4. If the object is a provider, the backend requires a matching `delete` impact analysis stamp.
5. If the impact risk is high, the backend requires a matching approval stamp.
6. The backend changes status to `deleted`; the database row remains available for audit and rollback.
7. The backend records `runtime_object.soft_delete` with actor, reason, evidence, and `DB MARIAM`.
8. The backend emits `runtime_object.soft_delete`.
9. The frontend refreshes Runtime Object History and replaces action buttons with `Restore`.

### Restore Runtime Object
1. User presses `Restore` on a soft-deleted runtime object.
2. The frontend sends:

```http
POST /api/runtime-objects/{object_id}/restore
```

3. The backend loads the runtime object from the runtime object repository.
4. The backend changes status to `disabled`, requiring a deliberate `Enable` action before use.
5. The backend records `runtime_object.restore` with actor, reason, evidence, and `DB MARIAM`.
6. The backend emits `runtime_object.restore`.
7. The frontend refreshes Runtime Object History and the Command Center summary.

### Upgrade Runtime Object
1. User presses `Upgrade` on a runtime object that is not deleted.
2. The frontend sends:

```http
PATCH /api/runtime-objects/{object_id}
```

3. The backend loads the runtime object from the runtime object repository.
4. The backend merges governed manifest updates and applies the requested version.
5. The backend records `runtime_object.patch` with actor, reason, evidence, manifest updates, and `DB MARIAM`.
6. The backend emits `runtime_object.patch`.
7. The frontend refreshes Runtime Object History and the Command Center summary.

### Rollback Runtime Object
1. User presses `Rollback` on a runtime object with a stored rollback point.
2. The frontend sends:

```http
POST /api/runtime-objects/{object_id}/rollback
```

3. The backend loads the runtime object from the runtime object repository.
4. The backend restores the previous name, version, and manifest snapshot.
5. The backend records `runtime_object.rollback` with actor, reason, rollback point, evidence, and `DB MARIAM`.
6. The backend emits `runtime_object.rollback`.
7. The frontend refreshes Runtime Object History and the Command Center summary.

### Export Runtime Object As DNA
1. User presses `Export DNA` on a runtime object.
2. The frontend sends:

```http
POST /api/runtime-objects/{object_id}/export-dna
```

3. The backend loads the runtime object from the runtime object repository.
4. The backend builds a `mariam.runtime_object.dna.v1` package from the runtime object metadata and manifest.
5. The backend excludes internal rollback stack data from the exported manifest.
6. The backend records `runtime_object.export_dna` with actor, reason, DNA package id, evidence, and `DB MARIAM`.
7. The backend emits `runtime_object.export_dna`.
8. The frontend displays the DNA package id and schema.

### Import Runtime Object DNA
1. User presses `Import Last DNA` after a successful export.
2. The frontend sends:

```http
POST /api/runtime-objects/import-dna
```

3. The backend validates the DNA package schema.
4. The backend creates a new runtime object from the package with status `disabled`.
5. The backend records source DNA metadata in the imported object's manifest.
6. The backend records `runtime_object.import_dna` with actor, reason, source package id, evidence, and `DB MARIAM`.
7. The backend emits `runtime_object.import_dna`.
8. The frontend shows the imported object as ready for governance review and refreshes Runtime Object History.

### Validate Runtime Object
1. User presses `Validate` on a runtime object.
2. The frontend sends:

```http
POST /api/runtime-objects/{object_id}/validate
```

3. The backend loads the runtime object from the runtime object repository.
4. The backend runs governance checks for deleted status, manifest presence, version presence, provider metadata, and DNA import review state.
5. The backend returns a validation report with pass/fail checks.
6. When validation passes, the backend stores a validation stamp in the runtime object manifest.
7. The backend records `runtime_object.validate` as approved or rejected in the audit log.
8. The backend emits `runtime_object.validate`.
9. The frontend displays the validation id and check count.

### Analyze Runtime Object Impact
1. User presses `Analyze Impact` on a runtime object.
2. The frontend sends:

```http
POST /api/runtime-objects/{object_id}/impact-analysis
```

3. The backend loads the runtime object from the runtime object repository.
4. The backend estimates affected capabilities, dependencies, governance notes, and risk level.
5. The backend stores an impact analysis stamp in the runtime object manifest.
6. The backend records `runtime_object.impact_analysis` in the audit log.
7. The backend emits `runtime_object.impact_analysis`.
8. The frontend displays the impact id, risk level, and affected counts.

### Approve Runtime Object Change
1. User presses `Approve Change` after impact analysis.
2. The frontend sends:

```http
POST /api/runtime-objects/{object_id}/approve-change
```

3. The backend verifies that a matching impact analysis exists for the intended action.
4. The backend stores a change approval stamp in the runtime object manifest.
5. The backend records `runtime_object.approve_change` in the audit log.
6. The backend emits `runtime_object.approve_change`.
7. The frontend displays the approval id and intended action.

### Register CRM Plugin
1. User presses `Register CRM Plugin`.
2. The frontend sends `POST /api/plugins`.
3. The backend validates the plugin manifest contract.
4. The backend stores the plugin in the configured plugin repository.
5. The backend emits `plugin.registered`.
6. The frontend displays plugin id, dashboard route, Chief Agent, and data boundary.
7. The frontend refreshes the Command Center summary so plugin and event counts update automatically.
8. The Plugin Registry History panel refreshes and shows the registered Plugin-managed Business Unit.

### Review Plugin Registry History
1. User opens the Command Center.
2. The frontend automatically sends:

```http
GET /api/plugins
```

3. The backend reads registered plugin manifests through the runtime registry.
4. The frontend displays recent registered plugins with name, status, version, Chief Agent, dashboard route, and data boundary.
5. If the user presses `Refresh Plugin Registry`, the frontend repeats the same call.

### Validate Plugin
1. User presses `Validate Plugin` on a Plugin-managed Business Unit.
2. The frontend sends:

```http
POST /api/plugins/{plugin_id}/validate
```

3. The backend checks the plugin dashboard route, API prefix, permissions, tests, Chief Agent, and data boundary.
4. The backend stores a validation stamp in the plugin manifest.
5. The backend records `plugin.validate` in the audit log.
6. The backend emits `plugin.validate`.
7. The frontend displays the validation id and check count.
8. The Plugin Registry History panel refreshes and shows the validation stamp.

### Enable Plugin
1. User presses `Enable Plugin` on a Plugin-managed Business Unit.
2. The frontend sends:

```http
POST /api/plugins/{plugin_id}/enable
```

3. The backend requires a successful plugin validation stamp.
4. If validation is missing, the backend rejects the activation with a governance error.
5. If validation passed, the backend updates the plugin status to `enabled`.
6. The backend records `plugin.enable` in the audit log.
7. The backend emits `plugin.enable`.
8. The frontend refreshes Plugin Registry History and the Command Center summary.

### Disable Plugin
1. User presses `Disable Plugin` on an enabled Plugin-managed Business Unit.
2. The frontend sends:

```http
POST /api/plugins/{plugin_id}/disable
```

3. The backend updates the plugin status to `disabled`.
4. The backend records `plugin.disable` in the audit log.
5. The backend emits `plugin.disable`.
6. The frontend refreshes Plugin Registry History and the Command Center summary.

### Record Audit Decision
1. User presses `Record Audit Decision`.
2. The frontend sends `POST /api/audit`.
3. The backend stores the approval decision and evidence.
4. The backend emits `audit.recorded`.
5. The frontend displays audit id, action, target, actor, and `DB MARIAM`.
6. The frontend refreshes the Command Center summary so audit and event counts update automatically.

### Review Audit History
1. User opens the Command Center.
2. The frontend automatically sends:

```http
GET /api/audit
```

3. The backend reads audit records through the configured audit repository.
4. The frontend displays recent governance decisions with decision, action, actor, target, and time.
5. If the user presses `Refresh Audit History`, the frontend repeats the same call.
6. Any action that records audit evidence refreshes this panel through the shared Command Center refresh signal.

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
- mission approval
- mission rejection
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
- Frontend Audit History displays recent governance decisions.
- Runtime objects are available from `GET /api/runtime-objects`.
- Frontend Runtime Object History displays recent governed runtime objects.
- Runtime objects can be disabled and enabled through governed frontend actions.
- Runtime objects require successful validation before enable.
- Runtime objects can be soft-deleted and restored without losing audit history.
- Runtime objects can be patched/upgraded through a governed endpoint.
- Runtime object upgrades can be rolled back to the previous manifest snapshot.
- Runtime objects can be exported as governed DNA packages.
- Runtime object DNA packages can be imported as disabled runtime objects for review.
- Runtime objects can be validated before activation or delivery.
- Successful validation is persisted as a runtime object manifest stamp.
- Runtime object impact can be analyzed before enable, disable, delete, or rollback.
- Provider disable/delete requires a matching impact analysis stamp and approval when the impact is high.
- Registered plugins are available from `GET /api/plugins`.
- Frontend Plugin Registry History displays registered Plugin-managed Business Units.
- Plugins can be enabled and disabled through governed lifecycle actions.
- Plugins require successful validation before enable.
- Successful plugin validation is persisted as a plugin manifest stamp.
- The Command Center status panel reads aggregated counts and recent runtime activity from `GET /api/runtime/summary`.
- The backend creates a governed mission plan.
- The backend can approve a mission through a governance endpoint.
- The backend can reject a mission through a governance endpoint.
- The mission references `DB MARIAM`.
- Mission history is available from `GET /api/missions`.
- Frontend Mission History displays recent mission repository records.
- Frontend Mission History can approve or reject pending mission records.
- The event bus records mission creation.
- AI capability routing can select a governed provider such as Ollama without making Ollama the system core.
- Every AI resource route returns a `route_id`, `created_at`, `requested_by`, `DB MARIAM`, selected provider, policy, and fallback list.
- `GET /api/ai-resources/routes` returns the runtime route history for audit and UI review.
- Frontend AI Route History displays recent provider routing decisions.
- AI route storage is accessed through a repository boundary.
- Local tests use the memory repository; Docker sets `MARIAM_AI_RESOURCE_ROUTE_STORE=postgres` and writes route decisions into `DB MARIAM`.
- Tests pass.
- Frontend production build succeeds.
- Frontend API calls use one configurable base URL.
- Frontend status panel auto-loads, manually refreshes, and refreshes after successful actions through one Command Center summary API.

## Current Completion Estimate
- Full Mariam Enterprise OS target: about 25%.
- Executable rebuild foundation target: about 96%.
