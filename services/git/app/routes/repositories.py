import pygit2
from fastapi import APIRouter

from app.dependencies import DepSessionAuth, ReponamePathParam, UsernamePathParam
from app.env import env

router = APIRouter(prefix="/repositories")


@router.get("/{username}/{reponame}/{commit_id}/{path:path}")
async def code(
    _: DepSessionAuth,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
    commit_id: str = "",
    path: str = "",
):
    repository = pygit2.Repository(env.REPOSITORIES_PATH / username / reponame)
    commit_id = repository.head.shorthand or commit_id
    files = repository.revparse_single(f"{commit_id}:{path}")
