from fastapi import APIRouter, Request

from app.domain.errors import DomainError, DomainErrorType
from app.domain import get_user_by_username, get_repository, get_repositories, get_repository_file
from app.dependencies import SessionAuth, templates

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


@router.get("/{username}/{repo_name}", name="repository")
@router.get("/{username}/{repo_name}/{commit}", name="repository")
@router.get("/{username}/{repo_name}/{commit}/{path:path}", name="repository")
async def get_repo(req: Request, user: SessionAuth, username: str, repo_name: str, commit: str | None = None, path: str = ""):
    ctx = {
        "user": user,
        "username": username,
        "commit": commit,
        "sufix_path": f"{path}/" if path else "",
        "repo": None,
        "file": None,
        "err": None,
    }

    try:
        ctx["repo"] = await get_repository(username, repo_name)
        ctx["file"] = get_repository_file(username, repo_name, commit=commit, path=path)
    except DomainError as err:
        match err.type:
            case DomainErrorType.REPOSITORY_EMPTY | DomainErrorType.REPOSITORY_FILE_NOT_FOUND:
                ctx["err"] = err.type.name
            case _:
                raise

    return templates.TemplateResponse(req, "pages/repository.html", ctx)
