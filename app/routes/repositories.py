import subprocess
from datetime import datetime
from typing import Annotated
from asyncpg import Connection
from uuid import UUID, uuid4

import pygit2
from pydantic import BaseModel, Field
from pydantic_core import PydanticCustomError
from fastapi import APIRouter, Form, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError

from app.dependencies import Config, TemplateData, DepSession, reponame_regex
from app.postgres import acquire
from app.postgres.repositories import Repository, RepositoryPageView
from app.postgres.pull_requests import PullRequest


router = APIRouter(prefix="/repositories")


class CreateReposiotryForm(BaseModel):
    reponame: str = Field(min_length=1, max_length=50, pattern=reponame_regex)
    description: str = Field(max_length=150)
    private: bool = Field(default=False)
    tags: list[str] = Field(default_factory=list)


@router.post("/")
async def create_repository(
    res: Response,
    session: DepSession,
    form: Annotated[CreateReposiotryForm, Form()],
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        conn: Connection
        async with conn.transaction():

            # Ensure the repository's name isn't taken.
            if await Repository.is_names_taken(conn, username=session.user.username, reponame=form.reponame):
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
                owner_id=session.user.user_id,
                parent_id=None,
            )

            await repo.insert(conn)

            # Initialize the repository with Git.
            repo_path = Config.repositories_path / session.user.username / form.reponame
            pygit2.init_repository(
                repo_path,
                bare=True,
                flags=pygit2.enums.RepositoryInitFlag.MKPATH | pygit2.enums.RepositoryInitFlag.NO_REINIT,
            )

    res.headers["HX-Redirect"] = f"/{session.user.username}/{repo.reponame}"


class ForkReposiotryForm(BaseModel):
    reponame: str = Field(min_length=1, max_length=50, pattern=reponame_regex)


@router.patch("/{repository_id}/fork", name="fork_repository")
async def fork_repository(
    res: Response,
    session: DepSession,
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
            if await Repository.is_names_taken(conn, username=session.user.username, reponame=form.reponame):
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
                owner_id=session.user.user_id,
                parent_id=UUID(repository_id),
            )

            await fork_repo.insert(conn)

            # Clone the repository with Git.
            clone = pygit2.clone_repository(
                str(Config.repositories_path / repo.owner_username / repo.reponame),  # old
                str(Config.repositories_path / session.user.username / form.reponame),  # new
                bare=True
            )
            clone.remotes.delete("origin")

    res.headers["HX-Redirect"] = f"/{session.user.username}/{fork_repo.reponame}"


class CreatePullRequestForm(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=1000)
    source_repository_id: str | None = Field(default=None)
    source_branch: str = Field(min_length=1, max_length=1000)
    target_branch: str = Field(min_length=1, max_length=1000)


@router.post("/{target_repository_id}/pull-requests", name="create_pull_request")
async def create_pull_request(
    res: Response,
    session: DepSession,
    target_repository_id: str,
    form: Annotated[CreatePullRequestForm, Form()],
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        conn: Connection
        async with conn.transaction():

            # Get the repositories.
            target_repo = await RepositoryPageView.select_by_id(conn, UUID(target_repository_id))
            source_repo = await RepositoryPageView.select_by_id(conn, UUID(form.source_repository_id))
            if not target_repo or (form.source_repository_id and not source_repo):
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
                owner_id=session.user.user_id,
                source_id=UUID(form.source_repository_id) if form.source_repository_id else None,
                target_id=UUID(target_repository_id),
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


@router.patch("/pull-requests/{pull_request_id}/complete", name="complete_pull_request")
async def complete_pull_request(
    res: Response,
    session: DepSession,
    pull_request_id: str,
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        async with conn.transaction():

            # Get the pull-request.
            pull_req = await PullRequest.select_by_id(conn, UUID(pull_request_id))
            if not pull_req:
                raise RequestValidationError([PydanticCustomError("pull_request_not_found", "This pull request doesn't exist.")])

            # Ensure the user is the owner or a contributor.
            if pull_req.owner_id != session.user.user_id and not await Repository.has_contributor(conn, pull_req.target_id, session.user.user_id):
                raise RequestValidationError([PydanticCustomError("unauthorized", "You're not authorized to complete this pull request.")])

            target_data = await RepositoryPageView.select_by_id(conn, pull_req.target_id)
            if not target_data:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            source_data = target_data

            target = pygit2.Repository(Config.repositories_path / target_data.owner_username / target_data.reponame)

            target_branch_ref_name = f"refs/heads/{pull_req.target_branch}"
            source_branch_ref_name = f"refs/heads/{pull_req.source_branch}"

            if pull_req.source_id:

                source_data = await RepositoryPageView.select_by_id(conn, pull_req.source_id)
                if not source_data:
                    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

                source_branch_ref_name = f"refs/remotes/{pull_req.pull_request_id}/{pull_req.source_branch}"
                target.remotes[str(pull_req.pull_request_id)].fetch()

            target_branch_ref = target.lookup_reference(target_branch_ref_name)
            source_branch_ref = target.lookup_reference(source_branch_ref_name)

            analasis, _ = target.merge_analysis(source_branch_ref.target, target_branch_ref_name)

            merge_oid: pygit2.Oid | str = ""
            merge_message = ""

            if analasis & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
                print("Can be fast-forwarded")
                merge_oid = source_branch_ref.target
                merge_message = f"Merge {pull_req.source_branch} into {pull_req.target_branch}"

            elif analasis & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
                print("Merge commit required")

                index = target.merge_commits(target_branch_ref.target, source_branch_ref.target)
                if index.conflicts:
                    print("Conflicts detected")
                    raise RequestValidationError([PydanticCustomError("merge_conflicts_deteted", "Merge conflicts detected.")])

                tree_oid = index.write_tree(target)

                author = pygit2.Signature(session.user.username, f"{session.user.username}@gitogether.com")
                committer = author
                merge_message = f"Merge {pull_req.source_branch} from {source_data.owner_username}/{source_data.reponame} into {pull_req.target_branch}"
                merge_oid = target.create_commit(
                    None, author, committer, merge_message, tree_oid,
                    [target_branch_ref.target, source_branch_ref.target],
                )

            if not (analasis & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE):
                print("Already up to date")
                subprocess.run(
                    [
                        "git",
                        "--git-dir",
                        str(Config.repositories_path / target_data.owner_username / target_data.reponame),
                        "update-ref",
                        "-m",
                        merge_message,
                        target_branch_ref_name,
                        str(merge_oid),
                        str(target_branch_ref.target),
                    ],
                    check=True,
                    capture_output=True,
                )

            res.headers["HX-Redirect"] = f"/{target_data.owner_username}/{target_data.reponame}/code/{pull_req.target_branch}"


class GetBranchesResponse(TemplateData):
    branches: list[str]


@router.get("/{repository_id}/branches", name="get_branches")
async def get_branches(
    req: Request,
    session: DepSession,
    repository_id: str,
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    data = GetBranchesResponse(req, "components/pull_request_branch_options.html")

    async with acquire() as conn:
        conn: Connection

        # Get the repository.
        repository = await RepositoryPageView.select_by_id(conn, UUID(repository_id))
        if not repository:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        # Ensure the user is the owner or a contributor.
        if repository.owner_id != session.user.user_id and not await Repository.has_contributor(conn, repository.repository_id, session.user.user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        # Open the repoisitory's Git data.
        repo = pygit2.Repository(Config.repositories_path / repository.owner_username / repository.reponame)

        data.branches = [b for b in repo.branches.local]

    return data()
