import os
import jwt
import bcrypt

from uuid import UUID
from typing import Annotated, Tuple
from pydantic.dataclasses import dataclass
from asyncpg import Connection

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse

from app.postgres import Repository, User, acquire
from app.config import Config

templates = Jinja2Templates(os.path.join(os.path.dirname(__file__), "templates"))


class Res:
    request: Request

    def __init__(self, req: Request, template_name: str) -> None:
        self.request = req
        self.template_name = template_name

    def __call__(self) -> _TemplateResponse:
        return templates.TemplateResponse(self.template_name, vars(self))


@dataclass
class Session:
    user_id: UUID
    username: str


def session_auth(req: Request) -> Session | None:
    try:
        session = jwt.decode(req.cookies["session"], Config.jwt_secret, algorithms=["HS256"])
        return Session(session["user_id"], session["username"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except KeyError:
        return None


SessionAuth = Annotated[Session | None, Depends(session_auth)]


class GitAuth(HTTPBasic):
    async def __call__(
        self,
        req: Request,
        username: str,
        repo_name: str,
        service: str,
    ) -> Tuple[User | None, Repository]:
        async with acquire() as conn:
            conn: Connection

            repo = await Repository.select_by_names(conn, username, repo_name)
            if not repo:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            if repo.public and service == "git-upload-pack":
                return (None, repo)

            credentials = await super().__call__(req)
            assert credentials is not None

            user = await User.select_by_username(conn, username)
            if (
                not user
                or repo.owner_id != user.user_id
                or not bcrypt.checkpw(credentials.password.encode(), user.password)
            ):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return (user, repo)


_git_auth = GitAuth()
git_auth = Annotated[Tuple[User | None, Repository], Depends(_git_auth)]
