"""
services/graph_service.py
──────────────────────────────────────────────────────────────────────────────
Graph Intelligence Service Layer

This service handles all Neo4j graph operations for the ILA backend.
It provides methods for entity search, neighbor traversal, and graph data
normalization for API responses.

Key Features:
  - Parameterized Cypher queries for security
  - Efficient graph traversal with configurable hop limits
  - Deduplication of nodes and edges
  - Structured logging for performance monitoring
  - Error handling for Neo4j operations

Cypher Query Patterns:
  - Entity search: Uses CONTAINS for fuzzy matching
  - Neighbor traversal: Variable depth MATCH with DISTINCT
  - Node deduplication: Uses sets for uniqueness
  - Edge deduplication: Uses tuples for uniqueness

Performance Considerations:
  - Limits result sets to prevent memory issues
  - Uses appropriate indexes in Neo4j
  - Batches operations where possible
──────────────────────────────────────────────────────────────────────────────
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from neo4j import Driver
from neo4j.exceptions import Neo4jError

from app.core.neo4j import get_neo4j_driver
from app.schemas.graph import GraphNode, GraphEdge, GraphResponse, GraphSearchResult, GraphSearchResponse

logger = logging.getLogger(__name__)


class GraphService:
    """Service class for Neo4j graph operations."""

    def __init__(self):
        self._driver: Optional[Driver] = None

    @property
    def driver(self) -> Driver:
        """Lazy-loaded Neo4j driver."""
        if self._driver is None:
            self._driver = get_neo4j_driver()
        return self._driver

    def search_entities(self, query: str, limit: int = 20) -> GraphSearchResponse:
        """
        Search for entities by identifier, display name, or aliases.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            GraphSearchResponse with matching entities
        """
        logger.info(f"Searching entities with query: '{query}', limit: {limit}")

        cypher_query = """
        MATCH (e:Entity)
        WHERE
          toLower(e.primary_identifier) CONTAINS toLower($query) OR
          toLower(e.display_name) CONTAINS toLower($query) OR
          EXISTS {
            MATCH (e)-[:HAS_ALIAS]->(a:Alias)
            WHERE toLower(a.value) CONTAINS toLower($query)
          }
        RETURN DISTINCT e.id as id, e.entity_type as entity_type,
                        e.display_name as display_name, e.risk_score as risk_score
        LIMIT $limit
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, query=query, limit=limit)
                records = list(result)

                results = []
                for record in records:
                    results.append(GraphSearchResult(
                        id=record["id"],
                        entity_type=record["entity_type"],
                        display_name=record["display_name"],
                        risk_score=record.get("risk_score")
                    ))

                logger.info(f"Found {len(results)} entities matching query '{query}'")
                return GraphSearchResponse(count=len(results), results=results)

        except Neo4jError as e:
            logger.error(f"Neo4j error during entity search: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during entity search: {e}")
            raise

    def get_entity_neighbors(self, entity_id: str, hops: int) -> GraphResponse:
        """
        Get graph neighbors for an entity up to specified hop distance.

        Args:
            entity_id: UUID of the center entity
            hops: Number of hops to traverse (1-3)

        Returns:
            GraphResponse with nodes and edges

        Raises:
            ValueError: If hops is not between 1 and 3
        """
        if hops < 1 or hops > 3:
            raise ValueError("Hops must be between 1 and 3")

        logger.info(f"Getting {hops}-hop neighbors for entity {entity_id}")

        # For 3-hop queries, limit total nodes to prevent performance issues
        node_limit = 100 if hops == 3 else None

        cypher_query = f"""
        MATCH path = (center:Entity {{id: $entity_id}})-[*1..{hops}]-(neighbor:Entity)
        WHERE center <> neighbor
        WITH center, neighbor, min(length(path)) as distance
        RETURN
          center.id as center_id, center.display_name as center_label,
          center.entity_type as center_type, center.risk_score as center_risk,
          collect(DISTINCT {{
            id: neighbor.id,
            label: neighbor.display_name,
            entity_type: neighbor.entity_type,
            risk_score: neighbor.risk_score,
            distance: distance
          }}) as neighbors
        LIMIT {node_limit or 1000}
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, entity_id=entity_id)
                record = result.single()

                if not record:
                    logger.warning(f"No entity found with ID {entity_id}")
                    raise ValueError(f"Entity {entity_id} not found")

                # Build center entity
                center_entity = GraphNode(
                    id=record["center_id"],
                    label=record["center_label"],
                    entity_type=record["center_type"],
                    risk_score=record.get("center_risk")
                )

                # Process neighbors
                nodes: List[GraphNode] = [center_entity]
                edges: List[GraphEdge] = []
                node_ids: Set[str] = {center_entity.id}

                for neighbor_data in record["neighbors"]:
                    neighbor_id = neighbor_data["id"]

                    # Add node if not already present
                    if neighbor_id not in node_ids:
                        node = GraphNode(
                            id=neighbor_id,
                            label=neighbor_data["label"],
                            entity_type=neighbor_data["entity_type"],
                            risk_score=neighbor_data.get("risk_score")
                        )
                        nodes.append(node)
                        node_ids.add(neighbor_id)

                    # Add edge
                    edge = GraphEdge(
                        source=center_entity.id,
                        target=neighbor_id,
                        relationship="CONNECTED_TO"  # Generic relationship for now
                    )
                    edges.append(edge)

                # Remove duplicates (though Cypher should handle this)
                unique_edges = []
                edge_set: Set[Tuple[str, str, str]] = set()
                for edge in edges:
                    edge_tuple = (edge.source, edge.target, edge.relationship)
                    if edge_tuple not in edge_set:
                        unique_edges.append(edge)
                        edge_set.add(edge_tuple)

                response = GraphResponse(
                    center_entity=center_entity,
                    nodes=nodes,
                    edges=unique_edges,
                    hop_count=hops,
                    node_count=len(nodes),
                    edge_count=len(unique_edges)
                )

                logger.info(f"Found {len(nodes)} nodes and {len(unique_edges)} edges for {hops}-hop query on {entity_id}")
                return response

        except Neo4jError as e:
            logger.error(f"Neo4j error during neighbor traversal: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during neighbor traversal: {e}")
            raise

    def get_entity_by_id(self, entity_id: str) -> Optional[GraphNode]:
        """
        Get a single entity by ID for validation purposes.

        Args:
            entity_id: Entity UUID

        Returns:
            GraphNode if found, None otherwise
        """
        cypher_query = """
        MATCH (e:Entity {id: $entity_id})
        RETURN e.id as id, e.display_name as label,
               e.entity_type as entity_type, e.risk_score as risk_score
        """

        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, entity_id=entity_id)
                record = result.single()

                if record:
                    return GraphNode(
                        id=record["id"],
                        label=record["label"],
                        entity_type=record["entity_type"],
                        risk_score=record.get("risk_score")
                    )
                return None

        except Neo4jError as e:
            logger.error(f"Neo4j error getting entity {entity_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting entity {entity_id}: {e}")
            return None


# Global service instance
graph_service = GraphService()