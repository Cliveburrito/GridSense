import os
from functools import lru_cache

from neo4j import AsyncDriver, AsyncGraphDatabase


@lru_cache
def get_driver() -> AsyncDriver:
    return AsyncGraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://graph-db:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )


async def shutdown() -> None:
    if get_driver.cache_info().currsize:
        await get_driver().close()
