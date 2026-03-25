from contextlib import asynccontextmanager

from pydantic import ValidationError

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app import postgres
from app.routes import pages, login, repositories, git_rpc
from app.dependencies import templates
from app.domain.errors import *


@asynccontextmanager
async def lifespan(app: FastAPI):
    await postgres.init()
    yield
    await postgres.close()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(git_rpc.router)
app.include_router(pages.router)
app.include_router(login.router)
app.include_router(repositories.router, prefix="/gitogether")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(req: Request, err: RequestValidationError):
    return templates.TemplateResponse(
        req, "form_validation_error.html.jinja", context={"errors": err.errors()}
    )


@app.exception_handler(DomainError)
async def service_error_handler(req: Request, err: DomainError):
    status_code: int = -1

    match err.type:
        case DomainErrorType.USERNAME_OR_PASSWORD_INVALID:
            status_code = status.HTTP_401_UNAUTHORIZED
        case (
            DomainErrorType.USER_NOT_FOUND
            | DomainErrorType.REPOSITORY_NOT_FOUND
            | DomainErrorType.REPOSITORY_FILE_NOT_FOUND
        ):
            status_code = status.HTTP_404_NOT_FOUND
        case DomainErrorType.USERNAME_TAKEN | DomainErrorType.REPOSITORY_NAME_TAKEN:
            status_code = status.HTTP_409_CONFLICT

    return Response(
        f"{err.args[0]}: {err.args[1]}",
        status_code,
    )
