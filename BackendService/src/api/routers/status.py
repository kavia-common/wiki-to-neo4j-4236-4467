from fastapi import APIRouter, Depends, HTTPException, status
from ..auth import get_current_subject
from ..models import StatusResponse
from src.core.jobs import JobStore, JobNotFound
from src.core.logging import get_logger

router = APIRouter(tags=["status"])
logger = get_logger(__name__)

@router.get(
    "/status/{job_id}",
    response_model=StatusResponse,
    summary="Retrieve status of extraction/ingestion job.",
)
def get_status(job_id: str, subject: str = Depends(get_current_subject)) -> StatusResponse:
    """
    PUBLIC_INTERFACE
    Get current job status. Requires Bearer token.
    """
    try:
        job = JobStore.get_job(job_id, subject)
    except JobNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return StatusResponse(job_id=job_id, status=job["status"], progress=job.get("progress", 0.0))
