import io
import subprocess

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import StreamingResponse

from app.config import Config
from app.dependencies import git_auth

router = APIRouter()


@router.get("/{username}/{repo_name}/info/refs")
async def repo_info(_: git_auth, username: str, repo_name: str, service: str):
    try:
        stdout = subprocess.run(
            ["git", service[4:], "--stateless-rpc", "--advertise-refs", "."],
            cwd=Config.repositories_path / username / repo_name,
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


@router.post("/{username}/{repo_name}/{service}")
async def repo_service(req: Request, _: git_auth, username: str, repo_name: str, service: str):
    try:
        process = subprocess.Popen(
            ["git", service[4:], "--stateless-rpc", "."],
            cwd=Config.repositories_path / username / repo_name,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        assert process.stdin is not None

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
