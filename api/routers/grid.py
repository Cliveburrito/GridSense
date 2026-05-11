from typing import Any

from fastapi import APIRouter, HTTPException, status
from neo4j import AsyncDriver

from db.neo4j import get_driver
from models.graph import AffectedNode, FaultImpactResponse, RestorePathResponse

router = APIRouter(prefix="/grid", tags=["grid"])

NODE_ID_EXPR = "coalesce(n.node_id, n.gsp_id, n.substation_id, n.asset_id, n.meter_id)"
ORIGIN_ID_EXPR = "coalesce(origin.node_id, origin.gsp_id, origin.substation_id, origin.asset_id, origin.meter_id)"
DOWNSTREAM_ID_EXPR = "coalesce(downstream.node_id, downstream.gsp_id, downstream.substation_id, downstream.asset_id, downstream.meter_id)"
VALID_LABELS = {"GridSupplyPoint", "Substation", "Transformer", "SmartMeter"}
VALID_RELATIONSHIPS = {"FEEDS", "SUPPLIES", "CONNECTS_TO", "TIE_LINE"}


async def _node_exists(driver: AsyncDriver, node_id: str) -> bool:
    cypher = f"""
        MATCH (n)
        WHERE {NODE_ID_EXPR} = $node_id
        RETURN count(n) > 0 AS exists
    """
    async with driver.session(database="neo4j") as session:
        result = await session.run(cypher, node_id=node_id)
        record = await result.single()
    return bool(record and record["exists"])


@router.get("/fault-impact/{node_id}", response_model=FaultImpactResponse)
async def get_fault_impact(node_id: str, max_depth: int = 6):
    """
    Return all nodes that would lose supply if node_id trips.
    Uses bounded variable-length Cypher traversal to avoid accidental
    full-graph scans on malformed input.
    """
    if max_depth > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_depth cannot exceed 10 to protect query performance.",
        )
    cypher = f"""
        MATCH (origin)
        WHERE {ORIGIN_ID_EXPR} = $node_id
        MATCH p=(origin)-[:FEEDS|SUPPLIES|CONNECTS_TO*1..{max_depth}]->(downstream)
        RETURN labels(downstream)[0] AS node_type,
               {DOWNSTREAM_ID_EXPR} AS node_id,
               coalesce(downstream.name, downstream.model, downstream.premise_id) AS name,
               min(length(p)) AS depth
        ORDER BY depth, node_id
    """
    driver = get_driver()
    async with driver.session(database="neo4j") as session:
        result = await session.run(cypher, node_id=node_id)
        records = await result.data()

    if not records and not await _node_exists(driver, node_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found in topology graph.",
        )

    affected = [AffectedNode(**record) for record in records]
    return FaultImpactResponse(
        origin_id=node_id,
        affected_nodes=affected,
        total_affected=len(affected),
    )


@router.get("/restore-paths/{node_id}", response_model=RestorePathResponse)
async def get_restore_paths(node_id: str):
    cypher = """
        MATCH (target)
        WHERE coalesce(target.node_id, target.gsp_id, target.substation_id, target.asset_id, target.meter_id) = $node_id
        MATCH p=(source)-[:FEEDS|SUPPLIES|CONNECTS_TO|TIE_LINE*1..6]->(target)
        WHERE source:GridSupplyPoint OR source:Substation
        RETURN length(p) AS depth,
               [node IN nodes(p) | {
                   node_id: coalesce(node.node_id, node.gsp_id, node.substation_id, node.asset_id, node.meter_id),
                   node_type: labels(node)[0],
                   name: coalesce(node.name, node.model, node.premise_id)
               }] AS nodes
        ORDER BY depth
        LIMIT 10
    """
    async with get_driver().session(database="neo4j") as session:
        result = await session.run(cypher, node_id=node_id)
        records = await result.data()

    if not records and not await _node_exists(get_driver(), node_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found in topology graph.",
        )
    return RestorePathResponse(
        node_id=node_id,
        paths=records,
        total_paths=len(records),
    )


@router.get("/nodes/{node_id}")
async def get_grid_node(node_id: str):
    cypher = f"""
        MATCH (n)
        WHERE {NODE_ID_EXPR} = $node_id
        RETURN {NODE_ID_EXPR} AS node_id,
               labels(n) AS labels,
               properties(n) AS properties
    """
    async with get_driver().session(database="neo4j") as session:
        result = await session.run(cypher, node_id=node_id)
        record = await result.single()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node '{node_id}' not found in topology graph.",
        )
    return record.data()


@router.post("/nodes")
async def create_grid_node(node: dict[str, Any]):
    label = node.get("label")
    properties = dict(node.get("properties", {}))
    if label not in VALID_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"label must be one of: {sorted(VALID_LABELS)}",
        )
    node_id = properties.get("node_id")
    if not isinstance(node_id, str) or not node_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="properties.node_id is required for API-created nodes.",
        )

    cypher = f"""
        MERGE (n:{label} {{node_id: $node_id}})
        SET n += $properties
        RETURN n.node_id AS node_id, labels(n) AS labels, properties(n) AS properties
    """
    async with get_driver().session(database="neo4j") as session:
        result = await session.run(
            cypher,
            node_id=node_id.strip(),
            properties=properties,
        )
        record = await result.single()
    return record.data()


@router.post("/relationships")
async def create_grid_relationship(relationship: dict[str, Any]):
    relationship_type = relationship.get("type")
    if relationship_type not in VALID_RELATIONSHIPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"type must be one of: {sorted(VALID_RELATIONSHIPS)}",
        )
    from_id = relationship.get("from_id")
    to_id = relationship.get("to_id")
    if not from_id or not to_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_id and to_id are required.",
        )
    properties = dict(relationship.get("properties", {}))
    cypher = f"""
        MATCH (a), (b)
        WHERE coalesce(a.node_id, a.gsp_id, a.substation_id, a.asset_id, a.meter_id) = $from_id
          AND coalesce(b.node_id, b.gsp_id, b.substation_id, b.asset_id, b.meter_id) = $to_id
        MERGE (a)-[r:{relationship_type}]->(b)
        SET r += $properties
        RETURN type(r) AS type, properties(r) AS properties
    """
    async with get_driver().session(database="neo4j") as session:
        result = await session.run(
            cypher,
            from_id=from_id,
            to_id=to_id,
            properties=properties,
        )
        record = await result.single()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both endpoint nodes were not found.",
        )
    return record.data()
