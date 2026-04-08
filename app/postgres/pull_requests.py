from typing import Self
from pydantic.dataclasses import dataclass
from uuid import UUID
from asyncpg import Connection

from .postgres import fetchrow


@dataclass
class PullRequest:
    pull_request_id: UUID

    title: str
    description: str
    source_branch: str
    target_branch: str

    source_id: UUID
    target_id: UUID

    async def insert(self, c: Connection) -> str:
        return await c.execute(
            """
            INSERT INTO pull_requests (
                pull_request_id,
                title, description, source_branch, target_branch,
                source_id, target_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            self.pull_request_id,
            self.title,
            self.description,
            self.source_branch,
            self.target_branch,
            self.source_id,
            self.target_id,
        )

    @classmethod
    async def select_by_id(cls, c: Connection, pull_request_id: UUID) -> Self | None:
        return await fetchrow(
            c,
            PullRequest,
            """
            SELECT
                pull_request_id,
                title, description, source_branch, target_branch,
                source_id, target_id
            FROM pull_requests
            WHERE pull_request_id = $1
            """,
            pull_request_id,
        )
