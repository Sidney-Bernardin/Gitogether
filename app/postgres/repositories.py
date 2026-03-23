from uuid import UUID
from asyncpg import Connection
from pydantic.dataclasses import dataclass

from .postgres import fetchrow


@dataclass()
class RepositoryPage:
    repository_id: UUID
    name: str
    stars: int
    public: bool

    fork_of: UUID | None

    owner_id: UUID
    username: str


async def insert_repository(
    c: Connection,
    repository_id: UUID,
    name: str,
    stars: int,
    public: bool,
    owner_id: UUID,
    fork_of: UUID | None,
):
    return await c.execute(
        """
        INSERT INTO repositories
            (repository_id, name, public, stars, owner_id, fork_of)
        VALUES ($1, $2, $3, $4, $5)
        """,
        repository_id,
        name,
        public,
        stars,
        owner_id,
        fork_of,
    )


async def select_repository_page(c: Connection, username: str, repo_name: str):
    return await fetchrow(
        c,
        RepositoryPage,
        """
        SELECT
            r.repository_id, r.name, r.stars, r.public, r.fork_of,
            r.owner_id, u.username
        FROM repositories r
        LEFT JOIN users u ON u.user_id = r.owner_id
        WHERE
            u.username = $1 AND
            r.name = $2
        """,
        username,
        repo_name,
    )
