from typing import Self
from pydantic.dataclasses import dataclass
from uuid import UUID
from asyncpg import Connection

from .postgres import fetchrows, fetchrow


@dataclass
class Repository:
    repository_id: UUID
    name: str
    stars: int
    public: bool

    owner_id: UUID
    fork_of: UUID | None

    async def insert(self, c: Connection) -> str:
        return await c.execute(
            """
            INSERT INTO repositories (repository_id, name, public, stars, owner_id, fork_of)
            VALUES ($1, $2, $3, $4, $5)
            """,
            self.repository_id,
            self.name,
            self.public,
            self.stars,
            self.owner_id,
            self.fork_of,
        )

    @classmethod
    async def select_by_names(cls, c: Connection, username: str, reponame: str) -> Self | None:
        return await fetchrow(
            c,
            cls,
            """
            SELECT repository_id, name, public, stars, fork_of, owner_id 
            FROM repositories r
            LEFT JOIN users u ON u.user_id = r.owner_id
            WHERE u.username = $1 AND r.name = $2
            """,
            username,
            reponame,
        )

    @classmethod
    async def select_by_owner_id(
        cls,
        c: Connection,
        owner_id: UUID,
        public_only: bool,
    ) -> list[Self]:
        return await fetchrows(
            c,
            cls,
            """
            SELECT repository_id, name, public, stars, fork_of, owner_id
            FROM repositories
            WHERE
                owner_id = $1 AND
                public = COALESCE($2, public)
            """,
            owner_id,
            public_only or None,
        )

    @classmethod
    async def select_by_contributor_id(
        cls,
        c: Connection,
        contributor_id: UUID,
        public_only: bool | None,
    ) -> list[Self]:
        return await fetchrows(
            c,
            cls,
            """
            SELECT repository_id, name, public, stars, fork_of, owner_id
            FROM repositories
            WHERE EXISTS (
                SELECT FROM repository_contributors
                WHERE
                    user_id = $1 AND
                    public = COALESCE($2, public)
            )
            """,
            contributor_id,
            public_only or None,
        )


@dataclass
class RepositoryPageView:
    repository_id: UUID
    name: str
    stars: int
    public: bool

    owner_id: UUID
    username: str

    fork_of: UUID | None

    @classmethod
    async def select_by_names(cls, c: Connection, username: str, repo_name: str) -> Self | None:
        return await fetchrow(
            c,
            cls,
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
