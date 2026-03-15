import pygit2
from typing import Any, List

from fastapi import APIRouter, Request

from app.domain.errors import DomainError
from app.domain import Repository, get_repository, get_repository_file
from app.dependencies import SessionAuth, templates

router = APIRouter()


@router.get("/")
async def home(req: Request, session: SessionAuth):
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


@router.get("/{username}", name="user")
async def user(req: Request, session: SessionAuth, username: str):
    repositories: List[Any] | None = None
    other_repositories: List[Any] | None = None

    # async with acquire() as conn:
    #     conn: asyncpg.Connection
    #
    #     user = await conn.fetchrow(
    #         """SELECT user_id, username FROM users WHERE username = $1""",
    #         username,
    #     )
    #
    #     if not user:
    #         return templates.TemplateResponse("pages/user.html", {"request": req, "user": None})
    #
    #     is_owner = session and session.get("username") == username
    #     if is_owner:
    #         repositories = await conn.fetch(
    #             """
    #             SELECT repository_id, name, public, fork_of, owner_id
    #             FROM repositories
    #             WHERE owner_id = $1
    #             """,
    #             user["user_id"],
    #         )
    #         other_repositories = await conn.fetch(
    #             """
    #             SELECT repository_id, name, public, fork_of, owner_id
    #             FROM repositories
    #             WHERE EXISTS (
    #                 SELECT FROM repository_contributors
    #                 WHERE user_id = $1
    #             )
    #             """,
    #             user["user_id"],
    #         )
    #     else:
    #         repositories = await conn.fetch(
    #             """
    #             SELECT repository_id, name, public, fork_of, owner_id
    #             FROM repositories
    #             WHERE owner_id = $1 AND public
    #             """,
    #             user["user_id"],
    #         )
    #         other_repositories = await conn.fetch(
    #             """
    #             SELECT repository_id, name, public, fork_of, owner_id
    #             FROM repositories
    #             WHERE EXISTS (
    #                 SELECT FROM repository_contributors
    #                 WHERE user_id = $1 AND public
    #             )
    #             """,
    #             user["user_id"],
    #         )
    #
    # return templates.TemplateResponse(
    #     "pages/user.html",
    #     {
    #         "request": req,
    #         "session": session,
    #         "user": user,
    #         "repositories": repositories,
    #         "other_repositories": other_repositories,
    #         "is_owner": is_owner,
    #     },
    # )


@router.get("/{username}/{repo_name}", name="repository")
@router.get("/{username}/{repo_name}/{commit}", name="repository")
@router.get("/{username}/{repo_name}/{commit}/{path:path}", name="repository")
async def get_repo(req: Request, user: SessionAuth, username: str, repo_name: str, commit: str | None = None, path: str = ""):
    repo: Repository | None = None
    file: pygit2.Object | None = None

    try:
        repo = await get_repository(username, repo_name)
        file = get_repository_file(username, repo_name, commit=commit, path=path)
    except DomainError:
        pass

    return templates.TemplateResponse(
        req,
        "pages/repository.html",
        context={
            "user": user,
            "username": username,
            "commit": commit,
            "path": path,
            "repo": repo,
            "file": file,
        },
    )
