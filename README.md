# Mariam AI Enterprise OS

This is the official code repository for Mariam AI Enterprise OS.

Mariam is being rebuilt from a documentation-driven architecture. The source of truth is:

https://github.com/generatorhost/Mariam-Architecture-Library

This repository now contains the first executable rebuild foundation:

- Backend API scaffold
- Frontend command center scaffold
- Database schema migrations
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

