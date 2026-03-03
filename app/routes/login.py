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

    # Get form data.
    form = await req.form()
    username = form.get("username")
    password = form.get("password")

    # Validate form.
    if not isinstance(username, str) or not isinstance(password, str):
        return '<p class="error">Username and password are required</p>'
    if len(username) < 3:
        return '<p class="error">Username must be at least 3 characters</p>'
    if len(password) < 6:
        return '<p class="error">Password must be at least 6 characters</p>'

    async with req.app.state.pg.acquire() as conn:
        conn: Connection

        # Check username.
        if await conn.fetchrow("""SELECT user_id FROM users WHERE username = $1""", username):
            return '<p class="error">Username already taken</p>'

        # Hash password.
        pw_salt = bcrypt.gensalt()
        pw_hashed = bcrypt.hashpw(password.encode(), pw_salt)

        user_id = uuid4()

        # Insert a new user.
        await conn.execute("""INSERT INTO users (user_id, username, password_hash, password_salt) VALUES ($1, $2, $3, $4)""", user_id, username, pw_hashed, pw_salt)

    set_new_session(res, user_id, username)
    res.headers["HX-Redirect"] = "/"


@router.post("/signin")
async def signin(req: Request, res: Response):

    # Get form data.
    form = await req.form()
    username = form.get("username")
    password = form.get("password")

    # Validate form.
    if not isinstance(username, str) or not isinstance(password, str):
        return '<p class="error">Username and password are required</p>'

    async with req.app.state.pg.acquire() as conn:
        conn: Connection

        # Get the user and check it's password.
        row = await conn.fetchrow("""SELECT user_id, username, password_hash FROM users WHERE username = $1""", username)
        if not row or not bcrypt.checkpw(password.encode(), row["password_hash"]):
            return '<p class="error">Invalid username or password</p>'

    set_new_session(res, row["user_id"], row["username"])
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
