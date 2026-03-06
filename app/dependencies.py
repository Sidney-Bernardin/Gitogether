import os
import jwt
import pathlib
import asyncpg
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates


class Config:
    jwt_secret = os.getenv("APP_JWT_SECRET", "foobarbaz")
    session_expiry_hours = int(os.getenv("APP_SESSION_EXPIRY_HOURS", "24"))
    postgres_url = os.getenv("APP_POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/postgres")


templates = Jinja2Templates(os.path.join(os.path.dirname(__file__), "templates"))
repositories_path = pathlib.Path("tmp/gitogether/repositories")


def session_auth(req: Request):
    try:
        return jwt.decode(req.cookies["session"], Config.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except KeyError:
        return None


SessionAuth = Annotated[Any, Depends(session_auth)]


class HTTPBasicAuth(HTTPBasic):
    async def __call__(self, req: Request, repo_name: str) -> HTTPBasicCredentials | None:
        async with req.app.state.pg.acquire() as conn:
            conn: asyncpg.Connection

            repo = await conn.fetchrow("""SELECT public FROM repositories WHERE name = $1""", repo_name)
            if not repo:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        return await super().__call__(req)


_http_basic_auth = HTTPBasicAuth()
http_basic_auth = Annotated[HTTPBasicCredentials, Depends(_http_basic_auth)]
