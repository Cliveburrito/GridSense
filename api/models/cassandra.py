from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    sensor_id: str
    reading_time: datetime
    metric_type: str
    value: float
    unit: str
    quality_flag: int = Field(ge=0, le=9)
    district_id: str = "network"


class SensorReadingBatch(BaseModel):
    readings: list[SensorReading]


class SensorSummary(BaseModel):
    sensor_id: str
    latest: SensorReading | None = None
    count_1h: int
    min_value_1h: float | None = None
    max_value_1h: float | None = None
    avg_value_1h: float | None = None
    source: Literal["cache", "cassandra"] = "cassandra"
