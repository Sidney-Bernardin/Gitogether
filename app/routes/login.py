import jwt
import bcrypt
from asyncpg import Connection
from uuid import UUID, uuid4
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse

from app.dependencies import Config, templates

router = APIRouter()


@router.get("/signup")
def signup_page(req: Request):
    return templates.TemplateResponse("pages/signup.html", {"request": req})


@router.get("/signin")
def signin_page(req: Request):
    return templates.TemplateResponse("pages/signin.html", {"request": req})


@router.get("/signout")
def signout(res: Response):
    res.delete_cookie("session", path="/")
    res.headers["HX-Redirect"] = "/"


@router.post("/signup")
async def signup(req: Request, res: Response):

    form = await req.form()
    username = form.get("username")
    password = form.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return "Username and password are required"
    if len(username) < 3:
        return "Username must be at least 3 characters"
    if len(password) < 6:
        return "Password must be at least 6 characters"

    user_id = uuid4()
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    async with req.app.state.pg.acquire() as conn:
        conn: Connection

        if await conn.fetchrow("""SELECT user_id FROM users WHERE username = $1""", username):
            return "Username already taken"

        await conn.execute("""INSERT INTO users (user_id, username, password) VALUES ($1, $2, $3)""", user_id, username, password_hash)

    set_new_session(res, user_id, username)
    res.headers["HX-Redirect"] = "/"


@router.post("/signin")
async def signin(req: Request, res: Response):

    form = await req.form()
    username = form.get("username")
    password = form.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return "Username and password are required"

    async with req.app.state.pg.acquire() as conn:
        conn: Connection

        user = await conn.fetchrow("""SELECT user_id, username, password FROM users WHERE username = $1""", username)
        if not user or not bcrypt.checkpw(password.encode(), user["password"]):
            return "Invalid username or password"

    set_new_session(res, user["user_id"], user["username"])
    res.headers["HX-Redirect"] = "/"


def set_new_session(res: Response, user_id: UUID, username: str):
    session = jwt.encode(
        {
            "sub": str(user_id),
            "username": username,
            "exp": datetime.now(timezone.utc) + timedelta(hours=Config.session_expiry_hours),
        },
        Config.jwt_secret,
        algorithm="HS256",
    )
    res.set_cookie("session", session, httponly=True, samesite="lax", path="/")
