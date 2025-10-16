from typing import Literal
import wikipedia

from src.core.logging import get_logger

logger = get_logger(__name__)

class WikiService:
    """
    PUBLIC_INTERFACE
    Service to fetch and preprocess Wikipedia content.
    """
    def fetch(self, input_type: Literal["url", "topic"], value: str) -> str:
        """Fetch article content by URL or topic name."""
        # wikipedia lib doesn't fetch by URL; if url provided, attempt to extract title
        if input_type == "url":
            # naive extraction: last segment as title
            title = value.rstrip("/").split("/")[-1].replace("_", " ")
        else:
            title = value
        try:
            page = wikipedia.page(title, auto_suggest=False, preload=False)
            content = page.content
        except Exception:
            logger.warning("Primary fetch failed, retry with auto_suggest")
            page = wikipedia.page(title, auto_suggest=True, preload=False)
            content = page.content
        # simple preprocess: strip excessive whitespace
        return "\n".join([line.strip() for line in content.splitlines() if line.strip()])
