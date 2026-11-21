import logging
import subprocess

from fastapi import FastAPI, Request, Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.routes import git_rpc, repositories

logger = logging.getLogger(__name__)

app = FastAPI()

app.include_router(git_rpc.router)
app.include_router(repositories.router, prefix="/api")


def parse_stream(stream: str | bytes | None) -> str | None:
    if stream is None or isinstance(stream, str):
        return stream

    return stream.decode(errors="replace").strip()


@app.exception_handler(subprocess.CalledProcessError)
async def called_proccess_error(req: Request, exc: subprocess.CalledProcessError):
    logger.error(
        """Subprocess failed
            return_code: %s
            stdout: %s
            stderr: %s""",
        exc.returncode,
        parse_stream(exc.stdout),
        parse_stream(exc.stderr),
        exc_info=exc,
    )

    return Response(status_code=HTTP_500_INTERNAL_SERVER_ERROR)
