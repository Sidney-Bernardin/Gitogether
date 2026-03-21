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
