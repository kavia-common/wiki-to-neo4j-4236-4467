from fastapi import APIRouter, Depends, HTTPException, status
from ..auth import get_current_subject
from ..models import ResultResponse
from src.core.jobs import JobStore, JobNotFound
from src.core.logging import get_logger

router = APIRouter(tags=["result"])
logger = get_logger(__name__)

@router.get(
    "/result/{job_id}",
    response_model=ResultResponse,
    summary="Retrieve extracted entities, relationships, and embeddings.",
)
def get_result(job_id: str, subject: str = Depends(get_current_subject)) -> ResultResponse:
    """
    PUBLIC_INTERFACE
    Get job results after completion. Requires Bearer token.
    """
    try:
        job = JobStore.get_job(job_id, subject)
    except JobNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job not completed")
    return ResultResponse(
        job_id=job_id,
        entities=job.get("entities", []),
        relationships=job.get("relationships", []),
        embeddings=job.get("embeddings", []),
    )
