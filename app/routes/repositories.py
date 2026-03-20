import pathlib
import pygit2
from fastapi import APIRouter, HTTPException, Request, Response, status

from app.dependencies import SessionAuth, form_get, templates
from app.domain import create_repository
from app.domain.repositories import fork_repository

router = APIRouter(prefix="/repositories")


@router.post("/")
async def create_repo(req: Request, user: SessionAuth):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    f = await req.form()
    name = form_get(f, "name") or ""
    public = form_get(f, "public") or ""

    repo = await create_repository(user, name, public)

    return templates.TemplateResponse(
        req,
        "repository.html",
        context={
            "view": "list-item",
            "username": user.username,
            "repo": repo,
            "is_owner": True,
        },
    )


@router.patch("/{repository_id}/fork", name="create_repository_fork")
async def create_fork(req: Request, res: Response, repository_id: str, user: SessionAuth):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    f = await req.form()
    name = form_get(f, "name") or ""

    repo = await fork_repository(user, repository_id, name)

    res.headers["HX-Redirect"] = f"/{user.username}/{repo.name}"
