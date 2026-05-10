from pydantic import BaseModel


class AffectedNode(BaseModel):
    node_id: str
    node_type: str
    name: str | None = None
    depth: int


class FaultImpactResponse(BaseModel):
    origin_id: str
    affected_nodes: list[AffectedNode]
    total_affected: int


class RestorePathResponse(BaseModel):
    node_id: str
    paths: list[dict]
    total_paths: int
