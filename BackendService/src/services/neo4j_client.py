from typing import List, Dict, Any, Optional, Callable
from contextlib import contextmanager
import time

from src.core.config import Settings
from src.core.logging import get_logger

logger = get_logger(__name__)


def _missing(val: Optional[str]) -> bool:
    return val is None or str(val).strip() == ""


class Neo4jClient:
    """
    PUBLIC_INTERFACE
    A Neo4j client that initializes from environment variables and supports:
    - Parameterized Cypher MERGE upserts for nodes and relationships
    - Embedding persistence on nodes
    - Graceful no-op behavior if Neo4j is not configured
    - Basic retry logic for transient errors

    If NEO4J_URI, NEO4J_USER, or NEO4J_PASSWORD are missing, all operations are no-ops.
    """
    def __init__(self):
        self.settings = Settings()
        self._driver = None
        self._configured = not (_missing(self.settings.NEO4J_URI) or _missing(self.settings.NEO4J_USER) or _missing(self.settings.NEO4J_PASSWORD))
        if not self._configured:
            logger.warning("Neo4j not configured (NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD). Operating in no-op mode.")
            return

        try:
            from neo4j import GraphDatabase  # type: ignore
            self._driver = GraphDatabase.driver(
                self.settings.NEO4J_URI,  # type: ignore[arg-type]
                auth=(self.settings.NEO4J_USER, self.settings.NEO4J_PASSWORD),  # type: ignore[arg-type]
            )
            # Probe connectivity once to surface config errors early, but don't raise if fails.
            try:
                self._driver.verify_connectivity()  # type: ignore[union-attr]
                logger.info("Neo4j connectivity verified")
            except Exception as conn_err:
                logger.warning(f"Neo4j connectivity check failed: {conn_err}. Will retry on demand.")
        except Exception as e:
            logger.warning(
                "Neo4j driver initialization failed; operating in no-op mode. "
                f"uri={self.settings.NEO4J_URI!r} user={self.settings.NEO4J_USER!r} error={e}"
            )
            self._driver = None
            self._configured = False

    @contextmanager
    def _session(self):
        """
        Context manager returning an auto-closed session if configured; otherwise yields None for no-op.
        """
        if self._driver:
            with self._driver.session() as session:  # type: ignore[union-attr]
                yield session
        else:
            yield None

    def _with_retries(self, op_name: str, func: Callable[[], Any], retries: int = 3, base_delay: float = 0.5) -> None:
        """
        Execute the provided function with simple exponential backoff retries for transient errors.
        """
        attempt = 0
        while True:
            try:
                func()
                return
            except Exception as e:
                attempt += 1
                if attempt > retries:
                    logger.warning(f"Neo4j operation '{op_name}' failed after {retries} retries: {e}")
                    return
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(f"Neo4j operation '{op_name}' error: {e}; retrying in {delay:.2f}s (attempt {attempt}/{retries})")
                time.sleep(delay)

    # PUBLIC_INTERFACE
    def upsert_entities_and_relationships(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> None:
        """
        PUBLIC_INTERFACE
        Upsert entities as nodes and relationships between them using parameterized Cypher MERGEs.
        Entities should be dicts with keys: id (str), label (optional str), properties (dict).
        Relationships should be dicts with keys: source (str), target (str), type (optional str), properties (dict).
        If Neo4j is not configured, this is a no-op that logs intent.
        """
        if not self._driver:
            logger.info(f"[NOOP] Would upsert {len(entities)} entities and {len(relationships)} relationships")
            return

        # Upsert entities: default label 'Entity' if missing. Merge by id and set properties atomically.
        ent_cypher = """
        UNWIND $rows AS row
        WITH row, coalesce(row.label, 'Entity') AS lbl
        CALL {
          WITH row, lbl
          MERGE (n:`Entity` {id: row.id})
          SET n:`Entity`, n:`` + lbl
          SET n += coalesce(row.properties, {})
          RETURN 0 AS _
        }
        """
        # Note: Using label parameterization in Neo4j requires apoc or string building; as a safe baseline we tag with base label Entity
        # and store requested label in a property. For standard driver, dynamic labels are not parameterized. We'll store 'label' property.
        ent_cypher = """
        UNWIND $rows AS row
        MERGE (n:Entity {id: row.id})
        SET n += coalesce(row.properties, {})
        SET n.label = coalesce(row.label, 'Entity')
        """

        # Upsert relationships: default type 'RELATED_TO' if missing. Merge endpoints, then merge relationship type via CASE (static type).
        # Because relationship types cannot be parameterized directly in Cypher, we handle common default and store requested type as property.
        rel_cypher_default = """
        UNWIND $rows AS row
        MERGE (s:Entity {id: row.source})
        MERGE (t:Entity {id: row.target})
        MERGE (s)-[r:RELATED_TO]->(t)
        SET r += coalesce(row.properties, {})
        SET r.type = coalesce(row.type, 'RELATED_TO')
        """

        def _run():
            with self._session() as s:
                if s is None:
                    return
                if entities:
                    s.run(ent_cypher, rows=entities)
                if relationships:
                    s.run(rel_cypher_default, rows=relationships)

        self._with_retries("upsert_entities_and_relationships", _run)

    # PUBLIC_INTERFACE
    def persist_embeddings(self, entity_id: str, vector: List[float]) -> None:
        """
        PUBLIC_INTERFACE
        Persist an embedding vector on a node identified by entity_id as a property 'embedding'.
        If Neo4j is not configured, this is a no-op that logs intent.
        """
        if not self._driver:
            logger.info("[NOOP] Would persist embedding for entity_id=%s (dim=%d)", entity_id, len(vector))
            return

        cypher = """
        MATCH (n:Entity {id: $entity_id})
        SET n.embedding = $vector
        """
        def _run():
            with self._session() as s:
                if s is None:
                    return
                s.run(cypher, entity_id=entity_id, vector=vector)

        self._with_retries("persist_embeddings", _run)

    # Backwards-compat internal calls from pipeline:

    def upsert_entities(self, entities: List[Dict[str, Any]]) -> None:
        """
        Upsert only entities; retained for backward compatibility with existing pipeline calls.
        """
        self.upsert_entities_and_relationships(entities, [])

    def upsert_relationships(self, relationships: List[Dict[str, Any]]) -> None:
        """
        Upsert only relationships; retained for backward compatibility with existing pipeline calls.
        """
        self.upsert_entities_and_relationships([], relationships)

    def upsert_embeddings(self, embeddings: List[Dict[str, Any]]) -> None:
        """
        Upsert embeddings list; retained for backward compatibility with existing pipeline calls.
        """
        if not embeddings:
            return
        for emb in embeddings:
            eid = emb.get("entity_id")
            vec = emb.get("vector") or []
            if not eid:
                continue
            self.persist_embeddings(eid, vec)

    # PUBLIC_INTERFACE
    def ping(self) -> tuple[bool, Optional[str]]:
        """
        PUBLIC_INTERFACE
        Check Neo4j driver connectivity at runtime.

        Returns:
            (connected, error_message) where connected is True if connectivity check succeeds,
            otherwise False with an error message. When the client is not configured, returns (False, reason).
        """
        if not self._configured:
            return False, "Neo4j not configured (missing NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD)"
        if not self._driver:
            return False, "Neo4j driver not initialized"

        try:
            # verify_connectivity() is supported in neo4j v5+
            self._driver.verify_connectivity()  # type: ignore[union-attr]
            return True, None
        except Exception as e:
            logger.warning("Neo4j ping failed: %s", e)
            return False, str(e)
