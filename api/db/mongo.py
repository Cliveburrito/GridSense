from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from core.config import get_settings


@lru_cache
def get_mongo_client() -> MongoClient:
    settings = get_settings()
    return MongoClient(
        host=settings.mongo_host,
        port=settings.mongo_port,
        username=settings.mongo_username,
        password=settings.mongo_password,
        authSource="admin",
    )


def get_mongo_database() -> Database:
    settings = get_settings()
    return get_mongo_client()[settings.mongo_database]
