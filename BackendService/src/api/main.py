from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from .routers import input as input_router
from .routers import status as status_router
from .routers import result as result_router
from .routers import error as error_router
from .routers import neo4j_status as neo4j_status_router
from .auth import register_security_scheme

# Initialize application with metadata and versioned docs
app = FastAPI(
    title="Wiki to Neo4j Extraction API",
    description="RESTful API for submitting Wikipedia extraction jobs, tracking status, retrieving results, and error reporting. Secured with JWT authentication.",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public health check
@app.get("/", summary="Health Check", tags=["system"])
def health_check():
    """
    PUBLIC_INTERFACE
    Health check endpoint to verify service is running.
    Returns a simple JSON message.
    """
    return {"message": "Healthy"}

# API routers under /api/v1
API_PREFIX = "/api/v1"
app.include_router(input_router.router, prefix=API_PREFIX)
app.include_router(status_router.router, prefix=API_PREFIX)
app.include_router(result_router.router, prefix=API_PREFIX)
app.include_router(error_router.router, prefix=API_PREFIX)
app.include_router(neo4j_status_router.router, prefix=API_PREFIX)

# Enhance OpenAPI with bearer auth security scheme
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Register HTTP bearer auth scheme
    register_security_scheme(openapi_schema)
    # Ensure top-level security requirement aligns with spec
    openapi_schema["security"] = [{"bearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Entrypoint hint for running via uvicorn (served externally by orchestrator)
def get_app():
    """
    PUBLIC_INTERFACE
    Returns the FastAPI app instance for ASGI servers.
    """
    return app
