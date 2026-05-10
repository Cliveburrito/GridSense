import os
from functools import lru_cache

from redis.asyncio import Redis


@lru_cache
def get_redis_client() -> Redis:
    return Redis(
        host=os.getenv("REDIS_HOST", "cache"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )


async def shutdown() -> None:
    if get_redis_client.cache_info().currsize:
        await get_redis_client().aclose()
