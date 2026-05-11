"""
api/v1/graph.py
──────────────────────────────────────────────────────────────────────────────
Graph Intelligence API Router

This router provides REST endpoints for graph-based intelligence operations.
It enables exploration of entity relationships and graph search capabilities
using Neo4j as the underlying graph database.

Endpoints:
  - GET /search: Search entities by identifier/name/alias
  - GET /entity/{id}/neighbors: Get graph neighbors with configurable hop depth

Features:
  - Input validation using Pydantic
  - Comprehensive error handling
  - Structured logging
  - Response caching considerations
  - Rate limiting ready

Error Handling:
  - 400: Invalid input parameters
  - 404: Entity not found
  - 500: Internal server errors (Neo4j failures)
──────────────────────────────────────────────────────────────────────────────
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.schemas.graph import GraphResponse, GraphSearchResponse
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search", response_model=GraphSearchResponse)
async def search_entities(
    q: str = Query(..., description="Search query for entities", min_length=1, max_length=100)
) -> GraphSearchResponse:
    """
    Search for entities by identifier, display name, or aliases.

    This endpoint performs a case-insensitive search across:
    - Primary identifiers
    - Display names
    - Associated aliases

    Returns up to 20 matching entities ordered by relevance.
    """
    try:
        logger.info(f"Entity search request: query='{q}'")
        result = graph_service.search_entities(q)
        logger.info(f"Entity search completed: found {result.count} results")
        return result

    except Exception as e:
        logger.error(f"Error during entity search: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during entity search"
        )


@router.get("/entity/{entity_id}/neighbors", response_model=GraphResponse)
async def get_entity_neighbors(
    entity_id: str,
    hops: int = Query(1, description="Number of hops to traverse", ge=1, le=3)
) -> GraphResponse:
    """
    Get graph neighbors for a specific entity.

    Traverses the graph from the specified entity up to the given number of hops.
    For 3-hop queries, results are capped at 100 nodes to prevent performance issues.

    Parameters:
    - entity_id: UUID of the center entity
    - hops: Number of relationship hops (1-3)

    Returns graph data suitable for visualization including nodes and edges.
    """
    try:
        # Validate entity_id format
        try:
            UUID(entity_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid entity ID format. Must be a valid UUID."
            )

        logger.info(f"Neighbor request: entity_id={entity_id}, hops={hops}")

        # Check if entity exists
        entity = graph_service.get_entity_by_id(entity_id)
        if not entity:
            raise HTTPException(
                status_code=404,
                detail=f"Entity {entity_id} not found"
            )

        # Get neighbors
        result = graph_service.get_entity_neighbors(entity_id, hops)
        logger.info(f"Neighbor query completed: {result.node_count} nodes, {result.edge_count} edges")
        return result

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during neighbor query: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during graph traversal"
        )