# BackendService

FastAPI backend for submitting Wikipedia extraction jobs and ingesting them into Neo4j. Includes JWT bearer auth, background processing, deterministic extraction (no LLM required), optional OpenAI embeddings, and optional Neo4j upsert.

## Run

- Create `.env` from `.env.example` and set secrets.
- Install deps:
  pip install -r requirements.txt
- Start server (binds 0.0.0.0:3001):
  uvicorn src.api.main:get_app --host 0.0.0.0 --port 3001 --reload

Health check:
GET /

Base API path:
- /api/v1

## Auth

Generate a token for testing:
```python
from src.api.auth import create_access_token
print(create_access_token("test-user"))
```
Then include:
Authorization: Bearer <token>

## Endpoints

- POST /api/v1/input/submit
- GET /api/v1/status/{job_id}
- GET /api/v1/result/{job_id}
- GET /api/v1/error/{job_id}

## Environment

See `.env.example` for available variables.

## Notes

- If Neo4j or OpenAI are not configured, the pipeline still runs and logs NOOP upserts / stub embeddings.
