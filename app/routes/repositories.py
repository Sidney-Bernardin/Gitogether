import jinja2
import io
import bcrypt
import subprocess
import asyncpg
import uuid

import pygit2
import pygit2.enums

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import StreamingResponse

from app.dependencies import git_auth, SessionAuth, templates, repositories_path

router = APIRouter()


@router.post("/repositories")
async def create_repo(req: Request, session: SessionAuth):
    try:
        if not session:
            return Response(status_code=401)

        form = await req.form()
        repo_name = form.get("repo_name")
        public = form.get("public") == "on"

        repository_id = uuid.uuid4()

        async with req.app.state.pg.acquire() as conn:
            conn: asyncpg.Connection
            async with conn.transaction():

                repo = await conn.fetchrow(
                    """
                    INSERT INTO repositories (repository_id, name, public, stars, owner_id)
                    SELECT $1, $2, $3, 0, $4
                    WHERE NOT EXISTS (
                        SELECT FROM repositories
                        WHERE owner_id = $4 AND name = $2
                    )
                    RETURNING repository_id
                    """,
                    repository_id,
                    repo_name,
                    public,
                    session["sub"],
                )

                if not repo:
                    return """<p class="error">name taken</p>"""

                repo_path = repositories_path / session["username"] / repo_name
                pygit2.init_repository(
                    repo_path,
                    bare=True,
                    flags=pygit2.enums.RepositoryInitFlag.MKPATH | pygit2.enums.RepositoryInitFlag.NO_REINIT,
                )

        repo = {
            "repository_id": repository_id,
            "name": repo_name,
            "public": public,
        }
        return templates.TemplateResponse(
            "repository.html",
            context={"request": req, "view": "list-item", "username": session["username"], "repo": repo, "is_owner": True},
        )

    except asyncpg.UniqueViolationError:
        return """<p class="error">name taken</p>"""


@router.get("/{username}/{repo_name}/info/refs")
async def repo_info(repo: git_auth, username: str, repo_name: str, service: str):
    try:
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


@router.get("/{username}/{repo_name}", name="repository")
@router.get("/{username}/{repo_name}/{commit}", name="repository")
@router.get("/{username}/{repo_name}/{commit}/{path:path}", name="repository")
async def get_repo(req: Request, session: SessionAuth, username: str, repo_name: str, commit: str | None = None, path: str = ""):
    ctx = {
        "request": req,
        "session": session,
        "username": username,
        "repo_name": repo_name,
        "path": f"{path}/" if path else "",
        "repo_info": None,
        "tree": None,
        "blob": None,
    }

    try:
        async with req.app.state.pg.acquire() as conn:
            conn: asyncpg.Connection
            ctx["repo_info"] = await conn.fetchrow(
                """
                SELECT repository_id, name, stars, fork_of, public
                FROM repositories
                WHERE
                    name = $1 AND
                    EXISTS (
                        SELECT FROM users
                        WHERE username = $2
                    )
                """,
                repo_name,
                username,
            )
            if not ctx["repo_info"]:
                ctx["not_found"] = True
                return templates.TemplateResponse("pages/repository.html", ctx)

        repo = pygit2.Repository(repositories_path / username / repo_name)
        ctx["commit"] = commit or repo.head.target
        try:
            obj = repo.revparse_single(f"{ctx["commit"]}:{path}")
        except KeyError:
            ctx["not_found"] = True
            return templates.TemplateResponse("pages/repository.html", ctx)

        if isinstance(obj, pygit2.Tree):
            ctx["tree"] = []
            for x in obj:
                ctx["tree"].append(x)
        elif isinstance(obj, pygit2.Blob):
            ctx["blob"] = obj.read_raw().decode()

        return templates.TemplateResponse("pages/repository.html", ctx)

    except pygit2.GitError as err:
        ctx["commit"] = None
        if err.args[0] == "reference 'refs/heads/master' not found":
            return templates.TemplateResponse("pages/repository.html", ctx)
        raise err


@router.post("/{username}/{repo_name}/{service}")
async def repo_service(req: Request, repo: git_auth, username: str, repo_name: str, service: str):
    try:
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
