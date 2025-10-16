from functools import lru_cache
from typing import Optional
from pydantic import BaseModel

from src.core.config import Settings

# PUBLIC_INTERFACE
@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()  # loads from env

class AuthedUser(BaseModel):
    """Represents an authenticated user context."""
    sub: str
    email: Optional[str] = None
