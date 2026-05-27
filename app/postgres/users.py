from typing import Self
from uuid import UUID

from asyncpg import Connection
from pydantic.dataclasses import dataclass

from .utils import fetchrow


@dataclass
class User:
    user_id: UUID
    username: str
    password: bytes

    async def insert(self, c: Connection) -> str:
        return await c.execute(
            """
            INSERT INTO users (user_id, username, password)
            VALUES ($1, $2, $3)
            """,
            self.user_id,
            self.username,
            self.password,
        )

    @classmethod
    async def is_username_taken(cls, c: Connection, username: str) -> bool:
        return await c.fetchrow(
            """
                SELECT 1 FROM users
                WHERE username = $1
                """,
            username,
        ) is not None

    @classmethod
    async def select_by_username(cls, c: Connection, username: str) -> Self | None:
        return await fetchrow(
            c, cls,
            """
            SELECT user_id, username, password
            FROM users
            WHERE username = $1
            """,
            username,
        )


@dataclass
class UserPageView:
    user_id: UUID
    username: str

    @classmethod
    async def select_by_id(cls, c: Connection, user_id: UUID) -> Self | None:
        return await fetchrow(
            c, cls,
            """
            SELECT user_id, username
            FROM users
            WHERE user_id = $1
            """,
            user_id,
        )

    @classmethod
    async def select_by_username(cls, c: Connection, username: str) -> Self | None:
        return await fetchrow(
            c, cls,
            """
            SELECT user_id, username
            FROM users
            WHERE username = $1
            """,
            username,
        )
