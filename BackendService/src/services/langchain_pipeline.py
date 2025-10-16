from typing import List, Dict, Any, Tuple
import re

from src.core.logging import get_logger
from .embedding_provider import EmbeddingProvider
from .neo4j_client import Neo4jClient

logger = get_logger(__name__)

class ExtractionPipeline:
    """
    PUBLIC_INTERFACE
    Deterministic extraction pipeline (LLM-optional) to get entities/relationships.
    """
    def __init__(self, embedder: EmbeddingProvider, graph: Neo4jClient):
        self.embedder = embedder
        self.graph = graph

    def extract(self, text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract entities and relationships using simple heuristics:
        - Entities: unique capitalized words (length >= 3)
        - Relationships: co-occurrence in same sentence
        """
        sentences = re.split(r"(?<=[\.\!\?])\s+", text)
        entities_map: Dict[str, Dict[str, Any]] = {}
        relationships: List[Dict[str, Any]] = []

        def add_entity(name: str):
            if name not in entities_map:
                entities_map[name] = {"id": name, "label": "Entity", "properties": {"name": name}}

        for sent in sentences[:50]:  # limit for speed
            caps = set(re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", sent))
            for c in caps:
                add_entity(c)
            caps_list = list(caps)
            for i in range(len(caps_list)):
                for j in range(i + 1, len(caps_list)):
                    relationships.append(
                        {"source": caps_list[i], "target": caps_list[j], "type": "MENTIONS", "properties": {}}
                    )
        entities = list(entities_map.values())
        logger.info(f"Extracted {len(entities)} entities and {len(relationships)} relationships")
        return entities, relationships

    def embed_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for entities."""
        vectors = []
        for e in entities:
            vec = self.embedder.embed(e["id"])
            vectors.append({"entity_id": e["id"], "vector": vec})
        return vectors

    def upsert_to_graph(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        embeddings: List[Dict[str, Any]],
    ) -> None:
        """Upsert entities, relationships, and embeddings into Neo4j."""
        # Prefer the combined upsert for atomic batches; retains backward-compat calls
        self.graph.upsert_entities_and_relationships(entities, relationships)
        # embeddings are often stored in a vector index or as properties
        self.graph.upsert_embeddings(embeddings)
