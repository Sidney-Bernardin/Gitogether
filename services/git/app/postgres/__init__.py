from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.env import env

engine = create_async_engine(env.POSTGRES_DSN)


class Base(DeclarativeBase):
    pass
