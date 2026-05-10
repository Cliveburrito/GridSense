from typing import Any

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/grid", tags=["grid"])


def _not_implemented() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Neo4j grid topology endpoints are planned for the next implementation pass.",
    )


@router.get("/fault-impact/{node_id}")
def get_fault_impact(node_id: str, max_depth: int = 6):
    if max_depth > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_depth cannot exceed 10 to protect query performance.",
        )
    _not_implemented()


@router.get("/restore-paths/{node_id}")
def get_restore_paths(node_id: str):
    _not_implemented()


@router.get("/nodes/{node_id}")
def get_grid_node(node_id: str):
    _not_implemented()


@router.post("/nodes")
def create_grid_node(node: dict[str, Any]):
    _not_implemented()


@router.post("/relationships")
def create_grid_relationship(relationship: dict[str, Any]):
    _not_implemented()
