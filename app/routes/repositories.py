from typing import Annotated
import uuid
import asyncpg
import pygit2
from pydantic import BaseModel, Field
from fastapi import APIRouter, Form, HTTPException, Request, Response, status

import app.postgres as pg
from app.dependencies import Config, SessionAuth, templates
from app.domain.repositories import fork_repository

router = APIRouter(prefix="/repositories")


class CreateReposiotryForm(BaseModel):
    reponame: str = Field(min_length=1, max_length=50)
    public: bool = Field(default=True)


@router.post("/")
async def create_repo(req: Request, user: SessionAuth, form: Annotated[CreateReposiotryForm, Form()]):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    repository_id = uuid.uuid4()

    async with pg.acquire() as conn:
        conn: asyncpg.Connection
        async with conn.transaction():

            # Insert the repo.
            await pg.insert_repository(
                conn,
                repository_id=repository_id,
                name=form.reponame,
                stars=0,
                public=form.public,
                owner_id=user.user_id,
                fork_of=None,
            )

            # Init the repo.
            repo_path = Config.repositories_path / user.username / form.reponame
            pygit2.init_repository(
                repo_path,
                bare=True,
                flags=pygit2.enums.RepositoryInitFlag.MKPATH | pygit2.enums.RepositoryInitFlag.NO_REINIT,
            )

    repo = pg.RepositoryPage(
        repository_id=uuid.uuid4(),
        name=form.reponame,
        public=form.public,
        stars=0,
        fork_of=None,
        owner_id=user.user_id,
        username=user.username,
    )

    return templates.TemplateResponse(
        req,
        "repository_list_item.html",
        context={
            "repo": repo,
            "is_owner": True,
        },
    )


@router.patch("/{repository_id}/fork", name="create_repository_fork")
async def create_fork(req: Request, res: Response, repository_id: str, user: SessionAuth):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    f = await req.form()
    name = form_get_str(f, "name") or ""

    repo = await fork_repository(user, repository_id, name)

    res.headers["HX-Redirect"] = f"/{user.username}/{repo.name}"
