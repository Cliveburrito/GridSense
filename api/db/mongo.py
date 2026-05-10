import os
from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


@lru_cache
def get_mongo_client() -> AsyncIOMotorClient:
    return AsyncIOMotorClient(
        host=os.getenv("MONGO_HOST", "catalog-db"),
        port=int(os.getenv("MONGO_PORT", "27017")),
        username=os.environ["MONGO_INITDB_ROOT_USERNAME"],
        password=os.environ["MONGO_INITDB_ROOT_PASSWORD"],
        authSource="admin",
    )


def get_mongo_database() -> AsyncIOMotorDatabase:
    return get_mongo_client()[os.getenv("MONGO_INITDB_DATABASE", "gridsense_catalog")]


async def shutdown() -> None:
    if get_mongo_client.cache_info().currsize:
        get_mongo_client().close()
