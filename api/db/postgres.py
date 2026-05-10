import asyncio
import json
import os

import asyncpg

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def _init_connection(conn: asyncpg.Connection) -> None:
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool

    async with _pool_lock:
        if _pool is not None:
            return _pool

        _pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "billing-db"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "gridsense_billing"),
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            min_size=1,
            max_size=10,
            init=_init_connection,
        )
        return _pool


async def fetch(query: str, *args) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return [dict(record) for record in await conn.fetch(query, *args)]


async def fetchrow(query: str, *args) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        record = await conn.fetchrow(query, *args)
        return dict(record) if record is not None else None


async def shutdown() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
