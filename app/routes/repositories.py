import pygit2
import subprocess

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
            fork_repo = pygit2.clone_repository(str(source_path), str(dest_path))
            fork_repo.remotes.delete("origin")

    res.headers["HX-Redirect"] = f"/{session.username}/{repo.reponame}"


class CreatePullRequestForm(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    source_branch: str = Field(min_length=1, max_length=1000)
    target_branch: str = Field(min_length=1, max_length=1000)


@router.post("/{target_repo_id}/pull-requests", name="create_pull_request")
async def create_pull_request(
    session: SessionAuth,
    target_repo_id: str,
    form: Annotated[CreatePullRequestForm, Form()],
    source_repo_id: str | None = None,
):
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    async with acquire() as conn:
        conn: Connection
        async with conn.transaction():

            source_repo = await RepositoryPageView.select_by_id(
                conn, repository_id=UUID(source_repo_id)
            )
            target_repo = await RepositoryPageView.select_by_id(
                conn, repository_id=UUID(target_repo_id)
            )

            if not source_repo or not target_repo:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    target_repo_path = Config.repositories_path / target_repo.owner_username / target_repo.reponame
    source_repo_path = Config.repositories_path / source_repo.owner_username / source_repo.reponame

    repo = pygit2.Repository(target_repo_path)

    try:
        remote = repo.remotes.create("source", str(source_repo_path))
    except ValueError:
        remote = repo.remotes["source"]
    remote.fetch()

    target_ref_name = f"refs/heads/{form.target_branch}"
    target_ref = repo.lookup_reference(target_ref_name)

    source_ref_name = f"refs/remotes/source/{form.source_branch}"
    source_ref = repo.lookup_reference(source_ref_name)

    analasis, _ = repo.merge_analysis(source_ref.target, target_ref_name)

    merge_oid: pygit2.Oid | str = ""
    merge_message = ""

    if analasis & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
        print("Already up to date")
        return

    elif analasis & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
        print("Can be fast-forwarded")
        merge_oid = source_ref.target
        merge_message = f"Merge {form.source_branch} into {form.target_branch}"

    elif analasis & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
        print("Merge commit required")

        index = repo.merge_commits(target_ref.target, source_ref.target)
        if index.conflicts:
            print("Conflicts detected")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Merge conflicts detected."
            )

        tree_oid = index.write_tree(repo)

        author = pygit2.Signature(session.username, f"{session.username}@gitogether.com")
        committer = author
        merge_message = f"Merge {form.source_branch} from {source_repo.owner_username}/{source_repo.reponame} into {form.target_branch}"
        merge_oid = repo.create_commit(
            None,
            author,
            committer,
            merge_message,
            tree_oid,
            [target_ref.target, source_ref.target],
        )

    subprocess.run(
        [
            "git",
            "--git-dir",
            str(target_repo_path),
            "update-ref",
            "-m",
            merge_message,
            target_ref_name,
            str(merge_oid),
            str(target_ref.target),
        ],
        check=True,
        capture_output=True,
    )
