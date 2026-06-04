from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from neo4j import GraphDatabase

from app.core.config import settings
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse, GraphSearchResponse


@dataclass
class GraphService:
    def _driver(self):
        return GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))

    def search_entities(self, query: str) -> GraphSearchResponse:
        cypher = """
        MATCH (n)
          WHERE toLower(coalesce(n.name, n.identifier, n.primary_identifier, '')) CONTAINS toLower($search_term)
              OR toLower(coalesce(n.alias_value, '')) CONTAINS toLower($search_term)
        RETURN n.id AS id,
               labels(n)[0] AS label,
               coalesce(n.name, n.primary_identifier, n.identifier, n.alias_value) AS name,
               labels(n)[0] AS node_type,
               properties(n) AS metadata
        LIMIT 20
        """
        with self._driver() as driver, driver.session() as session:
            rows = session.run(cypher, search_term=query)
            items = [
                GraphNode(
                    id=str(row["id"]),
                    label=row["label"],
                    name=row["name"],
                    node_type=row["node_type"],
                    metadata=dict(row["metadata"] or {}),
                )
                for row in rows
            ]
        return GraphSearchResponse(count=len(items), query=query, items=items)

    def get_entity_neighbors(self, entity_id: str, hops: int = 1) -> GraphResponse:
        cypher = """
        MATCH (center {id: $entity_id})
        CALL {
            WITH center
            MATCH path = (center)-[r*1..__HOPS__]-(neighbor)
            RETURN path
            LIMIT 100
        }
        UNWIND nodes(path) AS node
        WITH center, collect(DISTINCT node) AS nodes, collect(DISTINCT relationships(path)) AS rel_sets
        RETURN center.id AS center_id, nodes, rel_sets
        """.replace("__HOPS__", str(int(hops)))
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        with self._driver() as driver, driver.session() as session:
            result = session.run(cypher, entity_id=entity_id)
            record = result.single()
            if record and record["nodes"]:
                for node in record["nodes"]:
                    props = dict(node)
                    label = next(iter(node.labels)) if getattr(node, "labels", None) else "Node"
                    nodes.append(
                        GraphNode(
                            id=str(props.get("id", props.get("entity_id", ""))),
                            label=label,
                            name=props.get("name") or props.get("primary_identifier") or props.get("identifier"),
                            node_type=label,
                            metadata=props,
                        )
                    )
                for rel_set in record["rel_sets"]:
                    for rel in rel_set:
                        edges.append(
                            GraphEdge(
                                id=f"{rel.start_node.id}-{rel.type}-{rel.end_node.id}",
                                source=str(rel.start_node["id"]),
                                target=str(rel.end_node["id"]),
                                relation=rel.type,
                                metadata=dict(rel),
                            )
                        )
            else:
                center_query = "MATCH (center {id: $entity_id}) RETURN center"
                center_res = session.run(center_query, entity_id=entity_id)
                center_record = center_res.single()
                if center_record:
                    node = center_record["center"]
                    props = dict(node)
                    label = next(iter(node.labels)) if getattr(node, "labels", None) else "Node"
                    nodes.append(
                        GraphNode(
                            id=str(props.get("id", props.get("entity_id", ""))),
                            label=label,
                            name=props.get("name") or props.get("primary_identifier") or props.get("identifier"),
                            node_type=label,
                            metadata=props,
                        )
                    )
        return GraphResponse(
            center_entity_id=UUID(entity_id),
            node_count=len(nodes),
            edge_count=len(edges),
            nodes=nodes,
            edges=edges,
        )


graph_service = GraphService()
