import hashlib
from typing import List

from src.core.logging import get_logger
from src.core.config import Settings

logger = get_logger(__name__)

class EmbeddingProvider:
    """
    PUBLIC_INTERFACE
    Provides embeddings for text: deterministic stub by default; optional OpenAI if configured.
    """
    def __init__(self):
        self.settings = Settings()
        self.use_openai = bool(self.settings.OPENAI_API_KEY)

        # Lazy init OpenAI client if key present
        self._openai_client = None
        if self.use_openai:
            try:
                from openai import OpenAI  # type: ignore
                self._openai_client = OpenAI(api_key=self.settings.OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"OpenAI init failed, falling back to stub embeddings: {e}")
                self.use_openai = False

    def embed(self, text: str) -> List[float]:
        """Return a vector for the given text."""
        if self.use_openai and self._openai_client:
            try:
                resp = self._openai_client.embeddings.create(model="text-embedding-3-small", input=text)
                return list(resp.data[0].embedding)
            except Exception as e:
                logger.warning(f"OpenAI embedding error: {e}; using stub.")
        # Deterministic stub: hash to 128-dim vector of floats between -1 and 1
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # repeat to reach 128 floats
        bytes_needed = 128 * 4
        rep = (h * (bytes_needed // len(h) + 1))[:bytes_needed]
        # convert bytes to floats deterministically
        vec = []
        for i in range(0, len(rep), 4):
            chunk = rep[i : i + 4]
            val = int.from_bytes(chunk, "little", signed=False)
            norm = (val % 2000) / 1000.0 - 1.0
            vec.append(norm)
        return vec
