class Repository:
    repository_id: UUID

    reponame: str
    description: str
    private: bool
    stars: int
    tags: list[str]

    created_at: datetime
    updated_at: datetime

    owner_id: UUID
    parent_id: UUID | None

    async def insert(self, c: Connection) -> str:
        return await c.execute(
            """
            INSERT INTO repositories (
                repository_id,
                reponame, description, private, stars, tags,
                created_at, updated_at,
                owner_id, parent_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            self.repository_id,
            self.reponame,
            self.description,
            self.private,
            self.stars,
            self.tags,
            self.created_at,
            self.updated_at,
            self.owner_id,
            self.parent_id,
        )

    @classmethod
    async def exists(cls, c: Connection, repository_id: UUID) -> bool:
        return (
            await c.fetchrow(
                """
                SELECT 1 FROM repositories
                WHERE repository_id = $1
                """,
                repository_id,
            )
            is not None
        )

    @classmethod
    async def has_contributor(
        cls, c: Connection, repository_id: UUID, user_id: UUID
    ) -> bool:
        return (
            await c.fetchrow(
                """
                SELECT 1 FROM repository_contributors
                WHERE
                    repository_id = $1 AND
                    user_id = $2
                """,
                repository_id,
                user_id,
            )
            is not None
        )

    @classmethod
    async def is_names_taken(cls, c: Connection, username: str, reponame: str) -> bool:
        return (
            await c.fetchrow(
                """
                SELECT 1 FROM repositories
                WHERE
                    reponame = $1 AND
                    EXISTS (
                        SELECT 1 FROM users
                        WHERE username = $2 AND user_id = repositories.owner_id
                    )
                """,
                reponame,
                username,
            )
            is not None
        )

    @classmethod
    async def select_by_names(
        cls, c: Connection, username: str, reponame: str
    ) -> Self | None:
        return await fetchrow(
            c,
            cls,
            """
            SELECT
                repository_id,
                reponame, description, private, stars, tags,
                created_at, updated_at,
                parent_id, owner_id
            FROM repositories r
            WHERE
                r.reponame = $2 AND
                EXISTS (
                    SELECT 1 FROM users
                    WHERE username = $1 AND user_id = r.owner_id
                )
            """,
            username,
            reponame,
        )

    @classmethod
    async def select_by_owner_id(
        cls, c: Connection, owner_id: UUID, public_only: bool
    ) -> list[Self]:
        return await fetchrows(
            c,
            cls,
            """
            SELECT
                repository_id,
                reponame, description, private, stars, tags,
                created_at, updated_at,
                parent_id, owner_id
            FROM repositories
            WHERE
                owner_id = $1 AND
                private = COALESCE($2, private)
            """,
            owner_id,
            False if public_only else None,
        )

    @classmethod
    async def select_by_contributor_id(
        cls, c: Connection, contributor_id: UUID, public_only: bool
    ) -> list[Self]:
        return await fetchrows(
            c,
            cls,
            """
            SELECT
                repository_id,
                reponame, private, stars, tags,
                parent_id, owner_id
            FROM repositories
            WHERE EXISTS (
                SELECT FROM repository_contributors
                WHERE
                    user_id = $1 AND
                    private = COALESCE($2, private)
            )
            """,
            contributor_id,
            False if public_only else None,
        )


@dataclass
class RepositoryPageView:
    repository_id: UUID

    reponame: str
    description: str
    private: bool
    stars: int
    tags: list[str]
    forks: int

    owner_id: UUID
    owner_username: str

    parent_id: UUID | None
    parent_reponame: str | None
    parent_owner_username: str | None

    @classmethod
    async def select_by_id(cls, c: Connection, repository_id: UUID) -> Self | None:
        return await fetchrow(
            c,
            cls,
            """
            SELECT
                r.repository_id, r.reponame, r.description, r.stars, r.private, r.tags,
                (SELECT COUNT(*) FROM repositories WHERE parent_id = r.repository_id) AS forks,

                r.owner_id,
                u.username AS owner_username,

                r.parent_id,
                pr.reponame AS parent_reponame,
                pu.username AS parent_owner_username
            FROM repositories r
            LEFT JOIN users u ON u.user_id = r.owner_id
            LEFT JOIN repositories pr ON r.parent_id = pr.repository_id
            LEFT JOIN users pu ON pu.user_id = pr.owner_id
            WHERE
                r.repository_id = $1
            """,
            repository_id,
        )

    @classmethod
    async def select_by_names(
        cls, c: Connection, username: str, reponame: str
    ) -> Self | None:
        return await fetchrow(
            c,
            cls,
            """
            SELECT
                r.repository_id, r.reponame, r.description, r.stars, r.private, r.tags,
                (SELECT COUNT(*) FROM repositories WHERE parent_id = r.repository_id) AS forks,

                r.owner_id,
                u.username AS owner_username,

                r.parent_id,
                pr.reponame AS parent_reponame,
                pu.username AS parent_owner_username
            FROM repositories r
            LEFT JOIN users u ON u.user_id = r.owner_id
            LEFT JOIN repositories pr ON r.parent_id = pr.repository_id
            LEFT JOIN users pu ON pu.user_id = pr.owner_id
            WHERE
                u.username = $1 AND
                r.reponame = $2
            """,
            username,
            reponame,
        )

    @classmethod
    async def select_by_parent_id(cls, c: Connection, parent_id: UUID) -> list[Self]:
        return await fetchrows(
            c,
            cls,
            """
            SELECT
                r.repository_id, r.reponame, r.description, r.stars, r.private, r.tags,
                (SELECT COUNT(*) FROM repositories WHERE parent_id = r.repository_id) AS forks,

                r.owner_id,
                u.username AS owner_username,

                r.parent_id,
                pr.reponame AS parent_reponame,
                pu.username AS parent_owner_username
            FROM repositories r
            LEFT JOIN users u ON u.user_id = r.owner_id
            LEFT JOIN repositories pr ON r.parent_id = pr.repository_id
            LEFT JOIN users pu ON pu.user_id = pr.owner_id
            WHERE
                r.parent_id = $1
            """,
            parent_id,
        )

    @classmethod
    async def select_by_parent_and_user_id(
        cls,
        c: Connection,
        parent_id: UUID,
        contributor_id: UUID,
    ) -> list[Self]:
        return await fetchrows(
            c,
            cls,
            """
            SELECT
                r.repository_id, r.reponame, r.description, r.stars, r.private, r.tags,
                (SELECT COUNT(*) FROM repositories WHERE parent_id = r.repository_id) AS forks,

                r.owner_id,
                u.username AS owner_username,

                r.parent_id,
                pr.reponame AS parent_reponame,
                pu.username AS parent_owner_username
            FROM repositories r
            LEFT JOIN users u ON u.user_id = r.owner_id
            LEFT JOIN repositories pr ON r.parent_id = pr.repository_id
            LEFT JOIN users pu ON pu.user_id = pr.owner_id
            WHERE
                r.parent_id = $1
                AND
                    r.owner_id = $2
                    OR EXISTS (
                        SELECT FROM repository_contributors rc
                        WHERE rc.user_id = $2
                    )
            """,
            parent_id,
            contributor_id,
        )
