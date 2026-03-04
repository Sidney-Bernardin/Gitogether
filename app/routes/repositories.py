import io
import subprocess
from uuid import uuid4
from asyncpg import Connection, UniqueViolationError
from pygit2 import Blob, GitError, InvalidSpecError, Repository, Tree
from pygit2.enums import ObjectType, RepositoryInitFlag

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
import pygit2

from app.dependencies import SessionAuth, templates, repositories_path

router = APIRouter()


@router.post("/repositories")
async def create_repo(req: Request, session: SessionAuth):
    try:
        if not session:
            return Response(status_code=401)

        # Get form data.
        form = await req.form()
        reponame = form.get("reponame")

        repository_id = uuid4()

        async with req.app.state.pg.acquire() as conn:
            conn: Connection
            async with conn.transaction():

                # Insert a new repository.
                await conn.execute("""INSERT INTO repositories (repository_id, name, stars, owner_id) VALUES ($1, $2, $3, $4)""", repository_id, reponame, 0, session["sub"])

                # Init new repository.
                repo_path = repositories_path / session["username"] / reponame
                pygit2.init_repository(repo_path, bare=True, flags=RepositoryInitFlag.MKPATH | RepositoryInitFlag.NO_REINIT)

    except UniqueViolationError:
        return """<p class="error">name taken</p>"""


@router.get("/{username}/{reponame}/info/refs")
async def repo_info(username: str, reponame: str, service: str):
    repo_path = repositories_path / username / reponame
    if not (repo_path).exists():
        return Response(status_code=404)

    stdout = subprocess.run(
        ["git", service[4:], "--stateless-rpc", "--advertise-refs", "."],
        cwd=repo_path,
        capture_output=True,
    ).stdout

    # Formate response.
    res = b"# service=" + service.encode()
    l = len(res) + 4
    l = b"%04x" % l  # Convert length into hexadecimal.
    res = l + res + b"0000" + stdout

    return Response(content=res, media_type=f"application/x-{service}-advertisement")


@router.get("/{username}/{repo_name}")
@router.get("/{username}/{repo_name}/{commit}")
@router.get("/{username}/{repo_name}/{commit}/{path:path}")
async def get_repo(req: Request, session: SessionAuth, username: str, repo_name: str, commit: str | None = None, path: str = ""):
    ctx = {
        "request": req,
        "session": session,
        "repo_info": None,
        "tree": None,
        "blob": None,
    }

    try:
        async with req.app.state.pg.acquire() as conn:
            conn: Connection
            ctx["repo_info"] = await conn.fetch("""SELECT repository_id, name, stars, owner_id, fork_of FROM repositories WHERE name = $1""", repo_name)

        repo = Repository(repositories_path / username / repo_name)
        obj = repo.revparse_single(f"{commit or repo.head.target}:{path}")

        if isinstance(obj, Tree):
            ctx["tree"] = []
            for x in obj:
                ctx["tree"].append(f"{x.type_str} {x.name}")
        elif isinstance(obj, Blob):
            ctx["blob"] = obj.read_raw().decode()

        return templates.TemplateResponse("pages/repository.html", ctx)

    except GitError as err:
        if err.args[0] == "reference 'refs/heads/master' not found":
            pass


@router.post("/{username}/{reponame}/{service}")
async def repo_service(req: Request, username: str, reponame: str, service: str):
    repo_path = repositories_path / username / reponame
    if not (repo_path).exists():
        return Response(status_code=404)

    process = subprocess.Popen(
        ["git", service[4:], "--stateless-rpc", "."],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not process.stdout or not process.stdin:
        return

    async for chunk in req.stream():
        process.stdin.write(chunk)

    stdout, stderr = process.communicate()
    try:
        stdout = io.BytesIO(stdout)
    finally:
        if process.wait() != 0:
            print(stderr)

    return StreamingResponse(content=stdout, media_type=f"application/x-{service}-result")
