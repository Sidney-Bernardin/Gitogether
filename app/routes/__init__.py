from typing import Any, List
import asyncpg
from fastapi import Request, APIRouter

from app.dependencies import SessionAuth, templates
from app.routes import login, repositories

router = APIRouter(tags=["pages"])
router.include_router(login.router)
router.include_router(repositories.router)


@router.get("/")
async def home(req: Request, session: SessionAuth):
    return templates.TemplateResponse(
        "pages/home.html",
        {
            "request": req,
            "session": session,
        },
    )


@router.get("/{username}", name="user")
async def user(req: Request, session: SessionAuth, username: str):
    repositories: List[Any] | None = None
    other_repositories: List[Any] | None = None

    async with req.app.state.pg.acquire() as conn:
        conn: asyncpg.Connection

        user = await conn.fetchrow(
            """SELECT user_id, username FROM users WHERE username = $1""",
            username,
        )

        if not user:
            return templates.TemplateResponse("pages/user.html", {"request": req, "user": None})

        is_owner = session and session.get("username") == username
        if is_owner:
            repositories = await conn.fetch(
                """
                SELECT repository_id, name, public, fork_of, owner_id
                FROM repositories
                WHERE owner_id = $1
                """,
                user["user_id"],
            )
            other_repositories = await conn.fetch(
                """
                SELECT repository_id, name, public, fork_of, owner_id
                FROM repositories
                WHERE EXISTS (
                    SELECT FROM repository_contributors
                    WHERE user_id = $1
                )
                """,
                user["user_id"],
            )
        else:
            repositories = await conn.fetch(
                """
                SELECT repository_id, name, public, fork_of, owner_id
                FROM repositories
                WHERE owner_id = $1 AND public
                """,
                user["user_id"],
            )
            other_repositories = await conn.fetch(
                """
                SELECT repository_id, name, public, fork_of, owner_id
                FROM repositories
                WHERE EXISTS (
                    SELECT FROM repository_contributors
                    WHERE user_id = $1 AND public
                )
                """,
                user["user_id"],
            )

    return templates.TemplateResponse(
        "pages/user.html",
        {
            "request": req,
            "session": session,
            "user": user,
            "repositories": repositories,
            "other_repositories": other_repositories,
            "is_owner": is_owner,
        },
    )
