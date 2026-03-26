from typing import Self
from pydantic.dataclasses import dataclass
from uuid import UUID
from asyncpg import Connection

from .postgres import fetchrows, fetchrow


@dataclass
class Repository:
    repository_id: UUID

    reponame: str
    private: bool
    stars: int

    owner_id: UUID
    fork_id: UUID | None

    async def insert(self, c: Connection) -> str:
        return await c.execute(
            """
            INSERT INTO repositories (repository_id, reponame, private, stars, owner_id, fork_id)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            self.repository_id,
            self.reponame,
            self.private,
            self.stars,
            self.owner_id,
            self.fork_id,
        )

    @classmethod
    async def has_contributor(cls, c: Connection, repository_id: UUID, user_id: UUID) -> bool:
        return (
            await c.fetchrow(
                """
                SELECT 1 FROM repository_contributors
                WHERE
                    repository_id = $1 AND
                    user_id = $2
                """,
                repository_id,
                user_id,
            )
            is not None
        )

    @classmethod
    async def select_exists_by_names(cls, c: Connection, username: str, reponame: str) -> bool:
        return (
            await c.fetchrow(
                """
            SELECT 1 FROM repositories
            WHERE
                reponame = $1 AND
                EXISTS (
                    SELECT 1 FROM users
                    WHERE username = $2
                )
            """,
                reponame,
                username,
            )
            is not None
        )

    @classmethod
    async def select_by_names(cls, c: Connection, username: str, reponame: str) -> Self | None:
        return await fetchrow(
            c,
            cls,
            """
            SELECT repository_id, reponame, private, stars, fork_id, owner_id 
            FROM repositories r
            LEFT JOIN users u ON u.user_id = r.owner_id
            WHERE u.username = $1 AND r.reponame = $2
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
            SELECT repository_id, reponame, private, stars, fork_id, owner_id
            FROM repositories
            WHERE
                owner_id = $1 AND
                private = COALESCE($2, private)
            """,
            owner_id,
            False if public_only else None,
        )

    @classmethod
    async def select_by_contributor_id(
        cls,
        c: Connection,
        contributor_id: UUID,
        public_only: bool,
    ) -> list[Self]:
        return await fetchrows(
            c,
            cls,
            """
            SELECT repository_id, reponame, private, stars, fork_id, owner_id
            FROM repositories
            WHERE EXISTS (
                SELECT FROM repository_contributors
                WHERE
                    user_id = $1 AND
                    private = COALESCE($2, private)
            )
            """,
            contributor_id,
            False if public_only else None,
        )


@dataclass
class RepositoryPageView:
    repository_id: UUID

    reponame: str
    private: bool
    stars: int

    owner_id: UUID
    username: str

    fork_id: UUID | None

    @classmethod
    async def select_by_id(cls, c: Connection, repository_id: UUID) -> Self | None:
        return await fetchrow(
            c,
            cls,
            """
            SELECT
                r.repository_id, r.reponame, r.stars, r.private, r.fork_id,
                r.owner_id, u.username
            FROM repositories r
            LEFT JOIN users u ON u.user_id = r.owner_id
            WHERE
                r.repository_id = $1
            """,
            repository_id,
        )

    @classmethod
    async def select_by_names(cls, c: Connection, username: str, reponame: str) -> Self | None:
        return await fetchrow(
            c,
            cls,
            """
            SELECT
                r.repository_id, r.reponame, r.stars, r.private, r.fork_id,
                r.owner_id, u.username
            FROM repositories r
            LEFT JOIN users u ON u.user_id = r.owner_id
            WHERE
                u.username = $1 AND
                r.reponame = $2
            """,
            username,
            reponame,
        )
