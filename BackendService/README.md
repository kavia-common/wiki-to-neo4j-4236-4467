# BackendService

FastAPI backend for submitting Wikipedia extraction jobs and ingesting them into Neo4j. The service includes JWT bearer authentication, background processing, deterministic extraction (no LLM required), optional OpenAI embeddings, and optional Neo4j upsert.

## Architecture Overview

The BackendService is organized into several layers:

- API (FastAPI):
  - Entry point in src.api.main defines the application, CORS configuration, health check, and mounts the versioned routers under /api/v1.
  - Routers under src.api.routers expose the public endpoints:
    - input.py: POST /api/v1/input/submit to create a job.
    - status.py: GET /api/v1/status/{job_id} to retrieve status.
    - result.py: GET /api/v1/result/{job_id} to retrieve results.
    - error.py: GET /api/v1/error/{job_id} to retrieve error details.
  - Authentication in src.api.auth uses HTTP Bearer with JWTs. Tokens are validated for signature, issuer, audience, and expiration.
- Background jobs:
  - The in-memory JobStore (src.core.jobs) tracks job metadata and results keyed by job_id.
  - Jobs are queued using FastAPI BackgroundTasks and executed by queue_job, which runs the pipeline and updates progress and results.
- Extraction pipeline (LangChain-like):
  - src.services.langchain_pipeline.ExtractionPipeline implements a deterministic heuristic extractor for entities and relationships, an embedding step, and graph upsert orchestration.
  - src.services.embedding_provider.EmbeddingProvider provides deterministic stub embeddings by default, or uses OpenAI if OPENAI_API_KEY is configured.
- Neo4j client:
  - src.services.neo4j_client.Neo4jClient establishes a connection when NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD are set. If not configured or connection fails, it logs and performs no-op upserts so the pipeline can still complete.

## Setup and Run

1) Create a .env file from .env.example and set secrets as needed.
2) Install dependencies:
   pip install -r requirements.txt
3) Start the server bound to 0.0.0.0:3001:
   uvicorn src.api.main:get_app --host 0.0.0.0 --port 3001 --reload

- Health check: GET /
- Base API path prefix: /api/v1
- OpenAPI schema: GET /openapi.json
- Swagger UI: GET /docs
- ReDoc: GET /redoc

Note on port and CORS:
- The server listens on port 3001 by default as shown in the run command above.
- CORS is currently permissive (allow_origins=["*"]) in src.api.main. For production, restrict this to trusted frontend origins using the CORS_ALLOW_ORIGINS environment variable pattern shown in .env.example (documented below).

## Environment Variables

Settings are defined in src.core.config.Settings and loaded from environment variables.

- APP_NAME: Service name. Example: Wiki to Neo4j Extraction API
- API_PREFIX: Base path for APIs. Example: /api/v1
- HOST: Host bind address. Example: 0.0.0.0
- PORT: Listening port. Example: 3001

Authentication (JWT):
- JWT_SECRET: Secret key for signing JWTs. Example: dev-secret-change-me
- JWT_ALGORITHM: Signing algorithm. Example: HS256
- JWT_EXPIRE_MINUTES: Token expiration in minutes. Example: 60
- JWT_ISSUER: Expected JWT issuer value. Example: wiki-backend
- JWT_AUDIENCE: Expected JWT audience value. Example: wiki-clients

Embeddings:
- OPENAI_API_KEY: Optional. If set, embeddings are generated with OpenAI text-embedding-3-small. If not set, the service uses deterministic stub embeddings. Example: sk-...

Neo4j:
- NEO4J_URI: Bolt URI to Neo4j. Example: bolt://localhost:7687
- NEO4J_USER: Neo4j username. Example: neo4j
- NEO4J_PASSWORD: Neo4j password. Example: neo4j_password

CORS:
- CORS_ALLOW_ORIGINS: Optional, comma-separated list of origins to allow. Example: http://localhost:5173,http://localhost:3000

Base path:
- BASE_PATH: Optional, not currently read by the code. The service uses API_PREFIX=/api/v1 directly. If a reverse proxy is used, ensure it routes correctly to the service’s root and preserves /api/v1. This variable is included for compatibility with deployment setups but is not consumed in code.

## Authentication and JWT Usage

All /api/v1 endpoints require an Authorization: Bearer <token> header. Tokens must be signed with JWT_SECRET, use JWT_ALGORITHM, and include claims sub, iss, aud, and exp consistent with Settings.

Generate a token for development:
```python
from src.api.auth import create_access_token
print(create_access_token("test-user"))
```
- The token’s sub is the user identifier and is used to scope job access (jobs are only visible to their owner).
- Ensure the .env values for JWT_ISSUER, JWT_AUDIENCE, and JWT_SECRET match those used by the token generator.

## Background Job Lifecycle and Limitations

- When a submission is accepted, a job_id is created with status pending.
- A FastAPI BackgroundTask invokes queue_job, which:
  - Marks status processing and starts work.
  - Fetches the Wikipedia content by topic or URL via WikiService.
  - Runs ExtractionPipeline to produce entities and relationships.
  - Generates embeddings for extracted entities using EmbeddingProvider.
  - Attempts to upsert data to Neo4j via Neo4jClient (no-op if not configured).
  - On success, updates status to completed and stores entities, relationships, and embeddings in memory.
  - On failure, updates status to failed and records error details.

Limitations:
- The JobStore is in-memory, so jobs and results do not persist across restarts and are not shared across instances.
- BackgroundTasks execute in-process with the web worker; for production, consider a durable queue and persistent store.
- If Neo4j is not configured, upserts are skipped but the pipeline still completes successfully with logged no-op operations.

## Curl Examples

All requests must include a valid Authorization header. Replace $TOKEN and $JOB_ID accordingly.

1) Submit a job:
```bash
curl -s -X POST "http://localhost:3001/api/v1/input/submit" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"input_type":"topic","value":"Python (programming language)"}'
```

2) Check job status:
```bash
curl -s -X GET "http://localhost:3001/api/v1/status/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN"
```

3) Retrieve results (after status is completed):
```bash
curl -s -X GET "http://localhost:3001/api/v1/result/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN"
```

4) Retrieve error details (if status is failed):
```bash
curl -s -X GET "http://localhost:3001/api/v1/error/$JOB_ID" \
  -H "Authorization: BearER $TOKEN"
```

## Notes

- If Neo4j or OpenAI are not configured, the pipeline still runs and logs no-op upserts or uses stub embeddings, respectively.
- The server listens on 0.0.0.0:3001 as shown in the run command. Adjust host/port with HOST/PORT environment variables if needed and update your deployment accordingly.
- For production CORS, set CORS_ALLOW_ORIGINS to a comma-separated list of allowed origins and update the CORS middleware to consume it if you customize the code.
