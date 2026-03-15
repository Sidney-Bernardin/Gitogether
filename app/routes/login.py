import jwt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Response

from app.dependencies import form_get
from app.domain import User, signup_user, signin_user
from app.config import Config

router = APIRouter()


@router.get("/signout")
def signout(res: Response):
    res.delete_cookie("session", path="/")
    res.headers["HX-Redirect"] = "/"


@router.post("/signup")
async def signup(req: Request, res: Response):

    f = await req.form()
    username = form_get(f, "username") or ""
    password = form_get(f, "password") or ""

    user = await signup_user(username, password)
    set_new_session(res, user)
    res.headers["HX-Redirect"] = "/"


@router.post("/signin")
async def signin(req: Request, res: Response):

    f = await req.form()
    username = form_get(f, "username") or ""
    password = form_get(f, "password") or ""

    user = await signin_user(username, password)
    set_new_session(res, user)
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
