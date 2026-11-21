from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.env import env

url = make_url(env.POSTGRES_DSN.encoded_string()).set(drivername="postgresql+asyncpg")
engine = create_async_engine(url, echo=True)

AsyncSessionMaker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass
