import os
import jwt
import pathlib
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates


class Config:
    jwt_secret = os.getenv("APP_JWT_SECRET", "foobarbaz")
    session_expiry_hours = int(os.getenv("APP_SESSION_EXPIRY_HOURS", "24"))
    postgres_url = os.getenv("APP_POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/postgres")


templates = Jinja2Templates(os.path.join(os.path.dirname(__file__), "templates"))
repositories_path = pathlib.Path("tmp/gitogether/repositories")

get_basic_credentials = HTTPBasic()


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


def basic_auth(credentials: Annotated[HTTPBasicCredentials, Depends(get_basic_credentials)]):
    pass


BasicAuth = Annotated[Any, Depends(basic_auth)]
