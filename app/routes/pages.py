from uuid import UUID
import pygit2

from typing import Any
from fastapi import APIRouter, HTTPException, Request, status

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
    Res,
    Session,
    SessionAuth,
    UsernamePathParam,
    ReponamePathParam,
    templates,
)

router = APIRouter()


@router.get("/")
async def home(req: Request, session: SessionAuth):
    return templates.TemplateResponse(
        "pages/home.html.jinja",
        {
            "request": req,
            "session": session,
        },
    )


@router.get("/signup")
def signup_page(req: Request):
    return templates.TemplateResponse("pages/signup.html.jinja", {"request": req})


@router.get("/signin")
def signin_page(req: Request):
    return templates.TemplateResponse("pages/signin.html.jinja", {"request": req})


class UserPage(Res):
    session: Session | None
    username: str
    is_owner: bool
    user: UserPageView | None
    repos: list[Repository]
    contributed_repos: list[Repository]


@router.get("/{username}", name="user_page")
async def user_page(req: Request, session: SessionAuth, username: UsernamePathParam):
    res = UserPage(req, "pages/user.html.jinja")
    res.session = session
    res.username = username
    res.is_owner = session is not None and session.username == username

    async with acquire() as conn:
        conn: Connection

        res.user = await UserPageView.select_by_username(conn, username)
        if not res.user:
            return res()

        res.repos = await Repository.select_by_owner_id(conn, res.user.user_id, not res.is_owner)
        res.contributed_repos = await Repository.select_by_contributor_id(
            conn, res.user.user_id, not res.is_owner
        )

    return res()


class RepositoryPage(Res):
    session: Session | None
    username: str
    file_path_sufix: str
    repo: RepositoryPageView | None = None
    repo_branches: list[str] | None = None
    commit_id: str | None = None
    file: Any


@router.get("/{username}/{reponame}", name="repository_page")
@router.get("/{username}/{reponame}/commits/{commit_id}", name="repository_page")
@router.get("/{username}/{reponame}/commits/{commit_id}/{path:path}", name="repository_page")
async def get_repo(
    req: Request,
    session: SessionAuth,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
    commit_id: str = "",
    path: str = "",
):
    res = RepositoryPage(req, "pages/repository.html.jinja")
    res.session = session
    res.username = username
    res.file_path_sufix = f"{path}/" if path else ""

    try:
        async with acquire() as conn:
            conn: Connection

            res.repo = await RepositoryPageView.select_by_names(conn, username, reponame)
            if not res.repo:
                return res()

            if res.repo.private and (
                not session
                or (
                    res.repo.owner_id != session.user_id
                    and not await Repository.has_contributor(
                        conn, res.repo.repository_id, session.user_id
                    )
                )
            ):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

        try:
            repo = pygit2.Repository(Config.repositories_path / username / reponame)
            res.repo_branches = [branch for branch in repo.branches]
            res.commit_id = commit_id or repo.head.shorthand
            res.file = repo.revparse_single(f"{res.commit_id}:{path}")
        except KeyError:
            pass

        return res()

    except pygit2.GitError as err:
        if (
            (msg := err.args[0])
            and msg.startswith("reference 'refs/heads/")
            and msg.endswith("' not found")
        ):
            return res()
        raise err


class CreatePullRequestPage(Res):
    session: Session | None
    username: str
    repo: RepositoryPageView | None = None
    repo_branches: list[str] | None = None
    source_repo: RepositoryPageView | None = None
    source_repo_branches: list[str] | None = None


@router.get("/{username}/{reponame}/create-pull-request", name="create_pull_request_page")
async def create_pull_request_page(
    req: Request,
    session: SessionAuth,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
    child: str | None = None,
):
    res = CreatePullRequestPage(req, "pages/create_pull_request.html.jinja")
    res.session = session
    res.username = username

    async with acquire() as conn:
        conn: Connection

        res.repo = await RepositoryPageView.select_by_names(conn, username, reponame)
        if not res.repo:
            return res()

        if child:
            res.source_repo = await RepositoryPageView.select_by_id(conn, UUID(child))

        if not res.source_repo:
            return res()

        if res.source_repo.private and (
            not session
            or not await Repository.has_contributor(conn, res.repo.repository_id, session.user_id)
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    repo = pygit2.Repository(Config.repositories_path / username / reponame)
    res.repo_branches = [branch for branch in repo.branches]

    source_repo_path = (
        Config.repositories_path / res.source_repo.owner_username / res.source_repo.reponame
    )
    source_repo = pygit2.Repository(source_repo_path)
    res.source_repo_branches = [branch for branch in source_repo.branches]

    return res()


class PullRequestPage(Res):
    session: Session | None
    username: str
    repo: RepositoryPageView | None = None
    pull_req: PullRequest | None = None
    diff: pygit2.Diff | None = None


@router.get("/{username}/{reponame}/pull-requests/{pull_request_id}", name="pull_request_page")
async def pull_request_page(
    req: Request,
    session: SessionAuth,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
    pull_request_id: str,
):
    res = PullRequestPage(req, "pages/pull_request.html.jinja")
    res.session = session
    res.username = username

    async with acquire() as conn:
        conn: Connection

        res.repo = await RepositoryPageView.select_by_names(conn, username, reponame)
        if not res.repo:
            return res()

        res.pull_req = await PullRequest.select_by_id(conn, UUID(pull_request_id))
        if not res.pull_req:
            return res()

    repo = pygit2.Repository(Config.repositories_path / username / reponame)
    repo.remotes[str(res.pull_req.pull_request_id)].fetch()
    diff = repo.diff(
        (
            f"refs/heads/{res.pull_req.source_branch}"
            if res.pull_req.source_branch == "HEAD"
            else f"refs/remotes/{res.pull_req.pull_request_id}/{res.pull_req.source_branch}"
        ),
        res.pull_req.target_branch,
    )
    res.diff = "".join(([p.text for p in diff]))

    return res()
