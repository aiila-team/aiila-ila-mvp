from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.schemas.graph import GraphResponse, GraphSearchResponse
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/search", response_model=GraphSearchResponse)
async def search_entities(q: str = Query(..., min_length=1, max_length=100)) -> GraphSearchResponse:
    try:
        result = graph_service.search_entities(q)
        return JSONResponse(content=result.model_dump(mode="json"))
    except Exception as exc:
        logger.exception("graph search failed")
        raise HTTPException(status_code=500, detail="Internal server error during entity search") from exc


@router.get("/entity/{entity_id}/neighbors", response_model=GraphResponse)
async def get_entity_neighbors(entity_id: str, hops: int = Query(1, ge=1, le=3)) -> GraphResponse:
    try:
        UUID(entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid entity ID format. Must be a valid UUID.") from exc

    try:
        result = graph_service.get_entity_neighbors(entity_id, hops)
        return JSONResponse(content=result.model_dump(mode="json"))
    except Exception as exc:
        logger.exception("graph traversal failed")
        raise HTTPException(status_code=500, detail="Internal server error during graph traversal") from exc
