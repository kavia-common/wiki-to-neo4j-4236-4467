from fastapi import APIRouter, Depends, HTTPException, status
from ..auth import get_current_subject
from ..models import ErrorResponse
from src.core.jobs import JobStore, JobNotFound
from src.core.logging import get_logger

router = APIRouter(tags=["error"])
logger = get_logger(__name__)

@router.get(
    "/error/{job_id}",
    response_model=ErrorResponse,
    summary="Retrieve error details for a failed job.",
)
def get_error(job_id: str, subject: str = Depends(get_current_subject)) -> ErrorResponse:
    """
    PUBLIC_INTERFACE
    Get job error details if failed. Requires Bearer token.
    """
    try:
        job = JobStore.get_job(job_id, subject)
    except JobNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job["status"] != "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job has not failed")
    return ErrorResponse(
        job_id=job_id,
        error_code=job.get("error_code", "unknown_error"),
        message=job.get("error_message", "Unknown error"),
        details=job.get("error_details"),
    )
