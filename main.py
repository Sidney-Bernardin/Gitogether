import io
import pathlib
import subprocess

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

repositories_path = pathlib.Path("tmp/gitogether/repositories")

app = FastAPI()


@app.post("/{username}/{reponame}")
async def create_repo(username: str, reponame: str):
    repo_path = repositories_path / username / reponame
    repo_path.mkdir(parents=True, exist_ok=True)

    if not (repo_path / "HEAD").exists():
        subprocess.run(["git", "init", "--bare"], cwd=repo_path)


@app.get("/{username}/{reponame}/info/refs")
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


@app.post("/{username}/{reponame}/{service}")
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
