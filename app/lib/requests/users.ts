"use server"

import { DBQueryConfigColumns } from "drizzle-orm";
import { pg } from "../db/db";
import { repositories } from "../db/schema";
import { DomainError, Session, UserProfile, UserRepositories } from "../views";
import { cacheLife, cacheTag } from "next/cache";
import { Result } from "../errors";

export async function getUser(username: string): Promise<Result<UserProfile, DomainError>> {
  "use cache"

  cacheTag(`user:${username}`)
  cacheLife("minutes")

  const user = await pg.query.users.findFirst({
    columns: {
      id: true,
      created_at: true,
    },
    where: {
      username: username,
    }
  })

  if (!user)
    return [undefined, {
      type: "user_not_found",
      msg: "A user with that username doesn't exist.",
    }]

  return [user, undefined]
}

export async function getUserRepositories(session: Session | undefined, username: string): Promise<Result<UserRepositories, DomainError>> {
  "use cache"

  cacheTag(`user:${username}: repositories`)
  cacheLife("minutes")

  const repositoryColumns = {
    id: true,
    reponame: true,
  } as const satisfies DBQueryConfigColumns<typeof repositories._.columns>

  const user = session ?
    await pg.query.users.findFirst({
      columns: {},
      where: { username: username },
      with: {
        owned_repositories: {
          columns: repositoryColumns,
          where: {
            OR: [
              { owner_id: session.userId },
              { contributors: { id: session.userId } }
            ]
          }
        },
        shared_repositories: {
          columns: repositoryColumns,
          where: {
            OR: [
              { owner_id: session.userId },
              { contributors: { id: session.userId } }
            ]
          }
        },
      },
    }) :
    await pg.query.users.findFirst({
      columns: {},
      where: { username: username },
      with: {
        owned_repositories: {
          columns: repositoryColumns,
          where: { private: false }
        },
        shared_repositories: {
          columns: repositoryColumns,
          where: { private: false }
        },
      },
    })

  if (!user)
    return [undefined, {
      type: "user_not_found",
      msg: "A user with that username doesn't exist.",
    }]

  return [user, undefined]
}
