from asyncpg import Connection


async def fetchrow(conn: Connection, view: type, query: str, *args):
    r = await conn.fetchrow(query, *args)
    return view(**dict(r)) if r else None


async def fetchrows(conn: Connection, view: type, query: str, *args):
    rr = await conn.fetch(query, *args)
    return [view(**dict(r)) for r in rr]
