"""
services/influence_scorer.py
──────────────────────────────────────────────────────────────────────────────
Influence Scoring via Neo4j Graph Data Science (GDS) PageRank — ILA Day 4

What it does:
  Runs PageRank on the Neo4j entity graph and writes influence_score back
  onto every Person node and into the PostgreSQL entities table.

Why PageRank for influence:
  An entity that is connected to many other entities (owns many phones,
  controls many accounts, is KNOWN by many people) has high "centrality"
  in the threat network. PageRank captures this without requiring us to
  manually define what "important" means.

Prerequisites (Sridhar sets up on Day 1):
  - Neo4j GDS plugin installed (neo4j-graph-data-science-*.jar)
  - A named graph projection "entityGraph" created in Neo4j:
      CALL gds.graph.project(
          'entityGraph',
          ['Person','Phone','SocialAccount','UPIAccount','EmailAddress'],
          {OWNS:{}, CONTROLS:{}, KNOWS:{}, POSTED:{}}
      )
  - This projection is refreshed by refresh_graph_projection() before scoring.

Output:
  - Neo4j: Person.influence_score property updated on each node
  - PostgreSQL: entities.influence_score column updated

Called by:
  tasks/ml_tasks.py → run_pagerank_task (Celery beat, every 30 min)
──────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from loguru import logger

# ── Configuration ──────────────────────────────────────────────────────────────

GRAPH_NAME: str = "entityGraph"
PAGERANK_ITERATIONS: int = 20
PAGERANK_DAMPING: float = 0.85        # standard PageRank damping factor
SCORE_NORMALIZATION_CAP: float = 10.0 # PageRank raw scores vary; cap normalisation


# ── Data contract ──────────────────────────────────────────────────────────────

@dataclass
class PageRankResult:
    nodes_scored: int
    db_rows_updated: int
    max_score: float
    min_score: float
    duration_seconds: float


# ── Cypher queries ─────────────────────────────────────────────────────────────

_Q_DROP_PROJECTION = "CALL gds.graph.drop($graph_name, false)"

_Q_CREATE_PROJECTION = """
CALL gds.graph.project(
    $graph_name,
    ['Person', 'Phone', 'SocialAccount', 'UPIAccount', 'EmailAddress',
     'IMEIDevice', 'CryptoWallet'],
    {
        OWNS:     {orientation: 'UNDIRECTED'},
        CONTROLS: {orientation: 'UNDIRECTED'},
        KNOWS:    {orientation: 'UNDIRECTED'},
        POSTED:   {orientation: 'UNDIRECTED'}
    }
)
YIELD graphName, nodeCount, relationshipCount
RETURN graphName, nodeCount, relationshipCount
"""

_Q_RUN_PAGERANK = """
CALL gds.pageRank.stream($graph_name, {
    maxIterations:    $iterations,
    dampingFactor:    $damping,
    relationshipWeightProperty: null
})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS node, score
WHERE node.entity_id IS NOT NULL
RETURN node.entity_id AS entity_id, score
ORDER BY score DESC
"""

_Q_UPDATE_NODE_SCORE = """
MATCH (n {entity_id: $entity_id})
SET n.influence_score = $score,
    n.influence_updated_at = timestamp()
"""


# ── Core service ───────────────────────────────────────────────────────────────

class InfluenceScorer:
    """
    Runs Neo4j GDS PageRank and syncs results back to PostgreSQL.

    Usage (Celery task):
        from services.influence_scorer import InfluenceScorer
        scorer = InfluenceScorer()
        result = scorer.run(neo4j_driver, db_session)
    """

    def run(self, driver, db) -> PageRankResult:
        """
        Full pipeline:
          1. Refresh the named graph projection in Neo4j
          2. Run PageRank stream
          3. Normalise scores to [0, 1]
          4. Write back to Neo4j node properties
          5. Write back to PostgreSQL entities.influence_score

        Args:
            driver : neo4j.Driver instance (from neo4j_sync._get_driver())
            db     : SQLAlchemy Session
        """
        import time
        from app.models import Entity

        t0 = time.time()
        scores: dict[str, float] = {}   # entity_id → normalised score

        # ── Step 1 + 2: Project graph and run PageRank ────────────────────────
        with driver.session(database="neo4j") as session:
            try:
                self._refresh_projection(session)
            except Exception as exc:
                logger.warning(f"[PageRank] Projection refresh failed: {exc}. Using existing.")

            try:
                result = session.run(
                    _Q_RUN_PAGERANK,
                    graph_name=GRAPH_NAME,
                    iterations=PAGERANK_ITERATIONS,
                    damping=PAGERANK_DAMPING,
                )
                raw: list[tuple[str, float]] = [
                    (record["entity_id"], float(record["score"]))
                    for record in result
                ]
            except Exception as exc:
                logger.error(f"[PageRank] gds.pageRank.stream failed: {exc}")
                return PageRankResult(
                    nodes_scored=0, db_rows_updated=0,
                    max_score=0.0, min_score=0.0,
                    duration_seconds=round(time.time() - t0, 3),
                )

        if not raw:
            logger.warning("[PageRank] No scores returned from GDS.")
            return PageRankResult(
                nodes_scored=0, db_rows_updated=0,
                max_score=0.0, min_score=0.0,
                duration_seconds=round(time.time() - t0, 3),
            )

        # ── Step 3: Normalise to [0.0, 1.0] ──────────────────────────────────
        raw_values = [v for _, v in raw]
        max_raw = max(raw_values) or 1.0
        for entity_id, raw_score in raw:
            scores[entity_id] = round(
                min(1.0, raw_score / max_raw), 4
            )

        # ── Step 4: Write back to Neo4j nodes ────────────────────────────────
        with driver.session(database="neo4j") as session:
            with session.begin_transaction() as tx:
                for entity_id, norm_score in scores.items():
                    tx.run(
                        _Q_UPDATE_NODE_SCORE,
                        entity_id=entity_id,
                        score=norm_score,
                    )
                tx.commit()

        # ── Step 5: Write back to PostgreSQL ─────────────────────────────────
        updated = 0
        batch_size = 200
        entity_ids = list(scores.keys())

        for i in range(0, len(entity_ids), batch_size):
            batch = entity_ids[i : i + batch_size]
            rows = (
                db.query(Entity)
                .filter(Entity.id.in_(batch))
                .all()
            )
            for entity in rows:
                entity.influence_score = scores.get(str(entity.id), 0.0)
                updated += 1

        db.commit()

        duration = round(time.time() - t0, 3)
        logger.info(
            f"[PageRank] Done | nodes_scored={len(scores)} | "
            f"db_updated={updated} | max={max(scores.values()):.4f} | "
            f"duration={duration}s"
        )

        return PageRankResult(
            nodes_scored=len(scores),
            db_rows_updated=updated,
            max_score=max(scores.values()) if scores else 0.0,
            min_score=min(scores.values()) if scores else 0.0,
            duration_seconds=duration,
        )

    def _refresh_projection(self, session) -> None:
        """
        Drop and recreate the named graph projection.
        Safe to call even if the projection doesn't exist yet.
        """
        # Drop existing (ignore if not found)
        try:
            session.run(_Q_DROP_PROJECTION, graph_name=GRAPH_NAME)
            logger.debug(f"[PageRank] Dropped existing projection '{GRAPH_NAME}'")
        except Exception:
            pass  # projection didn't exist — fine

        result = session.run(_Q_CREATE_PROJECTION, graph_name=GRAPH_NAME)
        record = result.single()
        if record:
            logger.info(
                f"[PageRank] Projection '{GRAPH_NAME}' created | "
                f"nodes={record['nodeCount']} | "
                f"rels={record['relationshipCount']}"
            )
