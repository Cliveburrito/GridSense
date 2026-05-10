import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status

from db.cassandra import execute_async, prepare_statement
from db.redis import get_redis_client
from models.cassandra import SensorReading, SensorReadingBatch, SensorSummary

router = APIRouter(prefix="/sensors", tags=["sensors"])


def _bucket_minute(reading_time: datetime) -> str:
    return reading_time.astimezone(timezone.utc).strftime("%Y%m%d%H%M")


def _normalize_payload(
    payload: SensorReading | SensorReadingBatch | list[SensorReading],
) -> list[SensorReading]:
    if isinstance(payload, SensorReading):
        return [payload]
    if isinstance(payload, SensorReadingBatch):
        return payload.readings
    return payload


def _row_to_reading(row: dict) -> SensorReading:
    return SensorReading(
        sensor_id=row["sensor_id"],
        reading_time=row["reading_time"],
        metric_type=row["metric_type"],
        value=float(row["value"]),
        unit=row["unit"],
        quality_flag=int(row["quality_flag"]),
        district_id=row.get("district_id", "network"),
    )


@router.post("/readings", status_code=status.HTTP_201_CREATED)
async def create_sensor_reading(
    payload: SensorReading | SensorReadingBatch | list[SensorReading],
):
    readings = _normalize_payload(payload)
    if not readings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one reading is required.",
        )

    insert_by_sensor = prepare_statement(
        """
        INSERT INTO sensor_readings (
            sensor_id, reading_time, metric_type, value, unit, quality_flag
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """
    )
    insert_by_bucket = prepare_statement(
        """
        INSERT INTO sensor_readings_by_bucket (
            bucket_minute, district_id, metric_type, reading_time,
            sensor_id, value, unit, quality_flag
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    )

    for reading in readings:
        await execute_async(
            insert_by_sensor,
            (
                reading.sensor_id,
                reading.reading_time,
                reading.metric_type,
                reading.value,
                reading.unit,
                reading.quality_flag,
            ),
        )
        await execute_async(
            insert_by_bucket,
            (
                _bucket_minute(reading.reading_time),
                reading.district_id,
                reading.metric_type,
                reading.reading_time,
                reading.sensor_id,
                reading.value,
                reading.unit,
                reading.quality_flag,
            ),
        )

    return {"inserted": len(readings)}


@router.get("/dashboard/recent")
async def get_recent_dashboard_readings(
    district_id: str = "network",
    metric_type: str = "voltage",
    bucket_minute: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    bucket = bucket_minute or datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    rows = await execute_async(
        """
        SELECT bucket_minute, district_id, metric_type, reading_time,
               sensor_id, value, unit, quality_flag
        FROM sensor_readings_by_bucket
        WHERE bucket_minute = ? AND district_id = ? AND metric_type = ?
        LIMIT ?
        """,
        (bucket, district_id, metric_type, limit),
    )
    return {
        "bucket_minute": bucket,
        "district_id": district_id,
        "metric_type": metric_type,
        "readings": list(rows),
    }


@router.get("/{sensor_id}/readings", response_model=list[SensorReading])
async def get_sensor_readings(
    sensor_id: str,
    from_time: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    if from_time is None:
        rows = await execute_async(
            """
            SELECT sensor_id, reading_time, metric_type, value, unit, quality_flag
            FROM sensor_readings
            WHERE sensor_id = ?
            LIMIT ?
            """,
            (sensor_id, limit),
        )
    else:
        rows = await execute_async(
            """
            SELECT sensor_id, reading_time, metric_type, value, unit, quality_flag
            FROM sensor_readings
            WHERE sensor_id = ? AND reading_time >= ?
            LIMIT ?
            """,
            (sensor_id, from_time, limit),
        )
    return [_row_to_reading(row) for row in rows]


@router.get("/{sensor_id}/summary", response_model=SensorSummary)
async def get_sensor_summary(sensor_id: str):
    cache_key = f"sensor-summary:{sensor_id}"
    cached = await get_redis_client().get(cache_key)
    if cached:
        data = json.loads(cached)
        data["source"] = "cache"
        return data

    from_time = datetime.now(timezone.utc) - timedelta(hours=1)
    rows = list(
        await execute_async(
            """
            SELECT sensor_id, reading_time, metric_type, value, unit, quality_flag
            FROM sensor_readings
            WHERE sensor_id = ? AND reading_time >= ?
            LIMIT 3600
            """,
            (sensor_id, from_time),
        )
    )
    readings = [_row_to_reading(row) for row in rows]
    values = [reading.value for reading in readings]
    latest = readings[0] if readings else None
    summary = SensorSummary(
        sensor_id=sensor_id,
        latest=latest,
        count_1h=len(readings),
        min_value_1h=min(values) if values else None,
        max_value_1h=max(values) if values else None,
        avg_value_1h=(sum(values) / len(values)) if values else None,
        source="cassandra",
    )
    await get_redis_client().setex(
        cache_key,
        30,
        json.dumps(summary.model_dump(mode="json")),
    )
    return summary
