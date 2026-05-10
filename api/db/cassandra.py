import asyncio
import os
from functools import lru_cache
from typing import Any

from cassandra.cluster import Cluster, Session
from cassandra.query import PreparedStatement
from cassandra.query import dict_factory


@lru_cache
def get_cluster() -> Cluster:
    return Cluster(
        [os.getenv("CASSANDRA_HOST", "timeseries-db")],
        port=int(os.getenv("CASSANDRA_PORT", "9042")),
    )


@lru_cache
def get_session() -> Session:
    session = get_cluster().connect(os.getenv("CASSANDRA_KEYSPACE", "gridsense"))
    session.row_factory = dict_factory
    return session


@lru_cache
def prepare_statement(query: str) -> PreparedStatement:
    return get_session().prepare(query)


async def execute_async(query_or_statement: str | PreparedStatement, parameters=None) -> list[dict[str, Any]]:
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    statement = (
        prepare_statement(query_or_statement)
        if isinstance(query_or_statement, str)
        else query_or_statement
    )
    response = get_session().execute_async(statement, parameters)

    def on_success(rows):
        loop.call_soon_threadsafe(future.set_result, list(rows))

    def on_error(exc):
        loop.call_soon_threadsafe(future.set_exception, exc)

    response.add_callbacks(on_success, on_error)
    return await future


async def shutdown() -> None:
    if get_cluster.cache_info().currsize:
        get_cluster().shutdown()
