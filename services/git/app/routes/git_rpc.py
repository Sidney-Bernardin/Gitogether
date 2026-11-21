import asyncio
import subprocess
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from app.dependencies import DepGitAuth, ReponamePathParam, UsernamePathParam
from app.env import env
from app.views import GitQueryParams, GitService

router = APIRouter()


@router.get("/{username}/{reponame}/info/refs")
async def repo_info(
    _: DepGitAuth,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
    query: Annotated[GitQueryParams, Query()],
):
    if query.service is None:
        return Response("service is empty", status_code=HTTP_422_UNPROCESSABLE_CONTENT)

    try:
        cmd = ["git", query.service[4:], "--stateless-rpc", "--advertise-refs", "."]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=env.REPOSITORIES_PATH / username / reponame,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    stdout, stderr = await proc.communicate()
    assert proc.returncode is not None

    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode,
            cmd,
            stderr=stderr,
        )

    # Formate response.
    res = b"# service=" + query.service.encode()
    l = len(res) + 4
    l = b"%04x" % l  # Convert length into hexadecimal.
    res = l + res + b"0000" + stdout

    return Response(
        content=res, media_type=f"application/x-{query.service}-advertisement"
    )


@router.post("/{username}/{reponame}/{service}")
async def repo_service(
    req: Request,
    _: DepGitAuth,
    username: UsernamePathParam,
    reponame: ReponamePathParam,
    service: GitService,
):
    try:
        cmd = ["git", service[4:], "--stateless-rpc", "."]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=env.REPOSITORIES_PATH / username / reponame,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        return Response(status_code=status.HTTP_404_NOT_FOUND)

    input_done = asyncio.Event()

    async def stream_input() -> None:
        assert proc.stdin is not None

        try:
            async for chunk in req.stream():
                proc.stdin.write(chunk)
                await proc.stdin.drain()
        finally:
            proc.stdin.close()
            await proc.stdin.wait_closed()
            input_done.set()

    input_task = asyncio.create_task(stream_input())

    async def stream_output() -> AsyncGenerator[bytes]:
        assert proc.stdout is not None
        assert proc.stderr is not None

        stderr_task = asyncio.create_task(proc.stderr.read())

        try:
            while chunk := await proc.stdout.read(64 * 1024):
                print(chunk)
                yield chunk

            await input_task
            stderr = await stderr_task

            if returncode := await proc.wait():
                raise subprocess.CalledProcessError(returncode, cmd, stderr=stderr)

        finally:
            input_task.cancel()
            stderr_task.cancel()

            if proc.returncode is None:
                proc.kill()
                await proc.wait()

    await input_done.wait()

    return StreamingResponse(
        content=stream_output(), media_type=f"application/x-{service}-result"
    )
