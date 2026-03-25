from typing import Annotated
from pydantic import BaseModel, Field
from uuid import uuid4

from asyncpg import Connection
import pygit2

from fastapi import APIRouter, Form, HTTPException, Request, status

from app.postgres import Repository, RepositoryPageView, acquire
from app.dependencies import Config, SessionAuth, templates

router = APIRouter(prefix="/repositories")


class CreateReposiotryForm(BaseModel):
    reponame: str = Field(min_length=1, max_length=50)
    public: bool = Field(default=True)


@router.post("/")
async def create_repo(req: Request, session: SessionAuth, form: Annotated[CreateReposiotryForm, Form()]):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        conn: Connection
        async with conn.transaction():

            repo = Repository(
                repository_id=uuid4(),
                name=form.reponame,
                stars=0,
                public=form.public,
                owner_id=session.user_id,
                fork_of=None,
            )
            await repo.insert(conn)

            repo_path = Config.repositories_path / session.username / form.reponame
            pygit2.init_repository(
                repo_path,
                bare=True,
                flags=pygit2.enums.RepositoryInitFlag.MKPATH | pygit2.enums.RepositoryInitFlag.NO_REINIT,
            )

    return templates.TemplateResponse(
        req,
        "repository_list_item.html",
        context={
            "is_owner": True,
            "repo": RepositoryPageView(
                repository_id=repo.repository_id,
                name=repo.name,
                public=repo.public,
                stars=repo.stars,
                fork_of=repo.fork_of,
                owner_id=session.user_id,
                username=session.username,
            ),
        },
    )


# @router.patch("/{repository_id}/fork", name="create_repository_fork")
# async def create_fork(req: Request, res: Response, repository_id: str, user: SessionAuth):
#     if not user:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
#
#     f = await req.form()
#     name = form_get_str(f, "name") or ""
#
#     repo = await fork_repository(user, repository_id, name)
#
#     res.headers["HX-Redirect"] = f"/{user.username}/{repo.name}"
