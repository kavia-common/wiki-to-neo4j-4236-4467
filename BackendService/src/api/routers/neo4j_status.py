from fastapi import APIRouter
from src.services.neo4j_client import Neo4jClient

router = APIRouter(tags=["status"])

@router.get(
    "/status/neo4j",
    summary="Neo4j connectivity status",
)
def neo4j_status():
    """
    PUBLIC_INTERFACE
    Report Neo4j connectivity status using driver.verify_connectivity().

    Returns:
        JSON: {"connected": bool, "error": str|null}
    Notes:
        Authentication behavior follows existing design for status endpoints (public health/status style).
    """
    client = Neo4jClient()
    ok, err = client.ping()
    return {"connected": ok, "error": err}
