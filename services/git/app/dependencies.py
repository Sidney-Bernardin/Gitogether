import os
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Path, Query, Request
from fastapi.security import HTTPBasic
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND

from app.views import GitQueryParams

from .env import env
from .postgres import AsyncSessionMaker
from .postgres.models import Repository, RepositoryContributors, User

templates = Jinja2Templates(os.path.join(os.path.dirname(__file__), "ui"))


async def dep_postgres():
    async with AsyncSessionMaker() as session:
        yield session


DepPostgres = Annotated[AsyncSession, Depends(dep_postgres)]


class Session(BaseModel):
    user_id: int
    username: str


username_regex = r"^[a-zA-Z0-9_-]+$"
UsernamePathParam = Annotated[str, Path(title="username", pattern=username_regex)]

reponame_regex = r"^[a-zA-Z0-9_-]+$"
ReponamePathParam = Annotated[str, Path(title="reponame", pattern=reponame_regex)]


async def dep_session_auth(req: Request) -> Session | None:
    try:
        cookie = req.cookies.get("session")
        if not cookie:
            return None

        token = jwt.decode(cookie, env.JWT_SECRET, algorithms=["HS256"])
        return Session.model_validate(token)

    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except KeyError:
        return None


DepSessionAuth = Annotated[Session | None, Depends(dep_session_auth)]


class _DepGitAuth(HTTPBasic):
    async def __call__(
        self,
        req: Request,
        pg: DepPostgres,
        username: UsernamePathParam,
        reponame: ReponamePathParam,
        query: Annotated[GitQueryParams, Query()],
    ) -> tuple[User | None, Repository]:

        repository = (
            await pg.execute(
                select(
                    Repository,
                )
                .where(Repository.reponame == reponame)
                .options(
                    load_only(
                        Repository.id,
                        Repository.reponame,
                        Repository.private,
                        Repository.owner_id,
                        raiseload=True,
                    )
                )
            )
        ).scalar_one_or_none()

        if not repository:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND)

        # Skip auth when reading public repo.
        # git-upload-pack means client is reading, unintuitive but thats the way it is.
        if not repository.private and query.service == "git-upload-pack":
            return (None, repository)

        credentials = await super().__call__(req)
        assert credentials is not None

        user = (
            await pg.execute(
                select(User)
                .outerjoin(User.shared_repositories)
                .where(
                    and_(
                        User.username == credentials.username,
                        or_(
                            User.id == repository.owner_id,
                            User.shared_repositories.any(
                                RepositoryContributors.repository_id == repository.id
                            ),
                        ),
                    )
                )
            )
        ).scalar_one_or_none()

        if not user or not bcrypt.checkpw(
            credentials.password.encode(), user.password_hash
        ):
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED)

        return (user, repository)


dep_git_auth = _DepGitAuth()
DepGitAuth = Annotated[tuple[User | None, Repository], Depends(dep_git_auth)]
