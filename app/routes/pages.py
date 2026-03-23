import asyncpg
import pygit2
from typing import Any
from fastapi import APIRouter, Request

import app.domain as domain
import app.postgres as pg
from app.dependencies import Config, SessionAuth, templates

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


@router.get("/{username}", name="user")
async def user(req: Request, session: SessionAuth, username: str):
    ctx = {
        "session": session,
        "user": None,
        "repos": None,
        "contributed_repos": None,
        "is_owner": session and session.username == username,
    }

    try:
        ctx["user"] = await domain.get_user_by_username(username)
        ctx["repos"], ctx["contributed_repos"] = await domain.get_repositories(session, ctx["user"])
    except domain.DomainError:
        pass

    return templates.TemplateResponse(req, "pages/user.html.jinja", context=ctx)


class GetRepoContext:
    user: Any | None
    username: str
    file_path_sufix: str
    repo: pg.RepositoryPage | None = None
    commit_id: str | None = None
    tree: list[pygit2.Tree] | None = None
    blob: bytes | None = None
    file: Any


@router.get("/{username}/{repo_name}", name="repository")
@router.get("/{username}/{repo_name}/{commit_id}", name="repository")
@router.get("/{username}/{repo_name}/{commit_id}/{path:path}", name="repository")
async def get_repo(req: Request, user: SessionAuth, username: str, repo_name: str, commit_id: str = "", path: str = ""):
    ctx = GetRepoContext()
    ctx.user = user
    ctx.username = username
    ctx.file_path_sufix = f"{path}/" if path else ""

    try:
        async with pg.acquire() as conn:
            conn: asyncpg.Connection
            ctx.repo = await pg.select_repository_page(conn, username, repo_name)

            repo = pygit2.Repository(Config.repositories_path / username / repo_name)
            ctx.commit_id = commit_id or repo.head.shorthand
            ctx.file = repo.revparse_single(f"{ctx.commit_id}:{path}")

    except pygit2.GitError as err:
        if (msg := err.args[0]) and msg.startswith("reference 'refs/heads/") and msg.endswith("' not found"):
            pass
        else:
            raise err

    except KeyError:
        pass

    return templates.TemplateResponse(req, "pages/repository.html.jinja", vars(ctx))
