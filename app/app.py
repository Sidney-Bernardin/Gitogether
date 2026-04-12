from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app import postgres
from app.routes import pages, login, repositories, git_rpc
from app.dependencies import templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    await postgres.init()
    yield
    await postgres.close()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static/dist"), name="static")
app.include_router(repositories.router, prefix="/gitogether")
app.include_router(login.router)
app.include_router(git_rpc.router)
app.include_router(pages.router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(req: Request, err: RequestValidationError):
    return templates.TemplateResponse(
        req, "form_validation_error.html.jinja", context={"errors": err.errors()}
    )
