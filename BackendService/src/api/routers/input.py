from fastapi import APIRouter, BackgroundTasks, Depends

from ..auth import get_current_subject
from ..models import InputSubmission, StatusResponse
from src.core.jobs import JobStore, JobStatus, queue_job
from src.core.logging import get_logger

router = APIRouter(tags=["input"])

logger = get_logger(__name__)

@router.post(
    "/input/submit",
    response_model=StatusResponse,
    summary="Submit a Wikipedia page URL or topic name for extraction.",
)
def submit_input(
    payload: InputSubmission,
    background_tasks: BackgroundTasks,
    subject: str = Depends(get_current_subject),
) -> StatusResponse:
    """
    PUBLIC_INTERFACE
    Submit an extraction job. Requires Bearer token.
    """
    job_id = JobStore.create_job(owner=subject)
    logger.info(f"User {subject} submitted job {job_id} for {payload.input_type}:{payload.value}")
    # queue background processing
    background_tasks.add_task(queue_job, job_id=job_id, submission=payload.model_dump())
    return StatusResponse(job_id=job_id, status=JobStatus.pending.value, progress=0.0)
