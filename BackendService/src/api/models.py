from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# PUBLIC_INTERFACE
class InputSubmission(BaseModel):
    """Input request schema for submitting a job."""
    input_type: Literal["url", "topic"] = Field(..., description="Type of input: URL or topic name.")
    value: str = Field(..., description="Wikipedia page URL or topic name.")

# PUBLIC_INTERFACE
class StatusResponse(BaseModel):
    """Job status response schema."""
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: float

# PUBLIC_INTERFACE
class Entity(BaseModel):
    """Graph entity node."""
    id: str
    label: Optional[str] = None
    properties: Dict[str, Any] = {}

# PUBLIC_INTERFACE
class Relationship(BaseModel):
    """Graph relationship."""
    source: str
    target: str
    type: Optional[str] = None
    properties: Dict[str, Any] = {}

# PUBLIC_INTERFACE
class Embedding(BaseModel):
    """Embedding associated with an entity."""
    entity_id: str
    vector: List[float]

# PUBLIC_INTERFACE
class ResultResponse(BaseModel):
    """Job result payload containing extracted structures."""
    job_id: str
    entities: List[Entity]
    relationships: List[Relationship]
    embeddings: List[Embedding]

# PUBLIC_INTERFACE
class ErrorResponse(BaseModel):
    """Error response structure."""
    job_id: str
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
