from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import BIGINT, BOOLEAN, BYTEA, TEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.postgres import Base


class RepositoryContributors(Base):
    __tablename__ = "repository_contributors"

    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id"), primary_key=True
    )
    contributor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)

    username: Mapped[str] = mapped_column(TEXT)
    password_hash: Mapped[bytes] = mapped_column(BYTEA)

    shared_repositories: Mapped[list[RepositoryContributors]] = relationship()


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)

    reponame: Mapped[str] = mapped_column(TEXT)
    private: Mapped[bool] = mapped_column(BOOLEAN)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
