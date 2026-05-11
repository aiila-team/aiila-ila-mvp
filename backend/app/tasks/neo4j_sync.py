"""
tasks/neo4j_sync.py
──────────────────────────────────────────────────────────────────────────────
Neo4j Graph Sync Task for ILA — Intelligence Layer for Analytics

Responsibility:
  After entity resolution writes a resolved Entity + its EntityAliases into
  PostgreSQL, this Celery task syncs that data into the Neo4j graph database.

  Neo4j is the "relationship layer" of ILA. PostgreSQL holds canonical entity
  records; Neo4j holds the graph of *how* they connect to each other, enabling
  multi-hop traversal queries that PostgreSQL cannot do efficiently.

Node Types (Labels):
  ┌─────────────────┬──────────────────────────────────────────────────────┐
  │ Neo4j Label     │ ILA EntityType                                       │
  ├─────────────────┼──────────────────────────────────────────────────────┤
  │ Person          │ EntityType.PERSON                                    │
  │ Phone           │ EntityType.PHONE                                     │
  │ SocialAccount   │ EntityType.SOCIAL_HANDLE, EntityType.TELEGRAM        │
  │ UPIAccount      │ EntityType.UPI_ACCOUNT                               │
  │ EmailAddress    │ EntityType.EMAIL                                     │
  │ IMEIDevice      │ EntityType.IMEI                                      │
  │ CryptoWallet    │ EntityType.CRYPTO_WALLET                             │
  └─────────────────┴──────────────────────────────────────────────────────┘

Relationships:
  ┌──────────────┬────────────────────────────────────────────────────────┐
  │ Relationship │ Meaning                                                │
  ├──────────────┼────────────────────────────────────────────────────────┤
  │ OWNS         │ Person owns a Phone / UPIAccount / CryptoWallet / IMEI │
  │ CONTROLS     │ Person controls a SocialAccount / EmailAddress         │
  │ POSTED       │ SocialAccount posted content (event link)              │
  │ KNOWS        │ Person ↔ Person (co-occurrence / communication edge)   │
  └──────────────┴────────────────────────────────────────────────────────┘

All writes use MERGE (CREATE IF NOT EXISTS + UPDATE IF EXISTS) so this task
is fully idempotent — it can safely re-run on the same entity after any
enrichment update.

Neo4j Driver:
  Uses the neo4j Python driver (neo4j>=5.0). The driver singleton lives in
  app/core/neo4j.py and is passed in / imported. Connection config comes from
  environment variables:
      NEO4J_URI      = bolt://neo4j:7687
      NEO4J_USER     = neo4j
      NEO4J_PASSWORD = <password>

Celery integration:
  Called as: sync_entity_to_graph_task.delay(entity_id)
  Triggered by: tasks/enrich.py after resolve_entity_task completes.
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from celery import Task
from celery.utils.log import get_task_logger
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, TransientError

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Entity, EntityAlias, EntityType

logger = get_task_logger(__name__)

# ── Neo4j Driver Singleton ────────────────────────────────────────────────────
# One driver per Celery worker process (connection pool is managed internally).
# The driver is lazily initialized on first task execution.

_driver: Optional[Driver] = None


def _get_driver() -> Driver:
    """
    Return the Neo4j driver singleton.
    Lazily initializes on first call. Safe within a single Celery worker process.
    """
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_pool_size=10,         # per-worker pool
            connection_acquisition_timeout=30.0, # seconds
        )
        logger.info(f"Neo4j driver initialized → {settings.NEO4J_URI}")
    return _driver


def close_driver() -> None:
    """Call at Celery worker shutdown (connect to worker_shutdown signal)."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed.")


# ── EntityType → Neo4j Label Mapping ─────────────────────────────────────────

_ENTITY_TYPE_TO_LABEL: dict[str, str] = {
    EntityType.PERSON:        "Person",
    EntityType.PHONE:         "Phone",
    EntityType.EMAIL:         "EmailAddress",
    EntityType.UPI_ACCOUNT:   "UPIAccount",
    EntityType.SOCIAL_HANDLE: "SocialAccount",
    EntityType.TELEGRAM:      "SocialAccount",
    EntityType.IMEI:          "IMEIDevice",
    EntityType.CRYPTO_WALLET: "CryptoWallet",
}

# Relationship type for each alias node type connecting back to a Person node
_PERSON_TO_ALIAS_RELATIONSHIP: dict[str, str] = {
    "Phone":         "OWNS",
    "UPIAccount":    "OWNS",
    "IMEIDevice":    "OWNS",
    "CryptoWallet":  "OWNS",
    "SocialAccount": "CONTROLS",
    "EmailAddress":  "CONTROLS",
}


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class GraphSyncResult:
    """
    Return value of the sync operation.
    Useful for logging and for the Celery task result backend.
    """
    entity_id: str
    entity_label: str
    nodes_merged: int = 0
    relationships_merged: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


# ── Cypher Query Library ──────────────────────────────────────────────────────
# All queries use MERGE (idempotent). Parameters use $param syntax.
# Each query merges a node on its primary key and then sets/updates properties.

class _Queries:
    """
    Namespace for all Cypher queries used in this module.
    Keeping them here makes it easy to review and test independently.
    """

    # ── Node MERGE queries ────────────────────────────────────────────────────

    MERGE_PERSON = """
        MERGE (n:Person {entity_id: $entity_id})
        ON CREATE SET
            n.primary_identifier = $primary_identifier,
            n.display_name       = $display_name,
            n.risk_score         = $risk_score,
            n.risk_level         = $risk_level,
            n.influence_score    = $influence_score,
            n.is_flagged         = $is_flagged,
            n.first_seen         = $first_seen,
            n.last_seen          = $last_seen,
            n.created_at         = timestamp()
        ON MATCH SET
            n.display_name    = $display_name,
            n.risk_score      = $risk_score,
            n.risk_level      = $risk_level,
            n.influence_score = $influence_score,
            n.is_flagged      = $is_flagged,
            n.last_seen       = $last_seen,
            n.updated_at      = timestamp()
        RETURN n
    """

    MERGE_PHONE = """
        MERGE (n:Phone {number: $value})
        ON CREATE SET
            n.entity_id  = $entity_id,
            n.confidence = $confidence,
            n.platform   = $platform,
            n.created_at = timestamp()
        ON MATCH SET
            n.confidence = $confidence,
            n.updated_at = timestamp()
        RETURN n
    """

    MERGE_UPI = """
        MERGE (n:UPIAccount {vpa: $value})
        ON CREATE SET
            n.entity_id  = $entity_id,
            n.confidence = $confidence,
            n.platform   = $platform,
            n.created_at = timestamp()
        ON MATCH SET
            n.confidence = $confidence,
            n.updated_at = timestamp()
        RETURN n
    """

    MERGE_EMAIL = """
        MERGE (n:EmailAddress {address: $value})
        ON CREATE SET
            n.entity_id  = $entity_id,
            n.confidence = $confidence,
            n.platform   = $platform,
            n.created_at = timestamp()
        ON MATCH SET
            n.confidence = $confidence,
            n.updated_at = timestamp()
        RETURN n
    """

    MERGE_SOCIAL = """
        MERGE (n:SocialAccount {handle: $value})
        ON CREATE SET
            n.entity_id  = $entity_id,
            n.platform   = $platform,
            n.confidence = $confidence,
            n.created_at = timestamp()
        ON MATCH SET
            n.platform   = $platform,
            n.confidence = $confidence,
            n.updated_at = timestamp()
        RETURN n
    """

    MERGE_IMEI = """
        MERGE (n:IMEIDevice {imei: $value})
        ON CREATE SET
            n.entity_id  = $entity_id,
            n.confidence = $confidence,
            n.created_at = timestamp()
        ON MATCH SET
            n.confidence = $confidence,
            n.updated_at = timestamp()
        RETURN n
    """

    MERGE_CRYPTO = """
        MERGE (n:CryptoWallet {address: $value})
        ON CREATE SET
            n.entity_id  = $entity_id,
            n.confidence = $confidence,
            n.created_at = timestamp()
        ON MATCH SET
            n.confidence = $confidence,
            n.updated_at = timestamp()
        RETURN n
    """

    # ── Relationship MERGE queries ────────────────────────────────────────────
    # Pattern: find the anchor Person by entity_id, find the target node by
    # its natural key, MERGE the relationship.

    # Person -[:OWNS]-> Phone
    REL_PERSON_OWNS_PHONE = """
        MATCH (p:Person {entity_id: $person_entity_id})
        MATCH (ph:Phone {number: $value})
        MERGE (p)-[r:OWNS]->(ph)
        ON CREATE SET r.since = timestamp(), r.confidence = $confidence
        ON MATCH  SET r.confidence = $confidence
        RETURN r
    """

    # Person -[:OWNS]-> UPIAccount
    REL_PERSON_OWNS_UPI = """
        MATCH (p:Person {entity_id: $person_entity_id})
        MATCH (u:UPIAccount {vpa: $value})
        MERGE (p)-[r:OWNS]->(u)
        ON CREATE SET r.since = timestamp(), r.confidence = $confidence
        ON MATCH  SET r.confidence = $confidence
        RETURN r
    """

    # Person -[:OWNS]-> IMEIDevice
    REL_PERSON_OWNS_IMEI = """
        MATCH (p:Person {entity_id: $person_entity_id})
        MATCH (d:IMEIDevice {imei: $value})
        MERGE (p)-[r:OWNS]->(d)
        ON CREATE SET r.since = timestamp(), r.confidence = $confidence
        ON MATCH  SET r.confidence = $confidence
        RETURN r
    """

    # Person -[:OWNS]-> CryptoWallet
    REL_PERSON_OWNS_CRYPTO = """
        MATCH (p:Person {entity_id: $person_entity_id})
        MATCH (w:CryptoWallet {address: $value})
        MERGE (p)-[r:OWNS]->(w)
        ON CREATE SET r.since = timestamp(), r.confidence = $confidence
        ON MATCH  SET r.confidence = $confidence
        RETURN r
    """

    # Person -[:CONTROLS]-> SocialAccount
    REL_PERSON_CONTROLS_SOCIAL = """
        MATCH (p:Person {entity_id: $person_entity_id})
        MATCH (s:SocialAccount {handle: $value})
        MERGE (p)-[r:CONTROLS]->(s)
        ON CREATE SET r.since = timestamp(), r.confidence = $confidence
        ON MATCH  SET r.confidence = $confidence
        RETURN r
    """

    # Person -[:CONTROLS]-> EmailAddress
    REL_PERSON_CONTROLS_EMAIL = """
        MATCH (p:Person {entity_id: $person_entity_id})
        MATCH (e:EmailAddress {address: $value})
        MERGE (p)-[r:CONTROLS]->(e)
        ON CREATE SET r.since = timestamp(), r.confidence = $confidence
        ON MATCH  SET r.confidence = $confidence
        RETURN r
    """

    # SocialAccount -[:POSTED]-> event node (lightweight event reference)
    # We do not store full events in Neo4j — just a thin reference node.
    REL_SOCIAL_POSTED_EVENT = """
        MATCH (s:SocialAccount {handle: $handle})
        MERGE (ev:Event {event_id: $event_id})
        ON CREATE SET
            ev.platform    = $platform,
            ev.published_at = $published_at,
            ev.created_at  = timestamp()
        MERGE (s)-[r:POSTED]->(ev)
        ON CREATE SET r.at = timestamp()
        RETURN r
    """

    # Person -[:KNOWS]-> Person  (co-occurrence / communication)
    REL_PERSON_KNOWS_PERSON = """
        MATCH (a:Person {entity_id: $entity_id_a})
        MATCH (b:Person {entity_id: $entity_id_b})
        MERGE (a)-[r:KNOWS]-(b)
        ON CREATE SET
            r.since      = timestamp(),
            r.strength   = $strength,
            r.event_id   = $event_id
        ON MATCH SET
            r.strength   = $strength
        RETURN r
    """

    # ── Utility ───────────────────────────────────────────────────────────────

    # Used by schema.cypher on Day 1 (reference only — executed by Sridhar)
    SCHEMA_CONSTRAINTS = """
        CREATE CONSTRAINT person_entity_id IF NOT EXISTS
            FOR (p:Person) REQUIRE p.entity_id IS UNIQUE;

        CREATE CONSTRAINT phone_number IF NOT EXISTS
            FOR (ph:Phone) REQUIRE ph.number IS UNIQUE;

        CREATE CONSTRAINT upi_vpa IF NOT EXISTS
            FOR (u:UPIAccount) REQUIRE u.vpa IS UNIQUE;

        CREATE CONSTRAINT email_address IF NOT EXISTS
            FOR (e:EmailAddress) REQUIRE e.address IS UNIQUE;

        CREATE CONSTRAINT social_handle IF NOT EXISTS
            FOR (s:SocialAccount) REQUIRE s.handle IS UNIQUE;

        CREATE CONSTRAINT imei_number IF NOT EXISTS
            FOR (d:IMEIDevice) REQUIRE d.imei IS UNIQUE;

        CREATE CONSTRAINT crypto_address IF NOT EXISTS
            FOR (w:CryptoWallet) REQUIRE w.address IS UNIQUE;

        CREATE CONSTRAINT event_id IF NOT EXISTS
            FOR (ev:Event) REQUIRE ev.event_id IS UNIQUE;
    """


# ── Core Sync Logic ───────────────────────────────────────────────────────────

class Neo4jSyncService:
    """
    Handles all graph write operations for entity syncing.

    Design:
      - All public methods accept a neo4j Session (passed in for testability).
      - Celery task creates the session and calls these methods.
      - All writes are MERGE-based (idempotent).
      - Errors are caught per-alias so one bad alias doesn't abort the whole sync.

    Node merge strategy:
      1. Merge the root entity node (Person / Phone / etc.)
      2. For each alias of the entity, merge the alias node
      3. If root entity is a Person, merge the relationship
         Person→alias (OWNS or CONTROLS)
      4. If root entity is a SocialAccount and we have event data,
         merge the POSTED relationship

    Relationship inference:
      The relationship type between a Person and each alias is inferred from
      the alias's Neo4j label using _PERSON_TO_ALIAS_RELATIONSHIP mapping.
    """

    def sync_entity(
        self,
        session: Session,
        entity: Entity,
        aliases: list[EntityAlias],
    ) -> GraphSyncResult:
        """
        Full sync for one Entity and its aliases.

        Args:
            session : Active Neo4j session (write transaction).
            entity  : SQLAlchemy Entity ORM object.
            aliases : List of EntityAlias ORM objects for this entity.

        Returns:
            GraphSyncResult with counts and any errors encountered.
        """
        result = GraphSyncResult(
            entity_id=str(entity.id),
            entity_label=_ENTITY_TYPE_TO_LABEL.get(entity.entity_type, "Unknown"),
        )

        # ── Step 1: Merge the root entity node ───────────────────────────────
        try:
            self._merge_node(session, entity, result)
        except Exception as exc:
            msg = f"Failed to merge root node for entity {entity.id}: {exc}"
            logger.error(msg)
            result.errors.append(msg)
            return result   # Can't proceed without root node

        # ── Step 2: Merge alias nodes + relationships ─────────────────────────
        for alias in aliases:
            try:
                self._merge_alias_node(session, alias, result)
                self._merge_alias_relationship(session, entity, alias, result)
            except Exception as exc:
                msg = (
                    f"Failed to sync alias {alias.alias_value} "
                    f"({alias.alias_type}) for entity {entity.id}: {exc}"
                )
                logger.warning(msg)
                result.errors.append(msg)
                # Continue with remaining aliases

        logger.info(
            f"Graph sync complete for entity {entity.id} ({result.entity_label}) | "
            f"nodes_merged={result.nodes_merged} | "
            f"rels_merged={result.relationships_merged} | "
            f"errors={len(result.errors)}"
        )
        return result

    def merge_knows_relationship(
        self,
        session: Session,
        entity_id_a: str,
        entity_id_b: str,
        strength: float = 1.0,
        event_id: Optional[str] = None,
    ) -> bool:
        """
        Merge a bidirectional KNOWS relationship between two Person nodes.
        Used by coordinated_detector.py (Day 4) when co-occurrence is detected.

        Args:
            session    : Active Neo4j session.
            entity_id_a: First person's entity_id (UUID string).
            entity_id_b: Second person's entity_id.
            strength   : Edge weight (1.0 = direct communication, 0.5 = co-mention).
            event_id   : Optional triggering event_id for traceability.

        Returns:
            True if successful, False if either Person node doesn't exist.
        """
        try:
            result = session.run(
                _Queries.REL_PERSON_KNOWS_PERSON,
                entity_id_a=entity_id_a,
                entity_id_b=entity_id_b,
                strength=strength,
                event_id=event_id or "",
            )
            summary = result.consume()
            return summary.counters.relationships_created >= 0
        except Exception as exc:
            logger.error(
                f"Failed to merge KNOWS relationship "
                f"({entity_id_a} ↔ {entity_id_b}): {exc}"
            )
            return False

    def merge_posted_relationship(
        self,
        session: Session,
        handle: str,
        event_id: str,
        platform: str,
        published_at: Optional[str] = None,
    ) -> bool:
        """
        Merge a SocialAccount -[:POSTED]-> Event relationship.
        Called from enrich_task when we know the author handle of an event.

        Args:
            session     : Active Neo4j session.
            handle      : Normalized social account handle (e.g. "@raju_op")
            event_id    : raw_events.id (UUID string)
            platform    : "telegram", "twitter", etc.
            published_at: ISO 8601 timestamp string

        Returns:
            True if successful.
        """
        try:
            result = session.run(
                _Queries.REL_SOCIAL_POSTED_EVENT,
                handle=handle.lower(),
                event_id=event_id,
                platform=platform,
                published_at=published_at or "",
            )
            result.consume()
            return True
        except Exception as exc:
            logger.warning(f"Failed to merge POSTED rel for {handle} → {event_id}: {exc}")
            return False

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _merge_node(
        self, session: Session, entity: Entity, result: GraphSyncResult
    ) -> None:
        """Merge the root entity node based on its EntityType."""
        entity_type = entity.entity_type
        label = _ENTITY_TYPE_TO_LABEL.get(entity_type)

        if label is None:
            raise ValueError(f"No Neo4j label mapping for EntityType '{entity_type}'")

        base_params = {
            "entity_id":          str(entity.id),
            "primary_identifier": entity.primary_identifier,
            "display_name":       entity.display_name or entity.primary_identifier,
            "risk_score":         float(entity.risk_score or 0.0),
            "risk_level":         str(entity.risk_level or "low"),
            "influence_score":    float(entity.influence_score or 0.0),
            "is_flagged":         bool(entity.is_flagged),
            "first_seen":         _dt_to_str(entity.first_seen),
            "last_seen":          _dt_to_str(entity.last_seen),
        }

        # Route to the correct MERGE query for this node type
        query_map: dict[str, str] = {
            "Person":       _Queries.MERGE_PERSON,
            "Phone":        _Queries.MERGE_PHONE,
            "UPIAccount":   _Queries.MERGE_UPI,
            "EmailAddress": _Queries.MERGE_EMAIL,
            "SocialAccount":_Queries.MERGE_SOCIAL,
            "IMEIDevice":   _Queries.MERGE_IMEI,
            "CryptoWallet": _Queries.MERGE_CRYPTO,
        }

        query = query_map.get(label)
        if query is None:
            raise ValueError(f"No MERGE query defined for label '{label}'")

        # Non-Person nodes also need `value` and `confidence` params
        if label != "Person":
            base_params["value"] = entity.primary_identifier
            base_params["confidence"] = 1.0
            base_params["platform"] = str(
                entity.metadata_.get("platform", "") if entity.metadata_ else ""
            )

        cypher_result = session.run(query, **base_params)
        cypher_result.consume()
        result.nodes_merged += 1

    def _merge_alias_node(
        self,
        session: Session,
        alias: EntityAlias,
        result: GraphSyncResult,
    ) -> None:
        """
        Merge a single alias as a Neo4j node.
        The node type is determined by alias.alias_type.
        """
        label = _ENTITY_TYPE_TO_LABEL.get(alias.alias_type)
        if label is None:
            logger.debug(
                f"Skipping alias merge: no Neo4j label for alias_type '{alias.alias_type}'"
            )
            return

        params = {
            "entity_id":  str(alias.entity_id),
            "value":      alias.alias_value,
            "confidence": float(alias.confidence or 1.0),
            "platform":   alias.platform or "",
        }

        query_map: dict[str, str] = {
            "Phone":        _Queries.MERGE_PHONE,
            "UPIAccount":   _Queries.MERGE_UPI,
            "EmailAddress": _Queries.MERGE_EMAIL,
            "SocialAccount":_Queries.MERGE_SOCIAL,
            "IMEIDevice":   _Queries.MERGE_IMEI,
            "CryptoWallet": _Queries.MERGE_CRYPTO,
        }

        query = query_map.get(label)
        if query is None:
            # Person aliases (rare — a Person aliasing another person name)
            # would use the full MERGE_PERSON query, which needs more data.
            # Skip for now; handled by entity resolution creating a separate entity.
            logger.debug(f"No alias MERGE query for label '{label}', skipping.")
            return

        cypher_result = session.run(query, **params)
        cypher_result.consume()
        result.nodes_merged += 1

    def _merge_alias_relationship(
        self,
        session: Session,
        entity: Entity,
        alias: EntityAlias,
        result: GraphSyncResult,
    ) -> None:
        """
        Merge the relationship between the root entity and one of its aliases.

        If root entity is a Person → OWNS or CONTROLS the alias node.
        If root entity is NOT a Person → no automatic relationship is created
          here; those are created explicitly by coordinated_detector / enrich_task.
        """
        if entity.entity_type != EntityType.PERSON:
            return

        alias_label = _ENTITY_TYPE_TO_LABEL.get(alias.alias_type)
        if alias_label is None:
            return

        rel_type = _PERSON_TO_ALIAS_RELATIONSHIP.get(alias_label)
        if rel_type is None:
            return

        rel_query_map: dict[tuple[str, str], str] = {
            ("Person", "OWNS",     "Phone"):        _Queries.REL_PERSON_OWNS_PHONE,
            ("Person", "OWNS",     "UPIAccount"):   _Queries.REL_PERSON_OWNS_UPI,
            ("Person", "OWNS",     "IMEIDevice"):   _Queries.REL_PERSON_OWNS_IMEI,
            ("Person", "OWNS",     "CryptoWallet"): _Queries.REL_PERSON_OWNS_CRYPTO,
            ("Person", "CONTROLS", "SocialAccount"):_Queries.REL_PERSON_CONTROLS_SOCIAL,
            ("Person", "CONTROLS", "EmailAddress"): _Queries.REL_PERSON_CONTROLS_EMAIL,
        }

        query = rel_query_map.get(("Person", rel_type, alias_label))
        if query is None:
            logger.debug(
                f"No relationship query for Person-[{rel_type}]->{alias_label}"
            )
            return

        cypher_result = session.run(
            query,
            person_entity_id=str(entity.id),
            value=alias.alias_value,
            confidence=float(alias.confidence or 1.0),
        )
        cypher_result.consume()
        result.relationships_merged += 1


# ── Celery Task ───────────────────────────────────────────────────────────────

_sync_service = Neo4jSyncService()


class _Neo4jSyncTask(Task):
    """
    Custom Celery Task base class that holds the Neo4j driver open
    between task executions (avoids reconnecting per-task).

    Celery's Task class supports `__init__` for this pattern.
    """
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            f"sync_entity_to_graph_task FAILED | "
            f"task_id={task_id} | entity_id={args[0] if args else '?'} | "
            f"error={exc}"
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            f"sync_entity_to_graph_task RETRY | "
            f"task_id={task_id} | entity_id={args[0] if args else '?'} | "
            f"reason={exc}"
        )


@celery_app.task(
    bind=True,
    base=_Neo4jSyncTask,
    name="tasks.neo4j_sync.sync_entity_to_graph_task",
    max_retries=3,
    default_retry_delay=15,        # seconds before first retry
    acks_late=True,                # task ack'd AFTER completion (safe retry on crash)
    reject_on_worker_lost=True,    # re-queue if worker dies mid-task
)
def sync_entity_to_graph_task(self, entity_id: str) -> dict:
    """
    Celery task: sync one resolved Entity (and its aliases) into Neo4j.

    Triggered by: tasks/enrich.py → resolve_entity_task chain
    Input:        entity_id — UUID string of the Entity in PostgreSQL
    Output:       GraphSyncResult as dict (stored in Celery result backend)

    Retry policy:
      - Retries on ServiceUnavailable (Neo4j restart / transient network issue)
      - Retries on TransientError (Neo4j deadlock / lock timeout)
      - Does NOT retry on ValueError (bad data — permanent failure)
      - max_retries=3, backoff: 15s → 30s → 60s (exponential via countdown)
    """
    logger.info(f"sync_entity_to_graph_task started | entity_id={entity_id}")

    # ── Step 1: Load entity + aliases from PostgreSQL ─────────────────────────
    db = SessionLocal()
    try:
        entity: Optional[Entity] = db.get(Entity, entity_id)
        if entity is None:
            logger.error(f"Entity {entity_id} not found in PostgreSQL. Aborting.")
            return {"success": False, "error": f"Entity {entity_id} not found"}

        # Eager-load aliases in this session before closing
        aliases: list[EntityAlias] = list(entity.aliases)
    finally:
        db.close()

    # ── Step 2: Sync to Neo4j ─────────────────────────────────────────────────
    driver = _get_driver()
    try:
        with driver.session(database="neo4j") as session:
            with session.begin_transaction() as tx:
                result = _sync_service.sync_entity(tx, entity, aliases)
                if result.success:
                    tx.commit()
                    logger.info(
                        f"Transaction committed for entity {entity_id} | "
                        f"nodes={result.nodes_merged} rels={result.relationships_merged}"
                    )
                else:
                    # Partial failures (individual aliases) — still commit
                    # what succeeded, log the failures
                    tx.commit()
                    logger.warning(
                        f"Partial sync for entity {entity_id} | "
                        f"errors={result.errors}"
                    )

    except (ServiceUnavailable, TransientError) as exc:
        # Transient Neo4j errors — retry with exponential backoff
        retry_in = 15 * (2 ** self.request.retries)   # 15s, 30s, 60s
        logger.warning(
            f"Neo4j transient error for entity {entity_id}: {exc}. "
            f"Retrying in {retry_in}s (attempt {self.request.retries + 1}/3)"
        )
        raise self.retry(exc=exc, countdown=retry_in)

    except Exception as exc:
        logger.error(
            f"Unexpected error syncing entity {entity_id} to Neo4j: {exc}",
            exc_info=True,
        )
        # Don't retry on unexpected errors — flag for manual inspection
        return {
            "success": False,
            "entity_id": entity_id,
            "error": str(exc),
        }

    return {
        "success":               result.success,
        "entity_id":             result.entity_id,
        "entity_label":          result.entity_label,
        "nodes_merged":          result.nodes_merged,
        "relationships_merged":  result.relationships_merged,
        "errors":                result.errors,
    }


# ── Convenience: Bulk Sync (for scripts/load_neo4j.py) ───────────────────────

def bulk_sync_all_entities(batch_size: int = 50) -> dict:
    """
    Sync ALL entities from PostgreSQL into Neo4j.
    Used by scripts/load_neo4j.py on Day 1 to load mock data.

    Dispatches individual Celery tasks per entity so the worker pool
    processes them in parallel.

    Args:
        batch_size: Number of entity_ids to fetch per DB query (pagination).

    Returns:
        dict with total dispatched count.

    Usage (scripts/load_neo4j.py):
        from tasks.neo4j_sync import bulk_sync_all_entities
        result = bulk_sync_all_entities()
        print(f"Dispatched {result['dispatched']} sync tasks")
    """
    db = SessionLocal()
    dispatched = 0
    try:
        offset = 0
        while True:
            entity_ids = (
                db.query(Entity.id)
                .offset(offset)
                .limit(batch_size)
                .all()
            )
            if not entity_ids:
                break
            for (eid,) in entity_ids:
                sync_entity_to_graph_task.delay(str(eid))
                dispatched += 1
            offset += batch_size

        logger.info(f"Dispatched {dispatched} sync_entity_to_graph_task tasks.")
        return {"dispatched": dispatched}
    finally:
        db.close()


# ── Utilities ─────────────────────────────────────────────────────────────────

def _dt_to_str(dt) -> str:
    """Convert a datetime to ISO 8601 string, or empty string if None."""
    if dt is None:
        return ""
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)
