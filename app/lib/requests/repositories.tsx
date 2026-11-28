import { pg } from "../db/db";
import { Result } from "../errors";
import { DomainError, RepositoryPage, Session } from "../views";

export async function getRepositoryPage(session: Session | undefined, username: string, reponame: string): Promise<Result<RepositoryPage, DomainError>> {
  const repository = await pg.query.repositories.findFirst({
    columns: {
      id: true,
      reponame: true,
      description: true,
      stars: true,
      tags: true,
    },
    with: {
      owner: {
        columns: {
          id: true,
          username: true,
        },
      }
    },
    where: !session
      ? {
        reponame: reponame,
        owner: {
          username: username,
        },
        private: false,
      } : {
        reponame: reponame,
        owner: {
          username: username,
        },
        OR: [
          { owner_id: session.userId },
          { contributors: { id: session.userId } }
        ]
      }
  })

  if (!repository)
    return [undefined, {
      type: "repository_not_found",
      msg: "A repository with that name doesn't exist.",
    }]

  return [repository, undefined]
}
