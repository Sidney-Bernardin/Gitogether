from fastapi.exceptions import RequestValidationError
import jwt
from typing import Annotated
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Form, Request, Response
from pydantic_core import PydanticCustomError

from app.domain import User, signup_user, signin_user
from app.config import Config

router = APIRouter()


class SignupForm(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=50)


@router.post("/signup")
async def signup(res: Response, form: Annotated[SignupForm, Form()]):
    user = await signup_user(form.username, form.password)
    set_new_session(res, user)
    res.headers["HX-Redirect"] = "/"


class SigninForm(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=50)


@router.post("/signin")
async def signin(req: Request, res: Response, form: Annotated[SigninForm, Form()]):
    user = await signin_user(form.username, form.password)
    set_new_session(res, user)
    res.headers["HX-Redirect"] = "/"


@router.get("/signout")
def signout(res: Response):
    res.delete_cookie("session", path="/")
    res.headers["HX-Redirect"] = "/"


def set_new_session(res: Response, user: User):
    session = jwt.encode(
        {
            "sub": str(user.user_id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=Config.session_expiry_hours),
            "user_id": str(user.user_id),
            "username": user.username,
        },
        Config.jwt_secret,
        algorithm="HS256",
    )
    res.set_cookie("session", session, httponly=True, samesite="lax", path="/")
