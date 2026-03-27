import bcrypt
import uuid
import jwt

from typing import Annotated
from pydantic import BaseModel, Field
from pydantic_core import PydanticCustomError
from datetime import datetime, timezone, timedelta
from asyncpg import Connection

from fastapi import APIRouter, Form, Response
from fastapi.exceptions import RequestValidationError

from app.postgres import acquire, User
from app.config import Config
from app.dependencies import username_regex

router = APIRouter()


class SignupForm(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=username_regex)
    password: str = Field(min_length=6, max_length=50)


@router.post("/signup")
async def signup(res: Response, form: Annotated[SignupForm, Form()]):
    async with acquire() as conn:
        conn: Connection

        if await User.is_username_taken(conn, form.username):
            raise RequestValidationError([PydanticCustomError("username_taken", "Username taken.")])

        user = User(
            user_id=uuid.uuid4(),
            username=form.username,
            password=bcrypt.hashpw(form.password.encode(), bcrypt.gensalt()),
        )

        await user.insert(conn)

    set_new_session(res, user)
    res.headers["HX-Redirect"] = "/"


class SigninForm(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=username_regex)
    password: str = Field(min_length=6, max_length=50)


@router.post("/signin")
async def signin(res: Response, form: Annotated[SigninForm, Form()]):
    async with acquire() as conn:
        conn: Connection

        user = await User.select_by_username(conn, form.username)
        if not user or not bcrypt.checkpw(form.password.encode(), user.password):
            raise RequestValidationError(
                [
                    PydanticCustomError(
                        "invalid_username_or_password", "Invalid username or password."
                    )
                ]
            )

    set_new_session(res, user)
    res.headers["HX-Redirect"] = "/"


@router.get("/signout")
def signout(res: Response):
    res.delete_cookie("session", path="/")
    res.headers["HX-Redirect"] = "/"


def set_new_session(res: Response, user: User):
    res.set_cookie(
        "session",
        httponly=True,
        samesite="lax",
        path="/",
        value=jwt.encode(
            key=Config.jwt_secret,
            algorithm="HS256",
            payload={
                "sub": str(user.user_id),
                "exp": datetime.now(timezone.utc) + timedelta(hours=Config.session_expiry_hours),
                "user_id": str(user.user_id),
                "username": user.username,
            },
        ),
    )
