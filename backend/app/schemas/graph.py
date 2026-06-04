from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    name: str | None = None
    node_type: str | None = None
    metadata: dict[str, Any] | None = None


class GraphEdge(BaseModel):
    id: str | None = None
    source: str
    target: str
    relation: str
    weight: float | None = None
    metadata: dict[str, Any] | None = None


class GraphResponse(BaseModel):
    center_entity_id: UUID
    node_count: int
    edge_count: int
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class GraphSearchResponse(BaseModel):
    count: int
    query: str
    items: list[GraphNode] = Field(default_factory=list)
