from datetime import datetime
import pygit2

from typing import Annotated
from uuid import UUID, uuid4
from asyncpg import Connection

from pydantic import BaseModel, Field
from pydantic_core import PydanticCustomError

from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError

from app.dependencies import Config, TemplateData, SessionAuth, reponame_regex
from app.postgres import Repository, RepositoryPageView, PullRequest, acquire

router = APIRouter(prefix="/repositories")


class CreateReposiotryForm(BaseModel):
    reponame: str = Field(min_length=1, max_length=50, pattern=reponame_regex)
    description: str = Field(max_length=150)
    private: bool = Field(default=False)
    tags: list[str] = Field(default_factory=list)


@router.post("/")
async def create_repository(
    res: Response,
    session: SessionAuth,
    form: Annotated[CreateReposiotryForm, Form()],
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        conn: Connection
        async with conn.transaction():

            # Ensure the repository's name isn't taken.
            if await Repository.is_names_taken(conn, username=session.username, reponame=form.reponame):
                raise RequestValidationError([PydanticCustomError("reponame_taken", "Repository name taken.")])

            # Create the repository.
            repo = Repository(
                repository_id=uuid4(),
                reponame=form.reponame,
                description=form.description,
                private=form.private,
                stars=0,
                tags=form.tags,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                owner_id=session.user_id,
                parent_id=None,
            )

            await repo.insert(conn)

            # Initialize the repository with Git.
            repo_path = Config.repositories_path / session.username / form.reponame
            pygit2.init_repository(
                repo_path,
                bare=True,
                flags=pygit2.enums.RepositoryInitFlag.MKPATH | pygit2.enums.RepositoryInitFlag.NO_REINIT,
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

            # Get the repository.
            repo = await RepositoryPageView.select_by_id(conn, repository_id=UUID(repository_id))
            if not repo:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            # Ensure the repository isn't a fork.
            if repo.parent_id is not None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

            # Ensure the fork-repository's name isn't taken.
            if await Repository.is_names_taken(conn, username=session.username, reponame=form.reponame):
                raise RequestValidationError([PydanticCustomError("reponame_taken", "Repository name taken.")])

            # Create the fork-repository.
            fork_repo = Repository(
                repository_id=uuid4(),
                reponame=form.reponame,
                description=repo.description,
                private=False,
                stars=0,
                tags=repo.tags,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                owner_id=session.user_id,
                parent_id=UUID(repository_id),
            )

            await fork_repo.insert(conn)

            # Clone the repository with Git.
            fork_repo = pygit2.clone_repository(
                str(Config.repositories_path / repo.owner_username / repo.reponame),  # old
                str(Config.repositories_path / session.username / form.reponame),  # new
                bare=True
            )
            fork_repo.remotes.delete("origin")

    res.headers["HX-Redirect"] = f"/{session.username}/{fork_repo.reponame}"


class CreatePullRequestForm(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=1000)
    source_repo_id: str | None = Field(default=None)
    source_branch: str = Field(min_length=1, max_length=1000)
    target_branch: str = Field(min_length=1, max_length=1000)


@router.post("/{target_repo_id}/pull-requests", name="create_pull_request")
async def create_pull_request(
    res: Response,
    session: SessionAuth,
    target_repo_id: str,
    form: Annotated[CreatePullRequestForm, Form()],
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        conn: Connection
        async with conn.transaction():

            # Get the repositories.
            target_repo = await RepositoryPageView.select_by_id(conn, UUID(target_repo_id))
            source_repo = await RepositoryPageView.select_by_id(conn, UUID(form.source_repo_id))
            if not target_repo or (form.source_repo_id and not source_repo):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

            # Create the pull-request.
            pull_req = PullRequest(
                pull_request_id=uuid4(),
                title=form.title,
                description=form.description,
                source_branch=form.source_branch,
                target_branch=form.target_branch,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                source_id=UUID(
                    form.source_repo_id) if form.source_repo_id else None,
                target_id=UUID(target_repo_id),
            )

            await pull_req.insert(conn)

            # Open the repoisitory's Git data.
            repo = pygit2.Repository(Config.repositories_path / target_repo.owner_username / target_repo.reponame)

            # If there's a source repository, add the remote to the target repository.
            if source_repo:
                repo.remotes.create(
                    str(pull_req.pull_request_id),
                    str(Config.repositories_path /
                        source_repo.owner_username / source_repo.reponame),
                )

    res.headers["HX-Redirect"] = f"/{target_repo.owner_username}/{target_repo.reponame}/pull-requests/{pull_req.pull_request_id}"


class GetBranchesResponse(TemplateData):
    branches: list[str]


@router.get("/{repository_id}/branches", name="get_branches")
async def get_branches(
    req: Request,
    session: SessionAuth,
    repository_id: str,
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    data = GetBranchesResponse(req, "components/pull_request_branch_options.html")

    async with acquire() as conn:
        conn: Connection

        # Get the repository.
        repo = await RepositoryPageView.select_by_id(conn, UUID(repository_id))
        if not repo:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        # Ensure the user is the owner or a contributor.
        if repo.owner_id != session.user_id and not await Repository.has_contributor(conn, repo.repository_id, session.user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        # Open the repoisitory's Git data.
        repository = pygit2.Repository(Config.repositories_path / repo.owner_username / repo.reponame)

        data.branches = [b for b in repository.branches.local]

    return data()
