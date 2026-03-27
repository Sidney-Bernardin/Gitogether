import pygit2

from typing import Annotated
from uuid import UUID, uuid4
from asyncpg import Connection

from pydantic import BaseModel, Field
from pydantic_core import PydanticCustomError

from fastapi import APIRouter, Form, HTTPException, Response, status
from fastapi.exceptions import RequestValidationError

from app.postgres import Repository, RepositoryPageView, acquire
from app.dependencies import Config, SessionAuth, reponame_regex

router = APIRouter(prefix="/repositories")


class CreateReposiotryForm(BaseModel):
    reponame: str = Field(min_length=1, max_length=50, pattern=reponame_regex)
    private: bool = Field(default=False)


@router.post("/")
async def create_repo(
    res: Response,
    session: SessionAuth,
    form: Annotated[CreateReposiotryForm, Form()],
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        conn: Connection
        async with conn.transaction():

            if await Repository.is_names_taken(
                conn, username=session.username, reponame=form.reponame
            ):
                raise RequestValidationError(
                    [PydanticCustomError("reponame_taken", "Repository name taken.")]
                )

            repo = Repository(
                repository_id=uuid4(),
                reponame=form.reponame,
                private=form.private,
                stars=0,
                owner_id=session.user_id,
                fork_id=None,
            )

            await repo.insert(conn)

            repo_path = Config.repositories_path / session.username / form.reponame
            pygit2.init_repository(
                repo_path,
                bare=True,
                flags=pygit2.enums.RepositoryInitFlag.MKPATH
                | pygit2.enums.RepositoryInitFlag.NO_REINIT,
            )

    res.headers["HX-Redirect"] = f"/{session.username}/{repo.reponame}"


class ForkReposiotryForm(BaseModel):
    reponame: str = Field(min_length=1, max_length=50, pattern=reponame_regex)


@router.patch("/{repository_id}/fork", name="fork_repository")
async def fork_repository(
    res: Response,
    session: SessionAuth,
    repository_id: str,
    form: Annotated[ForkReposiotryForm, Form()],
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        conn: Connection
        async with conn.transaction():

            source_repo = await RepositoryPageView.select_by_id(
                conn, repository_id=UUID(repository_id)
            )

            if not source_repo:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            if source_repo.fork_id is not None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            if await Repository.is_names_taken(
                conn, username=session.username, reponame=form.reponame
            ):
                raise RequestValidationError(
                    [PydanticCustomError("reponame_taken", "Repository name taken.")]
                )

            repo = Repository(
                repository_id=uuid4(),
                reponame=form.reponame,
                private=False,
                stars=0,
                owner_id=session.user_id,
                fork_id=UUID(repository_id),
            )
            await repo.insert(conn)

            source_path = (
                Config.repositories_path / source_repo.owner_username / source_repo.reponame
            )
            dest_path = Config.repositories_path / session.username / form.reponame
            pygit2.clone_repository(str(source_path), str(dest_path))

    res.headers["HX-Redirect"] = f"/{session.username}/{repo.reponame}"
