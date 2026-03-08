import os
import jwt
import bcrypt
import pathlib
import asyncpg
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic
from fastapi.templating import Jinja2Templates


class Config:
    jwt_secret = os.getenv("APP_JWT_SECRET", "foobarbaz")
    session_expiry_hours = int(os.getenv("APP_SESSION_EXPIRY_HOURS", "24"))
    postgres_url = os.getenv("APP_POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/postgres")


templates = Jinja2Templates(os.path.join(os.path.dirname(__file__), "templates"))
repositories_path = pathlib.Path("tmp/gitogether/repositories")


def session_auth(req: Request):
    try:
        return jwt.decode(req.cookies["session"], Config.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except KeyError:
        return None


SessionAuth = Annotated[dict | None, Depends(session_auth)]


class GitAuth(HTTPBasic):
    async def __call__(self, req: Request, username: str, repo_name: str, service: str) -> dict:
        async with req.app.state.pg.acquire() as conn:
            conn: asyncpg.Connection

            repo = await conn.fetchrow(
                """
                SELECT repository_id, public
                FROM repositories r
                LEFT JOIN users u ON u.user_id = r.owner_id
                WHERE u.username = $1 AND r.name = $2
                """,
                username,
                repo_name,
            )
            if not repo:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            if repo["public"] and service == "git-upload-pack":
                return repo

            credentials = await super().__call__(req)
            if not credentials:
                raise Exception("===== NOT credentials =====")

            user = await conn.fetchrow(
                """
                SELECT u.password FROM users u
                LEFT JOIN repositories r ON r.owner_id = u.user_id
                WHERE
                    u.username = $1 AND
                    r.repository_id = $2
                """,
                credentials.username,
                repo["repository_id"],
            )

            if not user or not bcrypt.checkpw(credentials.password.encode(), user["password"]):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return repo


_git_auth = GitAuth()
git_auth = Annotated[dict, Depends(_git_auth)]
