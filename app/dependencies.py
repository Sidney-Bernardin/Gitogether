import os
import jwt
import bcrypt

from uuid import UUID
from typing import Annotated, Tuple
from pydantic.dataclasses import dataclass
from asyncpg import Connection

from fastapi import Depends, HTTPException, Path, Request, status
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


username_regex = r"^[a-zA-Z0-9_-]+$"
UsernamePathParam = Annotated[str, Path(title="username", pattern=username_regex)]

reponame_regex = r"^[a-zA-Z0-9_-]+$"
ReponamePathParam = Annotated[str, Path(title="reponame", pattern=reponame_regex)]


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
        username: UsernamePathParam,
        reponame: ReponamePathParam,
        service: str,
    ) -> Tuple[User | None, Repository]:
        async with acquire() as conn:
            conn: Connection

            repo = await Repository.select_by_names(conn, username, reponame)
            if not repo:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            if not repo.private and service == "git-upload-pack":
                return (None, repo)

            credentials = await super().__call__(req)
            assert credentials is not None

            user = await User.select_by_username(conn, credentials.username)
            if (
                user is None
                or not bcrypt.checkpw(credentials.password.encode(), user.password)
                or (
                    repo.owner_id != user.user_id
                    and not await Repository.has_contributor(conn, repo.repository_id, user.user_id)
                )
            ):
                print(user is None)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return (user, repo)


_git_auth = GitAuth()
git_auth = Annotated[Tuple[User | None, Repository], Depends(_git_auth)]
