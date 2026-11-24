"use server"

import { DBQueryConfigColumns, EmptyFilter, RelationsFilterColumns } from "drizzle-orm";
import { pg } from "../db/db";
import { relations, repositories, users } from "../db/schema";
import { Session } from "../views";
import { cacheLife, cacheTag } from "next/cache";

export async function getUser(username: string) {
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
    throw Error("user not found")

  return user
}

export async function getUserRepositories(session: Session | undefined, username: string) {
  "use cache"

  cacheTag(`user:${username}:repositories`)
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
    throw Error("user not found")

  return user
}
