"""
schemas/graph.py
──────────────────────────────────────────────────────────────────────────────
Pydantic Schemas for Graph API Responses

These schemas define the structure of responses for the graph intelligence API.
They ensure type safety and proper serialization for graph visualization data.
──────────────────────────────────────────────────────────────────────────────
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID


class GraphNode(BaseModel):
    """Represents a node in the graph visualization."""
    id: str = Field(..., description="Unique identifier of the entity")
    label: str = Field(..., description="Display label for the node")
    entity_type: str = Field(..., description="Type of entity (person, phone, etc.)")
    risk_score: Optional[float] = Field(None, description="Risk score of the entity")


class GraphEdge(BaseModel):
    """Represents an edge/relationship in the graph."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship: str = Field(..., description="Type of relationship")


class GraphResponse(BaseModel):
    """Response for graph neighbor queries."""
    center_entity: GraphNode = Field(..., description="The central entity being queried")
    nodes: List[GraphNode] = Field(..., description="All nodes in the graph (including center)")
    edges: List[GraphEdge] = Field(..., description="All edges in the graph")
    hop_count: int = Field(..., description="Number of hops traversed")
    node_count: int = Field(..., description="Total number of nodes returned")
    edge_count: int = Field(..., description="Total number of edges returned")


class GraphSearchResult(BaseModel):
    """Individual search result for entity search."""
    id: str = Field(..., description="Entity ID")
    entity_type: str = Field(..., description="Type of entity")
    display_name: str = Field(..., description="Display name of the entity")
    risk_score: Optional[float] = Field(None, description="Risk score")


class GraphSearchResponse(BaseModel):
    """Response for entity search queries."""
    count: int = Field(..., description="Number of results found")
    results: List[GraphSearchResult] = Field(..., description="Search results (max 20)")