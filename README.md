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
7. The frontend displays the mission status and step-by-step result.
