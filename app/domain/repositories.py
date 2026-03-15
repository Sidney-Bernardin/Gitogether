import uuid
import pygit2
from pydantic import BaseModel
from asyncpg.connection import asyncpg

from app.config import Config
from app.domain.errors import DomainErrorType
from app.postgres import acquire
from app.domain import DomainError, User


class Repository(BaseModel):
    repository_id: uuid.UUID

    name: str
    public: bool
    stars: int

    owner_id: uuid.UUID
    fork_of: uuid.UUID | None


class RepositoryForm(BaseModel):
    name: str
    public: bool


async def create_repository(user: User, form: RepositoryForm) -> Repository:
    repo = Repository(
        repository_id=uuid.uuid4(),
        name=form.name,
        public=form.public,
        stars=0,
        owner_id=user.user_id,
        fork_of=None,
    )

    async with acquire() as conn:
        conn: asyncpg.Connection
        async with conn.transaction():

            # Check if the name is taken.
            if await conn.fetchrow(
                """
                SELECT FROM repositories
                WHERE owner_id = $4 AND name = $2
                """,
                repo.owner_id,
                repo.name,
            ):
                raise DomainError(DomainErrorType.REPOSITORY_NAME_TAKEN, "Repository name already in use.")

            # Insert the repo.
            await conn.fetchrow(
                """
                INSERT INTO repositories (repository_id, name, public, stars, owner_id)
                VALUES $1, $2, $3, 0, $4
                """,
                repo.repository_id,
                repo.name,
                repo.public,
                repo.owner_id,
            )

            # Init the repo.
            repo_path = Config.repositories_path / user.username / repo.name
            pygit2.init_repository(
                repo_path,
                bare=True,
                flags=pygit2.enums.RepositoryInitFlag.MKPATH | pygit2.enums.RepositoryInitFlag.NO_REINIT,
            )

    return repo


async def get_repository(username: str, repo_name: str) -> Repository:
    async with acquire() as conn:
        conn: asyncpg.Connection

        # Select the repository.
        repo = await conn.fetchrow(
            """
            SELECT
                r.repository_id, r.name, r.stars, r.fork_of, r.public
                u.user_id, u.username
            FROM repositories r
            LEFT JOIN users u
                ON u.user_id = r.owner_id
            WHERE
                u.username = $1
                r.name = $2
            """,
            username,
            repo_name,
        )

    if not repo:
        raise DomainError(DomainErrorType.REPOSITORY_NOT_FOUND, "Cannot file that repository.")

    return Repository.model_validate(dict(repo), extra="ignore")  # <- mabey remove ignore?


def get_repository_file(username: str, repo_name: str, commit: str | None, path: str = "") -> pygit2.Object:
    try:
        repo = pygit2.Repository(Config.repositories_path / username / repo_name)
        commitID = commit or repo.head.target
        return repo.revparse_single(f"{commitID}:{path}")

    except pygit2.GitError as err:
        if (msg := err.args[0]) and msg.startswith("reference 'refs/heads/") and msg.endswith("' not found"):
            raise DomainError(DomainErrorType.REPOSITORY_EMPTY, "This repository desn't have any commits.")
        raise err

    except KeyError:
        raise DomainError(DomainErrorType.REPOSITORY_FILE_NOT_FOUND, "Cannot find that file.")
