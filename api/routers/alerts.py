from typing import Any

from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _not_implemented() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Redis alert endpoints are planned for the next implementation pass.",
    )


@router.get("/active")
def get_active_alerts():
    _not_implemented()


@router.post("/publish")
def publish_alert(alert: dict[str, Any]):
    _not_implemented()
