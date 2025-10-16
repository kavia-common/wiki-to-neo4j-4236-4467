from typing import List, Dict, Any
from contextlib import contextmanager

from src.core.config import Settings
from src.core.logging import get_logger

logger = get_logger(__name__)

class Neo4jClient:
    """
    PUBLIC_INTERFACE
    Minimal Neo4j client supporting upsert operations. If NEO4J_* not set, acts as no-op.
    """
    def __init__(self):
        self.settings = Settings()
        self._driver = None
        if self.settings.NEO4J_URI and self.settings.NEO4J_USER and self.settings.NEO4J_PASSWORD:
            try:
                from neo4j import GraphDatabase  # type: ignore
                self._driver = GraphDatabase.driver(
                    self.settings.NEO4J_URI,
                    auth=(self.settings.NEO4J_USER, self.settings.NEO4J_PASSWORD),
                )
                logger.info("Connected to Neo4j")
            except Exception as e:
                logger.warning(f"Neo4j connection failed: {e}; operating in no-op mode")

    @contextmanager
    def _session(self):
        if self._driver:
            with self._driver.session() as session:
                yield session
        else:
            yield None

    def upsert_entities(self, entities: List[Dict[str, Any]]) -> None:
        if not self._driver:
            logger.info(f"[NOOP] Would upsert {len(entities)} entities")
            return
        cypher = """
        UNWIND $rows AS row
        MERGE (n:Entity {id: row.id})
        SET n += row.properties
        """
        with self._session() as s:
            s.run(cypher, rows=entities)

    def upsert_relationships(self, relationships: List[Dict[str, Any]]) -> None:
        if not self._driver:
            logger.info(f"[NOOP] Would upsert {len(relationships)} relationships")
            return
        cypher = """
        UNWIND $rows AS row
        MERGE (s:Entity {id: row.source})
        MERGE (t:Entity {id: row.target})
        MERGE (s)-[r:MENTIONS]->(t)
        SET r += row.properties
        """
        with self._session() as s:
            s.run(cypher, rows=relationships)

    def upsert_embeddings(self, embeddings: List[Dict[str, Any]]) -> None:
        if not self._driver:
            logger.info(f"[NOOP] Would upsert {len(embeddings)} embeddings")
            return
        cypher = """
        UNWIND $rows AS row
        MATCH (n:Entity {id: row.entity_id})
        SET n.embedding = row.vector
        """
        with self._session() as s:
            s.run(cypher, rows=embeddings)
