import bcrypt
from asyncpg import Connection
from uuid import UUID, uuid4
from pydantic import BaseModel

from app.postgres import acquire
from app.domain import DomainError, DomainErrorType


class User(BaseModel):
    user_id: UUID

    username: str
    password: bytes | None = None


async def signup_user(username: str, password: str) -> User:

    if len(username) < 3 or 30 < len(username):
        raise DomainError(DomainErrorType.USERNAME_INVALID, "must be between 3 and 30")

    if len(password) < 6 or 100 < len(password):
        raise DomainError(DomainErrorType.PASSWORD_INVALID, "must be between 6 and 100")

    async with acquire() as conn:
        conn: Connection

        if await conn.fetchrow(
            """SELECT user_id FROM users WHERE username = $1""",
            username,
        ):
            raise DomainError(DomainErrorType.USERNAME_TAKEN, "that username is in use by another user")

        user = User(
            user_id=uuid4(),
            username=username,
            password=bcrypt.hashpw(password.encode(), bcrypt.gensalt()),
        )

        await conn.execute(
            """
            INSERT INTO users (user_id, username, password)
            VALUES ($1, $2, $3)
            """,
            user.user_id,
            user.username,
            user.password,
        )

    return user


async def select_user_by_username(conn: Connection, username: str) -> User:
    async with acquire() as conn:
        conn: Connection

        user = await conn.fetchrow(
            """
            SELECT user_id, username, password
            FROM users WHERE username = $1
            """,
            username,
        )

        if not user or not bcrypt.checkpw(password.encode(), user["password"]):
            raise DomainError(DomainErrorType.USERNAME_OR_PASSWORD_INVALID, "invalid username or password")

    return User.model_validate(dict(user), extra="ignore")


async def get_user_by_username(username: str) -> User:
    async with acquire() as conn:
        conn: Connection

        user = await conn.fetchrow(
            """
            SELECT user_id, username
            FROM users WHERE username = $1
            """,
            username,
        )

        if not user:
            raise DomainError(DomainErrorType.USER_NOT_FOUND, "invalid username or password")

    return User.model_validate(dict(user), extra="ignore")
