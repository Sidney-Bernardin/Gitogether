import asyncpg

from app.config import Config

pool: asyncpg.Pool | None = None


async def init():
    global pool
    pool = await asyncpg.create_pool(Config.postgres_url)


async def close():
    assert isinstance(pool, asyncpg.Pool)
    await pool.close()


def acquire():
    assert isinstance(pool, asyncpg.Pool)
    return pool.acquire()
