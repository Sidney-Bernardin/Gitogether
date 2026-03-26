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


async def fetchrow(conn: Connection, view: type, query: str, *args):
    r = await conn.fetchrow(query, *args)
    print(
        "===================================================================================================="
    )
    print(query)
    print(args)
    print(r)
    return view(**dict(r)) if r else None


async def fetchrows(conn: Connection, view: type, query: str, *args):
    rr = await conn.fetch(query, *args)
    return [view(**dict(r)) for r in rr]
