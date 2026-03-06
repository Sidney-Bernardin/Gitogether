import io
from typing import Annotated, Any
import bcrypt
import subprocess
import asyncpg
import uuid

import pygit2
import pygit2.enums

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse

from app.dependencies import GetBasicCredentials, http_basic_auth, SessionAuth, templates, repositories_path

router = APIRouter()


@router.post("/repositories")
async def create_repo(req: Request, session: SessionAuth):
    try:
        if not session:
            return Response(status_code=401)

        # Get form data.
        form = await req.form()
        reponame = form.get("reponame")

        repository_id = uuid.uuid4()

        async with req.app.state.pg.acquire() as conn:
            conn: asyncpg.Connection
            async with conn.transaction():

                # Insert a new repository.
                await conn.execute(
                    """INSERT INTO repositories (repository_id, name, stars) VALUES ($1, $2, $3)""",
                    repository_id,
                    reponame,
                    0,
                )
                await conn.execute(
                    """INSERT INTO repository_users (repository_id, user_id, role) VALUES ($1, $2, $3)""",
                    repository_id,
                    session["sub"],
                    "admin",
                )

                # Init new repository.
                repo_path = repositories_path / session["username"] / reponame
                pygit2.init_repository(
                    repo_path,
                    bare=True,
                    flags=pygit2.enums.RepositoryInitFlag.MKPATH | pygit2.enums.RepositoryInitFlag.NO_REINIT,
                )

    except asyncpg.UniqueViolationError:
        return """<p class="error">name taken</p>"""


@router.get("/{username}/{repo_name}/info/refs")
async def repo_info(req: Request, credentials: Annotated[Any, Depends(http_basic_auth)], username: str, repo_name: str, service: str):
    print(credentials)
    try:
        async with req.app.state.pg.acquire() as conn:
            conn: asyncpg.Connection

            repo = await conn.fetchrow("""SELECT repository_id FROM repositories WHERE name = $1""", repo_name)
            if not repo:
                return Response(status_code=status.HTTP_404_NOT_FOUND)

            user = await conn.fetchrow(
                """
                SELECT u.password FROM users u
                LEFT JOIN repository_users ru ON ru.user_id = u.user_id
                WHERE
                    u.username = $1 AND
                    ru.repository_id = $2
                """,
                credentials.username,
                repo["repository_id"],
            )

            if not user or not bcrypt.checkpw(credentials.password.encode(), user["password"]):
                return Response(status_code=status.HTTP_401_UNAUTHORIZED)

        stdout = subprocess.run(
            ["git", service[4:], "--stateless-rpc", "--advertise-refs", "."],
            cwd=repositories_path / username / repo_name,
            capture_output=True,
        ).stdout

        # Formate response.
        res = b"# service=" + service.encode()
        l = len(res) + 4
        l = b"%04x" % l  # Convert length into hexadecimal.
        res = l + res + b"0000" + stdout

        return Response(content=res, media_type=f"application/x-{service}-advertisement")

    except FileNotFoundError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)


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
            conn: asyncpg.Connection
            ctx["repo_info"] = await conn.fetch("""SELECT repository_id, name, stars, owner_id, fork_of FROM repositories WHERE name = $1""", repo_name)

        repo = pygit2.Repository(repositories_path / username / repo_name)
        obj = repo.revparse_single(f"{commit or repo.head.target}:{path}")

        if isinstance(obj, pygit2.Tree):
            ctx["tree"] = []
            for x in obj:
                ctx["tree"].append(f"{x.type_str} {x.name}")
        elif isinstance(obj, pygit2.Blob):
            ctx["blob"] = obj.read_raw().decode()

        return templates.TemplateResponse("pages/repository.html", ctx)

    except pygit2.GitError as err:
        if err.args[0] == "reference 'refs/heads/master' not found":
            pass


@router.post("/{username}/{repo_name}/{service}")
async def repo_service(req: Request, credentials: GetBasicCredentials, username: str, repo_name: str, service: str):
    try:
        async with req.app.state.pg.acquire() as conn:
            conn: asyncpg.Connection

            repo = await conn.fetchrow("""SELECT public FROM repositories WHERE name = $1""", repo_name)
            if not repo:
                return Response(status_code=status.HTTP_404_NOT_FOUND)

            # Get the user and check it's password.
            user = await conn.fetchrow("""SELECT user_id, username, password FROM users WHERE username = $1""", credentials.username)
            if not user or not bcrypt.checkpw(credentials.password.encode(), user["password"]):
                return Response(status_code=status.HTTP_401_UNAUTHORIZED)

        process = subprocess.Popen(
            ["git", service[4:], "--stateless-rpc", "."],
            cwd=repositories_path / username / repo_name,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if not process.stdin:
            print(f"========== {req.url}: stdin is None ==========")
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

    except FileNotFoundError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
