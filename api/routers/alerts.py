import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from db.redis import get_redis_client

router = APIRouter(prefix="/alerts", tags=["alerts"])


ACTIVE_ALERTS_KEY = "alerts:active"
ALERTS_CHANNEL = "fault-alerts"


@router.get("/active")
async def get_active_alerts():
    alerts = await get_redis_client().hvals(ACTIVE_ALERTS_KEY)
    return {"alerts": [json.loads(alert) for alert in alerts]}


@router.post("/publish")
async def publish_alert(alert: dict[str, Any]):
    if not alert.get("node_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="node_id is required.",
        )

    alert_id = str(alert.get("alert_id") or uuid4())
    payload = {
        "alert_id": alert_id,
        "node_id": alert["node_id"],
        "severity": alert.get("severity", "warning"),
        "message": alert.get("message", "Fault alert"),
        "created_at": alert.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "expires_in_seconds": int(alert.get("expires_in_seconds", 300)),
    }

    redis = get_redis_client()
    await redis.hset(ACTIVE_ALERTS_KEY, alert_id, json.dumps(payload))
    await redis.expire(ACTIVE_ALERTS_KEY, payload["expires_in_seconds"])
    await redis.publish(ALERTS_CHANNEL, json.dumps(payload))
    return payload
