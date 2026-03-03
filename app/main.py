from contextlib import asynccontextmanager
import asyncpg
from fastapi import FastAPI

from app.dependencies import Config
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pg = await asyncpg.create_pool(Config.postgres_url)
    yield
    await app.state.pg.close()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
