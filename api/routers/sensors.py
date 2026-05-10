from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter(prefix="/sensors", tags=["sensors"])


def _not_implemented() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Cassandra sensor endpoints are planned for the next implementation pass.",
    )


@router.post("/readings")
def create_sensor_reading(reading: dict[str, Any]):
    _not_implemented()


@router.get("/dashboard/recent")
def get_recent_dashboard_readings(limit: int = Query(default=50, ge=1, le=200)):
    _not_implemented()


@router.get("/{sensor_id}/readings")
def get_sensor_readings(
    sensor_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    _not_implemented()


@router.get("/{sensor_id}/summary")
def get_sensor_summary(sensor_id: str):
    _not_implemented()
