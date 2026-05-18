from typing import Any
from uuid import UUID

import pygit2
import pygit2.enums

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.postgres import (
    Connection,
    acquire,
    Repository,
    RepositoryPageView,
    UserPageView,
    PullRequest,
)

from app.dependencies import (
    Config,
    DepRepositoryPage,
    TemplateData,
    Session,
    DepSession,
    UsernamePathParam,
    ReponamePathParam,
    templates,
)

router = APIRouter()


@router.get("/")
async def home(req: Request, session: DepSession):
    return templates.TemplateResponse(
        "pages/home.html",
        {
            "request": req,
            "session": session,
        },
    )


@router.get("/signup")
def signup_page(req: Request):
    return templates.TemplateResponse("pages/signup.html", {"request": req})


@router.get("/signin")
def signin_page(req: Request):
    return templates.TemplateResponse("pages/signin.html", {"request": req})


class UserPageData(TemplateData):
    session: Session | None
    username: str
    is_owner: bool
    user: UserPageView | None
    repos: list[Repository]
    contributed_repos: list[Repository]


@router.get("/{username}", name="user_page")
async def user_page(
    req: Request,
    session: DepSession,
    username: UsernamePathParam,
):
    data = UserPageData(req, "pages/user.html")
    data.session = session
    data.username = username
    data.is_owner = session is not None and session.user.username == username

    async with acquire() as conn:
        conn: Connection

        # Get the user.
        data.user = await UserPageView.select_by_username(conn, username)
        if not data.user:
            return data()

        # Get the user's repositories.
        data.repos = await Repository.select_by_owner_id(conn, data.user.user_id, not data.is_owner)

        # Get the user's contributed repositories.
        data.contributed_repos = await Repository.select_by_contributor_id(conn, data.user.user_id, not data.is_owner)

    return data()


class RepositoryPageData(TemplateData):
    session: Session | None
    repository: RepositoryPageView | None = None
    username: str
    file_path: str
    file_path_sufix: str
    branches: list[str] | None = None
    commit_id: str | None = None
    commits: list[pygit2.Commit] | None = None
    file: Any


@router.get("/{username}/{reponame}", name="repository_code_page")
@router.get("/{username}/{reponame}/code/{commit_id}", name="repository_code_page")
@router.get("/{username}/{reponame}/code/{commit_id}/{path:path}", name="repository_code_page")
async def get_repo(
    req: Request,
    session: DepSession,
    repository: DepRepositoryPage,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
    commit_id: str = "",
    path: str = "",
):
    data = RepositoryPageData(req, "pages/repository.html")

    if not repository:
        return data()

    data.session = session
    data.repository = repository
    data.username = username
    data.file_path = path
    data.file_path_sufix = f"{path}/" if path else ""

    async with acquire() as conn:

        # If the repository is private, ensure the user is it's owner or a contributor.
        if data.repository.private and (
            not session
            or (
                data.repository.owner_id != session.user.user_id
                and not await Repository.has_contributor(conn, data.repository.repository_id, session.user.user_id)
            )
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    try:

        # Open the repoisitory's Git data.
        repo = pygit2.Repository(Config.repositories_path / username / reponame)

        data.branches = [branch for branch in repo.branches.local]
        data.commit_id = commit_id or repo.head.shorthand
        commit = repo.revparse_single(data.commit_id)
        data.commits = [c for c in repo.walk(commit.id, pygit2.enums.SortMode.TOPOLOGICAL)]
        data.file = repo.revparse_single(f"{data.commit_id}:{path}")

    except pygit2.GitError as err:

        # When the branch doesn't exist ignore the error.
        if (msg := err.args[0]) and msg.startswith("reference 'refs/heads/") and msg.endswith("' not found"):
            return data()

        raise err

    except KeyError:
        pass

    return data()


class PullRequestsPageData(TemplateData):
    session: Session | None
    repository: RepositoryPageView | None = None
    username: str
    branches: list[str] = []
    pull_requests: list[PullRequest] = []
    source_repositories: list[RepositoryPageView] = []


@router.get("/{username}/{reponame}/pull-requests", name="repository_pull_requests_page")
async def pull_requests_page(
    req: Request,
    response: Response,
    session: DepSession,
    repository: DepRepositoryPage,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
):
    data = PullRequestsPageData(req, "pages/pull_requests.html")

    if not session:
        response.headers["HX-Redirect"] = "/signin"
        return

    if not repository:
        return data()

    data.session = session
    data.repository = repository
    data.username = username

    async with acquire() as conn:
        conn: Connection

        # Get the pull-requests.
        data.pull_requests = await PullRequest.select_by_target_id(conn, data.repository.repository_id)

        # Open the repoisitory's Git data.
        respository = pygit2.Repository(Config.repositories_path / username / reponame)

        data.branches = [b for b in respository.branches.local]
        data.source_repositories = [
            *await RepositoryPageView.select_by_parent_and_user_id(
                conn,
                data.repository.repository_id,
                session.user.user_id,
            ),
        ]

    return data()


class PullRequestPageData(TemplateData):
    session: Session | None
    repository: RepositoryPageView | None = None
    username: str
    pull_request: PullRequest | None = None
    conflicts: list[str] | None = None
    diff: pygit2.Diff | None = None


@router.get("/{username}/{reponame}/pull-requests/{pull_request_id}", name="repository_pull_request_page")
async def pull_request_page(
    req: Request,
    session: DepSession,
    repository: DepRepositoryPage,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
    pull_request_id: str,
):
    data = PullRequestPageData(req, "pages/pull_request.html")

    if not repository:
        return data()

    data.session = session
    data.repository = repository
    data.username = username

    async with acquire() as conn:

        # Get the pull-request.
        data.pull_request = await PullRequest.select_by_id(conn, UUID(pull_request_id))
        if not data.pull_request:
            return data()

    # Open the repoisitory's Git data.
    repo = pygit2.Repository(Config.repositories_path / username / reponame)
    repo.remotes[str(data.pull_request.pull_request_id)].fetch()

    # Get the target and source branches.
    target_branch = repo.lookup_reference(f"refs/heads/{data.pull_request.target_branch}")
    source_branch = repo.lookup_reference(f"refs/heads/{data.pull_request.source_branch}" if data.pull_request.source_branch == "HEAD" else f"refs/remotes/{data.pull_request.pull_request_id}/{data.pull_request.source_branch}")

    # Temporarily merge.
    index = repo.merge_commits(target_branch.target, source_branch.target)

    # If there are conflicts, get their filenames.
    if index.conflicts:
        data.conflicts = [c[1].path for c in index.conflicts]
        return data()

    # Get the diff of the merge against the target branch's head.
    # diff = index.diff_to_tree(repo.head.peel(pygit2.Tree))  # TODO use the target branch's head
    diff = index.diff_to_tree(target_branch.peel(pygit2.Tree))
    data.diff = "".join(([p.text for p in diff]))

    return data()


class ForksPageData(TemplateData):
    session: Session | None
    repository: RepositoryPageView | None = None
    username: str
    forks: list[RepositoryPageView] | None = None


@router.get("/{username}/{reponame}/forks", name="repository_forks_page")
async def forks_page(
    req: Request,
    session: DepSession,
    repository: DepRepositoryPage,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
):
    data = ForksPageData(req, "pages/forks.html")

    if not repository:
        return data()

    data.session = session
    data.repository = repository
    data.username = username

    async with acquire() as conn:

        # Get the forks.
        data.forks = await RepositoryPageView.select_by_parent_id(conn, data.repository.repository_id)

    return data()
