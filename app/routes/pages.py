import pygit2

from typing import Any
from fastapi import APIRouter, HTTPException, Request, status

from app.postgres import Connection, acquire, Repository, RepositoryPageView, UserPageView
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
    commit_id: str | None = None
    file: Any


@router.get("/{username}/{reponame}", name="repository_page")
@router.get("/{username}/{reponame}/{commit_id}", name="repository_page")
@router.get("/{username}/{reponame}/{commit_id}/{path:path}", name="repository_page")
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

        repo = pygit2.Repository(Config.repositories_path / username / reponame)
        res.commit_id = commit_id or repo.head.shorthand
        res.file = repo.revparse_single(f"{res.commit_id}:{path}")

        return res()

    except pygit2.GitError as err:
        if (
            (msg := err.args[0])
            and msg.startswith("reference 'refs/heads/")
            and msg.endswith("' not found")
        ):
            return res()
        raise err
