import os
import jwt
import bcrypt
import asyncpg
from typing import Annotated, Literal, Tuple, overload

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic
from fastapi.templating import Jinja2Templates
from fastapi.datastructures import FormData
import pygit2
from starlette.datastructures import UploadFile

from app.domain.errors import DomainError, DomainErrorType
from app.postgres import acquire
from app.config import Config
from app.domain import User, Repository

templates = Jinja2Templates(os.path.join(os.path.dirname(__file__), "templates"))


def session_auth(req: Request) -> User | None:
    try:
        session = jwt.decode(req.cookies["session"], Config.jwt_secret, algorithms=["HS256"])
        return User.model_validate(session, extra="ignore")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except KeyError:
        return None


SessionAuth = Annotated[User | None, Depends(session_auth)]


class GitAuth(HTTPBasic):
    async def __call__(self, req: Request, username: str, repo_name: str, service: str) -> Tuple[User | None, Repository]:
        async with acquire() as conn:
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
                return (None, repo)

            credentials = await super().__call__(req)
            assert credentials is not None

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

        return (None, repo)


_git_auth = GitAuth()
git_auth = Annotated[Tuple[User, Repository], Depends(_git_auth)]


def form_get(form: FormData, key: str) -> str | None:
    val = form.get(key)
    if isinstance(val, UploadFile):
        raise HTTPException(
            detail=f"The {key} field cannot be a file",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
    return val


def str_to_bool(s: str) -> bool:
    return s == "true" or s == "on" or s == "yes"
