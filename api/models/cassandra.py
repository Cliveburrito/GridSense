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


class SensorReadingBatch(BaseModel):
    readings: list[SensorReading]


class SensorSummary(BaseModel):
    sensor_id: str
    status: Literal["not_implemented"] = "not_implemented"
