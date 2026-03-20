from typing import Tuple
import uuid
import pygit2
from pydantic import BaseModel
from asyncpg.connection import asyncpg

from app.config import Config
from app.postgres import acquire
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


async def create_repository(user: User, name: str, public: str) -> Repository:
    repo = Repository(
        repository_id=uuid.uuid4(),
        name=name,
        public=public == "true" or public == "yes" or public == "on",
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
                SELECT 1 FROM repositories
                WHERE owner_id = $1 AND name = $2
                """,
                repo.owner_id,
                repo.name,
            ):
                raise DomainError(DomainErrorType.REPOSITORY_NAME_TAKEN, "repository name already in use")

            # Insert the repo.
            await conn.fetchrow(
                """
                INSERT INTO repositories (repository_id, name, public, stars, owner_id)
                VALUES ($1, $2, $3, 0, $4)
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


async def fork_repository(user: User, repository_id: str, fork_name: str) -> Repository:
    async with acquire() as conn:
        conn: asyncpg.Connection
        async with conn.transaction():

            # Select the repository.
            original_repo = await conn.fetchrow(
                """
                SELECT
                    r.repository_id, r.name, r.stars, r.fork_of, r.public, r.owner_id,
                    u.user_id, u.username
                FROM repositories r
                LEFT JOIN users u
                    ON u.user_id = r.owner_id
                WHERE r.repository_id = $1
                """,
                repository_id,
            )

            if not original_repo:
                raise DomainError(DomainErrorType.REPOSITORY_NOT_FOUND, "")

            if original_repo.owner_id == user.user_id:
                raise DomainError(DomainErrorType.CANNOT_FORK_OWN_REPO, "you cannot fork your own repository")

            if not original_repo.public:
                raise DomainError(DomainErrorType.CANNOT_FORK_PRIVATE_REPO, "")

            # Check if the name is taken.
            if await conn.fetchrow(
                """
                SELECT 1 FROM repositories
                WHERE owner_id = $1 AND name = $2
                """,
                user.user_id,
                original_repo["name"],
            ):
                raise DomainError(DomainErrorType.REPOSITORY_NAME_TAKEN, "repository name already in use")

            repo = Repository(
                repository_id=uuid.uuid4(),
                name=fork_name,
                public=True,
                stars=0,
                owner_id=user.user_id,
                fork_of=original_repo["repository_id"],
            )

            # Insert the repo.
            await conn.fetchrow(
                """
                INSERT INTO repositories (repository_id, name, public, stars, owner_id, fork_of)
                VALUES ($1, $2, $3, 0, $4)
                """,
                repo.repository_id,
                repo.name,
                repo.public,
                repo.owner_id,
                repo.fork_of,
            )

            repository = pygit2.clone_repository(
                Config.repositories_path / original_repo["username"] / original_repo["name"],
                Config.repositories_path / user.username / fork_name,
            )

            return repo


async def select_repository(conn: asyncpg.Connection, username: str, repo_name: str) -> asyncpg.Record | None:
    return await conn.fetchrow(
        """
        SELECT
            r.repository_id, r.name, r.stars, r.fork_of, r.public, r.owner_id,
            u.user_id, u.username
        FROM repositories r
        LEFT JOIN users u
            ON u.user_id = r.owner_id
        WHERE
            u.username = $1 AND
            r.name = $2
        """,
        username,
        repo_name,
    )


async def get_repositories(session: User | None, user: User) -> Tuple[list[Repository], list[Repository]]:
    async with acquire() as conn:
        conn: asyncpg.Connection

        repos = await conn.fetch(
            """
            SELECT repository_id, name, public, stars, fork_of, owner_id
            FROM repositories
            WHERE
                owner_id = $1 AND
                public = COALESCE($2, public)
            """,
            user.user_id,
            None if session and session.username == user.username else True,
        )

        contributed_repos = await conn.fetch(
            """
            SELECT repository_id, name, public, stars, fork_of, owner_id
            FROM repositories
            WHERE EXISTS (
                SELECT FROM repository_contributors
                WHERE
                    user_id = $1 AND
                    public = COALESCE($2, public)
            )
            """,
            user.user_id,
            None if session and session.username == user.username else True,
        )

    return (
        [Repository.model_validate(dict(repo)) for repo in repos],
        [Repository.model_validate(dict(repo)) for repo in contributed_repos],
    )


def get_repository_file(username: str, repo_name: str, commit: str | None, path: str = "") -> pygit2.Object:
    try:
        repo = pygit2.Repository(Config.repositories_path / username / repo_name)
        commitID = commit or repo.head.name
        return repo.revparse_single(f"{commitID}:{path}")
    except pygit2.GitError as err:
        if (msg := err.args[0]) and msg.startswith("reference 'refs/heads/") and msg.endswith("' not found"):
            raise DomainError(DomainErrorType.REPOSITORY_EMPTY, "This repository desn't have any commits.")
        raise err

    except KeyError:
        raise DomainError(DomainErrorType.REPOSITORY_FILE_NOT_FOUND, "Cannot find that file.")
