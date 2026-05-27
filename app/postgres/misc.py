from typing import Self
from uuid import UUID

from pydantic.dataclasses import dataclass
from asyncpg import Connection

from .utils import fetchrows


@dataclass
class SearchResult:
    user_id: UUID
    username: str

    repository_id: UUID
    reponame: str

    @classmethod
    async def select_by_name_similarity(cls, c: Connection, username: str, reponame: str) -> list[Self]:
        return await fetchrows(
            c, cls,
            """
            SELECT
                u.user_id, u.username,
                r.repository_id, r.reponame
            FROM users u
            LEFT JOIN repositories r ON u.user_id = r.owner_id
            WHERE
                similarity(u.username, $1) > 0.1
                OR
                similarity(r.reponame, $2) > 0.1
            """,
            username,
            reponame,
        )
