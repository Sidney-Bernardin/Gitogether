from asyncpg import Pool, Connection, create_pool

from app.config import Config

pool: Pool | None = None


async def init():
    global pool
    pool = await create_pool(Config.postgres_url)


async def close():
    assert pool is not None
    await pool.close()


def acquire():
    assert pool is not None
    return pool.acquire()


async def fetchrow(conn: Connection, view, query: str, *args):
    record = await conn.fetchrow(query, *args)
    if not record:
        raise KeyError
    return view(**dict(record))
