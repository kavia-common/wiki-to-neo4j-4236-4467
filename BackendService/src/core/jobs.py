import uuid
from typing import Dict, Any, Optional
from enum import Enum

from src.core.logging import get_logger
from src.services.wiki import WikiService
from src.services.langchain_pipeline import ExtractionPipeline
from src.services.embedding_provider import EmbeddingProvider
from src.services.neo4j_client import Neo4jClient

logger = get_logger(__name__)

class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

class JobNotFound(Exception):
    pass

class JobStore:
    """
    PUBLIC_INTERFACE
    Simple in-memory job store. For production, replace with persistent store.
    """
    _jobs: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create_job(cls, owner: str) -> str:
        job_id = str(uuid.uuid4())
        cls._jobs[job_id] = {
            "owner": owner,
            "status": JobStatus.pending.value,
            "progress": 0.0,
        }
        return job_id

    @classmethod
    def update(cls, job_id: str, **kwargs) -> None:
        if job_id not in cls._jobs:
            raise JobNotFound(job_id)
        cls._jobs[job_id].update(kwargs)

    @classmethod
    def get_job(cls, job_id: str, owner: Optional[str] = None) -> Dict[str, Any]:
        job = cls._jobs.get(job_id)
        if not job:
            raise JobNotFound(job_id)
        if owner is not None and job.get("owner") != owner:
            raise JobNotFound(job_id)
        return job

def queue_job(job_id: str, submission: Dict[str, Any]) -> None:
    """
    PUBLIC_INTERFACE
    Background task that executes the pipeline for a job.
    """
    logger.info(f"Starting job {job_id}")
    try:
        JobStore.update(job_id, status=JobStatus.processing.value, progress=0.05)
        wiki = WikiService()
        text = wiki.fetch(submission["input_type"], submission["value"])
        JobStore.update(job_id, progress=0.25)

        pipeline = ExtractionPipeline(EmbeddingProvider(), Neo4jClient())
        entities, relationships = pipeline.extract(text)
        JobStore.update(job_id, progress=0.6)

        embeddings = pipeline.embed_entities(entities)
        JobStore.update(job_id, progress=0.8)

        pipeline.upsert_to_graph(entities, relationships, embeddings)
        JobStore.update(
            job_id,
            status=JobStatus.completed.value,
            progress=1.0,
            entities=entities,
            relationships=relationships,
            embeddings=embeddings,
        )
        logger.info(f"Completed job {job_id}")
    except Exception as e:
        logger.exception("Job failed")
        JobStore.update(
            job_id,
            status=JobStatus.failed.value,
            error_code="pipeline_error",
            error_message=str(e),
            error_details={"type": type(e).__name__},
        )
