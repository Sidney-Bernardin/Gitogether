import asyncpg
import pygit2

import pydantic
from pydantic.dataclasses import dataclass
from dataclasses import asdict

from fastapi import APIRouter, Request

import app.domain as domain
from app.domain.errors import DomainError
from app.domain import get_user_by_username, get_repositories
from app.dependencies import Config, SessionAuth, templates
from app.domain.users import User
from app.postgres import acquire

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
    ctx = {
        "session": session,
        "user": None,
        "repos": None,
        "contributed_repos": None,
        "is_owner": session and session.username == username,
    }

    try:
        ctx["user"] = await get_user_by_username(username)
        ctx["repos"], ctx["contributed_repos"] = await get_repositories(session, ctx["user"])
    except DomainError as err:
        pass

    return templates.TemplateResponse(req, "pages/user.html", ctx)


@dataclass(config=pydantic.ConfigDict(arbitrary_types_allowed=True))
class GetRepoContext:
    user: User | None
    username: str
    file_path_sufix: str
    repo: asyncpg.Record | None = None
    commit_id: str | None = None
    file: pygit2.Object | None = None


@router.get("/{username}/{repo_name}", name="repository")
@router.get("/{username}/{repo_name}/{commit_id}", name="repository")
@router.get("/{username}/{repo_name}/{commit_id}/{path:path}", name="repository")
async def get_repo(req: Request, user: SessionAuth, username: str, repo_name: str, commit_id: str = "", path: str = ""):
    ctx = GetRepoContext(
        user,
        username,
        file_path_sufix=f"{path}/" if path else "",
    )

    try:
        async with acquire() as conn:
            conn: asyncpg.Connection

            # Sect the repository.
            ctx.repo = await conn.fetchrow(
                """
                SELECT r.repository_id, r.name, r.stars, r.fork_of, r.public, r.owner_id, u.user_id, u.username
                FROM repositories r
                LEFT JOIN users u ON u.user_id = r.owner_id
                WHERE u.username = $1 AND r.name = $2
                """,
                username,
                repo_name,
            )

            if not ctx.repo:
                raise KeyError

            # Get the file from the repository.
            repo_svc = pygit2.Repository(Config.repositories_path / username / repo_name)
            ctx.commit_id = commit_id or repo_svc.head.shorthand
            ctx.file = repo_svc.revparse_single(f"{ctx.commit_id}:{path}")

    except pygit2.GitError as err:
        if (msg := err.args[0]) and msg.startswith("reference 'refs/heads/") and msg.endswith("' not found"):
            pass
        else:
            raise err

    except KeyError:
        pass

    return templates.TemplateResponse(req, "pages/repository.html", asdict(ctx))
