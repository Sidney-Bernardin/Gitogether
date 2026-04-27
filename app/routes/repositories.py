import pygit2

from typing import Annotated
from uuid import UUID, uuid4
from asyncpg import Connection

from pydantic import BaseModel, Field
from pydantic_core import PydanticCustomError

from fastapi import APIRouter, Form, HTTPException, Response, status
from fastapi.exceptions import RequestValidationError

from app.postgres import Repository, RepositoryPageView, PullRequest, acquire
from app.dependencies import Config, SessionAuth, reponame_regex

router = APIRouter(prefix="/repositories")


class CreateReposiotryForm(BaseModel):
    reponame: str = Field(min_length=1, max_length=50, pattern=reponame_regex)
    description: str = Field(max_length=150)
    private: bool = Field(default=False)
    tags: list[str] = Field(default_factory=list)


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
                description=form.description,
                private=form.private,
                stars=0,
                tags=form.tags,
                owner_id=session.user_id,
                parent_id=None,
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

            if source_repo.parent_id is not None:
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
                parent_id=UUID(repository_id),
            )
            await repo.insert(conn)

            source_path = (
                Config.repositories_path / source_repo.owner_username / source_repo.reponame
            )
            dest_path = Config.repositories_path / session.username / form.reponame
            fork_repo = pygit2.clone_repository(str(source_path), str(dest_path), bare=True)
            fork_repo.remotes.delete("origin")

    res.headers["HX-Redirect"] = f"/{session.username}/{repo.reponame}"


class CreatePullRequestForm(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=1000)
    source_branch: str = Field(min_length=1, max_length=1000)
    target_branch: str = Field(min_length=1, max_length=1000)


@router.post("/{target_repo_id}/pull-requests", name="create_pull_request")
async def create_pull_request(
    res: Response,
    session: SessionAuth,
    target_repo_id: str,
    form: Annotated[CreatePullRequestForm, Form()],
    child: str | None = None,
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        conn: Connection
        async with conn.transaction():

            target_repo = await RepositoryPageView.select_by_id(conn, UUID(target_repo_id))
            source_repo = await RepositoryPageView.select_by_id(conn, UUID(child))

            if not target_repo or (child and not source_repo):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            pr = PullRequest(
                pull_request_id=uuid4(),
                title=form.title,
                description="",
                source_branch=form.source_branch,
                target_branch=form.target_branch,
                source_id=UUID(child) if child else UUID(target_repo_id),
                target_id=UUID(target_repo_id),
            )

            await pr.insert(conn)

            repo = pygit2.Repository(
                Config.repositories_path / target_repo.owner_username / target_repo.reponame
            )

            if child and source_repo:
                repo.remotes.create(
                    str(pr.pull_request_id),
                    str(
                        Config.repositories_path / source_repo.owner_username / source_repo.reponame
                    ),
                )

    res.headers["HX-Redirect"] = (
        f"/{target_repo.owner_username}/{target_repo.reponame}/pull-requests/{pr.pull_request_id}"
    )
