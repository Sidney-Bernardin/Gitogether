import uuid
import asyncpg
from fastapi import Request, APIRouter

from app.dependencies import SessionAuth, templates
from app.routes import login, repositories

router = APIRouter(tags=["pages"])
router.include_router(login.router)
router.include_router(repositories.router)


@router.get("/")
async def home(req: Request, session: SessionAuth):
    async with req.app.state.pg.acquire() as conn:
        conn: asyncpg.Connection

        repositories = await conn.fetch(
            """
            SELECT r.repository_id, r.name, r.public, r.fork_of
            FROM repositories r
            WHERE EXISTS
                (SELECT ru.user_id FROM repository_users ru WHERE ru.user_id = $1)
            """,
            session["sub"],
        )

    return templates.TemplateResponse(
        "pages/home.html",
        {
            "request": req,
            "session": session,
            "repositories": repositories,
        },
    )
