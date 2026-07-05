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
- AI Resource Manager provider routing
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

1. Open the Command Center.
2. Press **Start CRM Mission**.
3. The frontend sends `POST /api/missions`.
4. The backend validates the request and creates a governed mission plan.
5. The mission records the Plugin Chief, runtime scheduling step, approval gate, and `DB MARIAM` data platform boundary.
6. The backend emits `mission.created`.
7. The mission is saved behind a repository boundary.
8. Docker stores mission history in the `missions` and ordered `mission_steps` tables.
9. The frontend displays the mission status and step-by-step result.

## First AI Resource Flow

1. Press **Route AI Capability**.
2. The frontend sends `POST /api/ai-resources/route`.
3. The backend selects an approved provider for the requested capability.
4. The backend records a route decision with `route_id` and `created_at`.
5. The route decision includes `requested_by` and the `DB MARIAM` data boundary.
6. Local-first chat routing selects Ollama as a model runtime provider, not as Mariam Core.
7. The route history is available from `GET /api/ai-resources/routes`.
8. Route storage is behind a repository boundary so tests can use memory while Docker writes to Postgres in `DB MARIAM`.

## DB MARIAM Runtime Storage

Docker uses `MARIAM_MISSION_STORE=postgres`, so mission history is stored in the `missions` and `mission_steps` tables.
Docker uses `MARIAM_AI_RESOURCE_ROUTE_STORE=postgres`, so AI resource route decisions are stored in the `ai_resource_routes` table.
Local tests use the default in-memory repository unless that setting is explicitly changed.
